#!/usr/bin/env python3
"""
Index context documents into ChromaDB for RAG retrieval
This script processes curated content and Wikipedia articles for contextual understanding
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.retriever import RAGRetriever
from utils.config import load_config
import markdown

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def load_markdown_files(directory: str) -> List[Dict[str, Any]]:
    """Load markdown files from directory"""
    documents = []
    md_dir = Path(directory)
    
    if not md_dir.exists():
        logging.warning(f"Directory does not exist: {directory}")
        return documents
    
    for md_file in md_dir.glob("*.md"):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse markdown to get title
            lines = content.split('\n')
            title = md_file.stem.replace('_', ' ').title()
            
            # Look for markdown title
            for line in lines:
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
            
            # Remove markdown headers from content for better indexing
            clean_content = content
            if content.startswith('# '):
                # Remove first title line
                clean_content = '\n'.join(lines[1:]).strip()
            
            doc = {
                'content': clean_content,
                'metadata': {
                    'title': title,
                    'filename': md_file.name,
                    'type': 'curated_content',
                    'source': 'local',
                    'category': md_file.stem.split('_')[0] if '_' in md_file.stem else 'general',
                    'indexed_at': time.strftime('%Y-%m-%d %H:%M:%S')
                },
                'id': f"curated_{md_file.stem}"
            }
            
            documents.append(doc)
            logging.info(f"Loaded: {title} ({len(clean_content)} chars)")
            
        except Exception as e:
            logging.error(f"Error loading {md_file}: {str(e)}")
    
    return documents

def chunk_content(content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split content into overlapping chunks"""
    if len(content) <= chunk_size:
        return [content]
    
    chunks = []
    start = 0
    
    while start < len(content):
        end = start + chunk_size
        
        # Try to break at a sentence or paragraph
        if end < len(content):
            # Look for good break points
            break_points = [
                content.rfind('\n\n', start, end),  # Paragraph break
                content.rfind('. ', start, end),    # Sentence end
                content.rfind('\n', start, end)     # Line break
            ]
            
            good_break = max([bp for bp in break_points if bp > start])
            if good_break > start:
                end = good_break + 1
        
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = max(start + chunk_size - overlap, end)
    
    return chunks

def process_documents_for_indexing(documents: List[Dict[str, Any]], chunk_size: int = 1000) -> List[Dict[str, Any]]:
    """Process documents into chunks suitable for indexing"""
    processed_docs = []
    
    for doc in documents:
        content = doc['content']
        metadata = doc['metadata']
        doc_id = doc['id']
        
        # Chunk the content
        chunks = chunk_content(content, chunk_size)
        
        for i, chunk in enumerate(chunks):
            chunk_doc = {
                'content': chunk,
                'metadata': {
                    **metadata,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'chunk_id': f"{doc_id}_chunk_{i}"
                },
                'id': f"{doc_id}_chunk_{i}"
            }
            processed_docs.append(chunk_doc)
    
    logging.info(f"Created {len(processed_docs)} chunks from {len(documents)} documents")
    return processed_docs

def fetch_wikipedia_articles(topics: List[str], cache_dir: str = "context/wikipedia_cache") -> List[Dict[str, Any]]:
    """Fetch Wikipedia articles for specified topics"""
    try:
        import wikipedia
    except ImportError:
        logging.error("Wikipedia package not installed. Install with: pip install wikipedia")
        return []
    
    documents = []
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    
    for topic in topics:
        try:
            # Check cache first
            cache_file = cache_path / f"{topic.replace(' ', '_')}.txt"
            
            if cache_file.exists():
                logging.info(f"Loading cached Wikipedia article: {topic}")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                logging.info(f"Fetching Wikipedia article: {topic}")
                
                try:
                    page = wikipedia.page(topic)
                    content = page.content
                    url = page.url
                    title = page.title
                except wikipedia.exceptions.DisambiguationError as e:
                    # Try first option
                    page = wikipedia.page(e.options[0])
                    content = page.content
                    url = page.url
                    title = page.title
                    logging.info(f"Used disambiguation: {title}")
                except wikipedia.exceptions.PageError:
                    logging.warning(f"Wikipedia page not found: {topic}")
                    continue
                
                # Cache the content
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Create document
            doc = {
                'content': content,
                'metadata': {
                    'title': topic,
                    'type': 'wikipedia',
                    'source': 'wikipedia',
                    'category': 'encyclopedia',
                    'url': f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}",
                    'indexed_at': time.strftime('%Y-%m-%d %H:%M:%S')
                },
                'id': f"wikipedia_{topic.replace(' ', '_').lower()}"
            }
            
            documents.append(doc)
            logging.info(f"Added Wikipedia article: {topic} ({len(content)} chars)")
            
            # Rate limiting
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"Error fetching Wikipedia article for {topic}: {str(e)}")
    
    return documents

