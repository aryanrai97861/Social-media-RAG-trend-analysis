import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.schema import get_engine
from rag.retriever import RAGRetriever
from rag.generator import RAGGenerator
from utils.config import load_config
from utils.content_filter import filter_content

st.set_page_config(
    page_title="Topic Explorer",
    page_icon="🔎",
    layout="wide"
)

config = load_config()

@st.cache_resource
def get_rag_system():
    """Initialize RAG system components"""
    try:
        retriever = RAGRetriever(
            chroma_path=config.get('CHROMA_PATH', './data/chroma'),
            embedding_model=config.get('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        )
        
        generator = RAGGenerator(
            model_name=config.get('GEN_MODEL', 'google/flan-t5-base')
        )
        
        return retriever, generator
    except Exception as e:
        st.error(f"Error initializing RAG system: {str(e)}")
        return None, None

def search_posts(query, platform=None, limit=20):
    """Search posts by query"""
    try:
        engine = get_engine()
        
        where_clause = "WHERE text LIKE ?"
        params = [f"%{query}%"]
        
        if platform and platform != "All":
            where_clause += " AND platform = ?"
            params.append(platform)
        
        sql_query = f"""
            SELECT id, platform, author, text, url, created_at, hashtags, entities
            FROM posts
            {where_clause}
            ORDER BY datetime(created_at) DESC
            LIMIT {limit}
        """
        
        df = pd.read_sql(sql_query, engine, params=params)
        df['created_at'] = pd.to_datetime(df['created_at'])
        return df
        
    except Exception as e:
        st.error(f"Error searching posts: {str(e)}")
        return pd.DataFrame()

def get_related_topics(query):
    """Get related topics using embeddings"""
    try:
        retriever, _ = get_rag_system()
        if not retriever:
            return []
        
        results = retriever.search(query, k=5)
        return [result.get('entity', 'Unknown') for result in results]
        
    except Exception as e:
        st.error(f"Error getting related topics: {str(e)}")
        return []

def main():
    st.title("🔎 Topic Explorer")
    st.markdown("Search and explore social media topics with AI-powered contextual analysis")
    
    # Search interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input(
            "🔍 Search topics, hashtags, or keywords:",
            placeholder="Enter your search query... (e.g., #trending, climate change, memes)"
        )
    
    with col2:
        # Platform filter
        try:
            engine = get_engine()
            platforms_df = pd.read_sql("SELECT DISTINCT platform FROM posts ORDER BY platform", engine)
            platforms = ["All"] + platforms_df['platform'].tolist()
            selected_platform = st.selectbox("Platform", platforms)
        except:
            selected_platform = "All"
    
    if search_query:
        tab1, tab2, tab3 = st.tabs(["📱 Posts", "🤖 AI Analysis", "🔗 Related Topics"])
        
        with tab1:
            st.subheader(f"Posts containing: '{search_query}'")
            
            # Search posts
            posts_df = search_posts(search_query, selected_platform)
            
            if not posts_df.empty:
                # Display results count
                st.info(f"Found {len(posts_df)} posts")
                
                # Filter and display options
                col1, col2, col3 = st.columns(3)
                with col1:
                    show_filtered = st.checkbox("Apply content filtering", value=True)
                with col2:
                    posts_per_page = st.selectbox("Posts per page", [10, 20, 50], index=1)
                with col3:
                    sort_by = st.selectbox("Sort by", ["Most Recent", "Most Relevant"])
                
                # Apply filtering if requested
                if show_filtered:
                    posts_df = posts_df[posts_df['text'].apply(
                        lambda x: filter_content(x)['is_safe']
                    )]
                
                # Paginate results
                total_pages = max(1, (len(posts_df) - 1) // posts_per_page + 1)
                
                if total_pages > 1:
                    page = st.selectbox(f"Page (1-{total_pages})", range(1, total_pages + 1))
                    start_idx = (page - 1) * posts_per_page
                    end_idx = start_idx + posts_per_page
                    page_posts = posts_df.iloc[start_idx:end_idx]
                else:
                    page_posts = posts_df.head(posts_per_page)
                
                # Display posts
                for idx, post in page_posts.iterrows():
                    with st.expander(
                        f"📱 {post['platform'].title()} - {post['created_at'].strftime('%Y-%m-%d %H:%M')}",
                        expanded=False
                    ):
                        # Post content
                        st.write(post['text'][:500] + "..." if len(post['text']) > 500 else post['text'])
                        
                        # Metadata
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if post['author']:
                                st.text(f"👤 {post['author']}")
                        with col2:
                            if post['hashtags']:
                                hashtags = post['hashtags'].split(',')
                                st.text(f"#️⃣ {', '.join(hashtags[:3])}")
                        with col3:
                            if post['url']:
                                st.link_button("🔗 View Original", post['url'])
                        
                        # Entities
                        if post['entities']:
                            entities = post['entities'].split(',')[:5]
                            st.text(f"🏷️ Tags: {', '.join(entities)}")
                        
                        # Content safety check
                        safety_result = filter_content(post['text'])
                        if not safety_result['is_safe']:
                            st.warning(f"⚠️ Content Warning: {', '.join(safety_result['flags'])}")
            
            else:
                st.info(f"No posts found for '{search_query}'. Try different keywords or check if data ingestion has been run.")
        
        with tab2:
            st.subheader("🤖 AI-Powered Analysis")
            
            retriever, generator = get_rag_system()
            
            if retriever and generator:
                with st.spinner("Generating analysis..."):
                    try:
                        # Get context from RAG
                        context_results = retriever.search(search_query, k=3)
                        
                        if context_results:
                            # Generate analysis
                            context_text = "\n".join([
                                result.get('content', '')[:200] 
                                for result in context_results
                            ])
                            
                            analysis = generator.generate_explanation(
                                query=search_query,
                                context=context_text,
                                max_length=200
                            )
                            
                            # Display analysis
                            st.markdown("### 📝 Contextual Analysis")
                            st.write(analysis)
                            
                            # Show sources
                            st.markdown("### 📚 Knowledge Sources")
                            for i, result in enumerate(context_results, 1):
                                with st.expander(f"Source {i}: {result.get('title', 'Unknown')}"):
                                    st.write(result.get('content', 'No content available')[:500])
                                    if result.get('url'):
                                        st.link_button("🔗 View Source", result['url'])
                        
                        else:
                            st.info("No contextual information found for this topic. Try indexing more context or use different keywords.")
                    
                    except Exception as e:
                        st.error(f"Error generating analysis: {str(e)}")
            
            else:
                st.error("RAG system not available. Please check the configuration and try again.")
            
            # Manual context search
            st.markdown("### 🔍 Manual Context Search")
            if st.button("Search Wikipedia"):
                with st.spinner("Searching Wikipedia..."):
                    try:
                        import wikipedia
                        try:
                            page = wikipedia.page(search_query)
                            st.markdown(f"**{page.title}**")
                            summary = wikipedia.summary(search_query, sentences=3)
                            st.write(summary)
                            st.link_button("📖 Read Full Article", page.url)
                        except wikipedia.exceptions.DisambiguationError as e:
                            st.write("Multiple pages found. Suggestions:")
                            for option in e.options[:5]:
                                st.write(f"• {option}")
                        except wikipedia.exceptions.PageError:
                            st.info(f"No Wikipedia page found for '{search_query}'")
                    except Exception as e:
                        st.error(f"Wikipedia search error: {str(e)}")
        
        with tab3:
            st.subheader("🔗 Related Topics")
            
            # Get related topics from embeddings
            with st.spinner("Finding related topics..."):
                related_topics = get_related_topics(search_query)
                
                if related_topics:
                    st.markdown("### 🎯 Similar Topics")
                    cols = st.columns(min(3, len(related_topics)))
                    for i, topic in enumerate(related_topics[:6]):
                        with cols[i % 3]:
                            if st.button(f"🔍 {topic}", key=f"related_{i}"):
                                st.session_state.search_query = topic
                                st.rerun()
                
                # Trending topics in same category
                try:
                    engine = get_engine()
                    similar_trends = pd.read_sql("""
                        SELECT entity, trend_score, current_count
                        FROM trends
                        WHERE entity LIKE ?
                        ORDER BY trend_score DESC
                        LIMIT 10
                    """, engine, params=[f"%{search_query.split()[0]}%"])
                    
                    if not similar_trends.empty:
                        st.markdown("### 📈 Trending Similar Topics")
                        for _, trend in similar_trends.iterrows():
                            col1, col2, col3 = st.columns([2, 1, 1])
                            with col1:
                                st.write(f"**{trend['entity']}**")
                            with col2:
                                st.write(f"Score: {trend['trend_score']:.1f}")
                            with col3:
                                st.write(f"Mentions: {trend['current_count']}")
                
                except Exception as e:
                    st.error(f"Error loading similar trends: {str(e)}")
    
    else:
        # Show trending topics as suggestions
        st.subheader("🔥 Trending Topics")
        st.markdown("Click on any trending topic to explore it:")
        
        try:
            engine = get_engine()
            trending_df = pd.read_sql("""
                SELECT entity, trend_score, current_count
                FROM trends
                ORDER BY trend_score DESC
                LIMIT 12
            """, engine)
            
            if not trending_df.empty:
                cols = st.columns(3)
                for i, (_, trend) in enumerate(trending_df.iterrows()):
                    with cols[i % 3]:
                        if st.button(
                            f"🔥 {trend['entity'][:30]}{'...' if len(trend['entity']) > 30 else ''}\n"
                            f"Score: {trend['trend_score']:.1f} | Mentions: {trend['current_count']}",
                            key=f"trending_{i}"
                        ):
                            # Set search query and rerun
                            st.session_state.search_query = trend['entity']
                            st.rerun()
            else:
                st.info("No trending topics available. Run data ingestion and trend computation first.")
        
        except Exception as e:
            st.error(f"Error loading trending topics: {str(e)}")

if __name__ == "__main__":
    main()