def get_default_wikipedia_topics() -> List[str]:
    """Get default list of Wikipedia topics to index"""
    return [
        "Internet meme",
        "Viral video",
        "Social media",
        "Twitter",
        "Reddit",
        "TikTok",
        "Instagram",
        "Facebook",
        "Social movement",
        "Digital activism",
        "Cancel culture",
        "Influencer marketing",
        "Hashtag activism",
        "Viral marketing",
        "Internet culture",
        "Meme culture",
        "Digital media",
        "Social networking service",
        "User-generated content",
        "Online community",
        "Digital communication",
        "Social media and politics",
        "Fake news",
        "Echo chamber",
        "Filter bubble",
        "Social media influence",
        "Digital divide",
        "Online harassment",
        "Cyberbullying",
        "Digital privacy",
        "Content moderation",
        "Algorithm",
        "Machine learning",
        "Natural language processing",
        "Text mining",
        "Sentiment analysis"
    ]

def main():
    """Main indexing function"""
    parser = argparse.ArgumentParser(description='Index context documents for Social Media RAG')
    parser.add_argument('--curated-dir', default='context/curated',
                       help='Directory containing curated markdown files')
    parser.add_argument('--wikipedia-topics', nargs='*',
                       help='Specific Wikipedia topics to index')
    parser.add_argument('--skip-wikipedia', action='store_true',
                       help='Skip Wikipedia indexing')
    parser.add_argument('--skip-curated', action='store_true',
                       help='Skip curated content indexing')
    parser.add_argument('--chunk-size', type=int, default=1000,
                       help='Chunk size for document splitting')
    parser.add_argument('--clear-existing', action='store_true',
                       help='Clear existing collection before indexing')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup
    setup_logging(args.verbose)
    logging.info("🚀 Starting context indexing process")
    
    # Load configuration
    try:
        config = load_config()
        logging.info("✅ Configuration loaded successfully")
    except Exception as e:
        logging.error(f"❌ Failed to load configuration: {str(e)}")
        sys.exit(1)
    
    # Initialize retriever
    try:
        retriever = RAGRetriever(
            chroma_path=config.get('CHROMA_PATH', './data/chroma'),
            embedding_model=config.get('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        )
        logging.info("✅ RAG retriever initialized")
    except Exception as e:
        logging.error(f"❌ Failed to initialize retriever: {str(e)}")
        sys.exit(1)
    
    # Clear existing collection if requested
    if args.clear_existing:
        try:
            retriever.clear_collection()
            logging.info("✅ Existing collection cleared")
        except Exception as e:
            logging.error(f"❌ Failed to clear collection: {str(e)}")
            sys.exit(1)
    
    all_documents = []
    
    # Load curated content
    if not args.skip_curated:
        logging.info("📚 Loading curated content...")
        curated_docs = load_markdown_files(args.curated_dir)
        all_documents.extend(curated_docs)
        logging.info(f"✅ Loaded {len(curated_docs)} curated documents")
    
    # Fetch Wikipedia articles
    if not args.skip_wikipedia:
        logging.info("🌐 Fetching Wikipedia articles...")
        
        if args.wikipedia_topics:
            topics = args.wikipedia_topics
        else:
            topics = get_default_wikipedia_topics()
        
        logging.info(f"Fetching {len(topics)} Wikipedia articles...")
        wikipedia_docs = fetch_wikipedia_articles(topics)
        all_documents.extend(wikipedia_docs)
        logging.info(f"✅ Fetched {len(wikipedia_docs)} Wikipedia articles")
    
    if not all_documents:
        logging.warning("⚠️  No documents to index")
        return
    
    # Process documents for indexing
    logging.info("🔄 Processing documents for indexing...")
    processed_docs = process_documents_for_indexing(all_documents, args.chunk_size)
    
    # Index documents
    logging.info("📤 Indexing documents into ChromaDB...")
    try:
        retriever.add_documents(processed_docs)
        logging.info(f"✅ Successfully indexed {len(processed_docs)} document chunks")
    except Exception as e:
        logging.error(f"❌ Failed to index documents: {str(e)}")
        sys.exit(1)
    
    # Verify indexing
    try:
        stats = retriever.get_collection_stats()
        logging.info(f"📊 Collection stats: {stats}")
    except Exception as e:
        logging.warning(f"Could not get collection stats: {str(e)}")
    
    # Test search
    logging.info("🧪 Testing search functionality...")
    try:
        test_results = retriever.search("viral memes", k=3)
        logging.info(f"Test search returned {len(test_results)} results")
        if test_results:
            for i, result in enumerate(test_results):
                logging.info(f"  {i+1}. {result.get('metadata', {}).get('title', 'Unknown')} "
                           f"(similarity: {result.get('similarity', 0):.3f})")
    except Exception as e:
        logging.error(f"Search test failed: {str(e)}")
    
    print("\n" + "="*50)
    print("✅ CONTEXT INDEXING COMPLETE")
    print("="*50)
    print(f"Total documents processed: {len(all_documents)}")
    print(f"Total chunks indexed: {len(processed_docs)}")
    print(f"Collection: {retriever.collection_name}")
    print("\nContext is now available for RAG queries!")

if __name__ == "__main__":
    main()
