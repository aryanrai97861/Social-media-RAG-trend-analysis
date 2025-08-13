import streamlit as st
from datetime import datetime
import pandas as pd

def trend_card(trend_data):
    """Create a trend card component"""
    entity = trend_data.get('entity', 'Unknown')
    trend_score = trend_data.get('trend_score', 0)
    current_count = trend_data.get('current_count', 0)
    growth_rate = trend_data.get('growth_rate', 0)
    platform = trend_data.get('platform', 'Unknown')
    
    # Determine trend status
    if trend_score >= 3.0:
        status = "🔥 VIRAL"
        status_color = "red"
    elif trend_score >= 2.0:
        status = "📈 TRENDING"
        status_color = "orange"
    elif trend_score >= 1.0:
        status = "📊 RISING"
        status_color = "blue"
    else:
        status = "📉 STABLE"
        status_color = "green"
    
    # Create card
    with st.container():
        st.markdown(f"""
        <div style="
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <h4 style="color: {status_color}; margin: 0 0 10px 0;">{entity}</h4>
            <p style="margin: 5px 0; font-size: 14px;"><strong>{status}</strong></p>
            <p style="margin: 5px 0; font-size: 12px;">Score: {trend_score:.2f}σ</p>
            <p style="margin: 5px 0; font-size: 12px;">Mentions: {current_count:,}</p>
            <p style="margin: 5px 0; font-size: 12px;">Growth: {growth_rate:.1%}</p>
            <p style="margin: 5px 0; font-size: 12px; color: #666;">Platform: {platform.title()}</p>
        </div>
        """, unsafe_allow_html=True)

def post_card(post_data):
    """Create a social media post card"""
    platform = post_data.get('platform', 'unknown')
    author = post_data.get('author', 'Unknown')
    text = post_data.get('text', '')
    created_at = post_data.get('created_at', datetime.now())
    url = post_data.get('url', '')
    hashtags = post_data.get('hashtags', '')
    
    # Truncate text for display
    display_text = text[:200] + "..." if len(text) > 200 else text
    
    # Platform emoji
    platform_emoji = {
        'reddit': '📱',
        'rss': '📰',
        'twitter': '🐦',
        'x': '❌'
    }.get(platform.lower(), '📄')
    
    with st.expander(f"{platform_emoji} {platform.title()} - {created_at.strftime('%Y-%m-%d %H:%M')}"):
        st.write(display_text)
        
        col1, col2 = st.columns(2)
        with col1:
            if author:
                st.text(f"👤 Author: {author}")
            if hashtags:
                hashtag_list = hashtags.split(',')[:3]
                st.text(f"🏷️ Tags: {', '.join(hashtag_list)}")
        
        with col2:
            if url:
                st.link_button("🔗 View Original", url)

def metric_card(title, value, delta=None, delta_color="normal"):
    """Create a metric card with optional delta"""
    st.metric(
        label=title,
        value=value,
        delta=delta,
        delta_color=delta_color
    )

def alert_card(alert_data):
    """Create an alert card"""
    entity = alert_data.get('entity', 'Unknown')
    alert_type = alert_data.get('alert_type', 'Unknown')
    actual_value = alert_data.get('actual_value', 0)
    threshold_value = alert_data.get('threshold_value', 0)
    message = alert_data.get('message', 'No message')
    created_at = alert_data.get('created_at', datetime.now())
    status = alert_data.get('status', 'active')
    
    # Alert severity based on how much it exceeds threshold
    if isinstance(actual_value, (int, float)) and isinstance(threshold_value, (int, float)):
        severity_ratio = actual_value / max(threshold_value, 0.1)
        if severity_ratio >= 3:
            severity = "🚨 CRITICAL"
            color = "#ff4444"
        elif severity_ratio >= 2:
            severity = "⚠️ HIGH"
            color = "#ff8800"
        elif severity_ratio >= 1.5:
            severity = "📢 MEDIUM"
            color = "#ffaa00"
        else:
            severity = "ℹ️ LOW"
            color = "#0088ff"
    else:
        severity = "📢 ALERT"
        color = "#0088ff"
    
    status_emoji = "🟢" if status == "resolved" else "🔴"
    
    st.markdown(f"""
    <div style="
        border-left: 4px solid {color};
        padding: 15px;
        margin: 10px 0;
        background-color: #f8f9fa;
        border-radius: 0 8px 8px 0;
    ">
        <h4 style="color: {color}; margin: 0 0 10px 0;">{severity} {entity}</h4>
        <p style="margin: 5px 0;"><strong>Type:</strong> {alert_type.title()}</p>
        <p style="margin: 5px 0;"><strong>Message:</strong> {message}</p>
        <p style="margin: 5px 0;"><strong>Value:</strong> {actual_value} (Threshold: {threshold_value})</p>
        <p style="margin: 5px 0;"><strong>Time:</strong> {created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p style="margin: 5px 0;"><strong>Status:</strong> {status_emoji} {status.title()}</p>
    </div>
    """, unsafe_allow_html=True)

def context_card(context_data):
    """Create a context information card"""
    title = context_data.get('title', 'Context Information')
    content = context_data.get('content', '')
    source = context_data.get('source', 'Unknown')
    url = context_data.get('url', '')
    relevance_score = context_data.get('relevance_score', 0)
    
    # Truncate content for display
    display_content = content[:300] + "..." if len(content) > 300 else content
    
    with st.expander(f"📚 {title} (Relevance: {relevance_score:.2f})"):
        st.write(display_content)
        st.text(f"📖 Source: {source}")
        if url:
            st.link_button("🔗 View Full Source", url)

def summary_card(title, data_dict):
    """Create a summary statistics card"""
    st.markdown(f"### {title}")
    
    cols = st.columns(len(data_dict))
    for i, (key, value) in enumerate(data_dict.items()):
        with cols[i]:
            if isinstance(value, dict):
                st.metric(key, value.get('value', 'N/A'), delta=value.get('delta'))
            else:
                st.metric(key, value)

def platform_stats_card(platform_data):
    """Create platform statistics card"""
    platform = platform_data.get('platform', 'Unknown')
    total_posts = platform_data.get('total_posts', 0)
    trending_topics = platform_data.get('trending_topics', 0)
    avg_engagement = platform_data.get('avg_engagement', 0)
    last_updated = platform_data.get('last_updated', datetime.now())
    
    # Platform-specific styling
    platform_colors = {
        'reddit': '#ff4500',
        'rss': '#ff8c00',
        'twitter': '#1da1f2',
        'x': '#000000'
    }
    
    color = platform_colors.get(platform.lower(), '#6c757d')
    
    st.markdown(f"""
    <div style="
        border: 2px solid {color};
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        background: linear-gradient(135deg, {color}15 0%, {color}05 100%);
    ">
        <h3 style="color: {color}; margin: 0 0 15px 0;">{platform.title()}</h3>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
            <div>
                <p style="margin: 5px 0; font-weight: bold;">Total Posts</p>
                <p style="margin: 0; font-size: 24px; color: {color};">{total_posts:,}</p>
            </div>
            <div>
                <p style="margin: 5px 0; font-weight: bold;">Trending Topics</p>
                <p style="margin: 0; font-size: 24px; color: {color};">{trending_topics}</p>
            </div>
        </div>
        <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
            Last updated: {last_updated.strftime('%Y-%m-%d %H:%M')}
        </p>
    </div>
    """, unsafe_allow_html=True)

def trending_hashtag_card(hashtag_data):
    """Create trending hashtag card"""
    hashtag = hashtag_data.get('hashtag', '#unknown')
    count = hashtag_data.get('count', 0)
    growth = hashtag_data.get('growth', 0)
    sentiment = hashtag_data.get('sentiment', 'neutral')
    
    # Sentiment color coding
    sentiment_colors = {
        'positive': '#28a745',
        'negative': '#dc3545',
        'neutral': '#6c757d'
    }
    
    color = sentiment_colors.get(sentiment, '#6c757d')
    
    with st.container():
        st.markdown(f"""
        <div style="
            border: 1px solid {color};
            border-radius: 8px;
            padding: 12px;
            margin: 8px 0;
            background-color: {color}10;
        ">
            <h4 style="color: {color}; margin: 0 0 8px 0;">{hashtag}</h4>
            <p style="margin: 3px 0; font-size: 14px;">Mentions: <strong>{count:,}</strong></p>
            <p style="margin: 3px 0; font-size: 14px;">Growth: <strong>{growth:+.1%}</strong></p>
            <p style="margin: 3px 0; font-size: 14px;">Sentiment: <strong style="color: {color};">{sentiment.title()}</strong></p>
        </div>
        """, unsafe_allow_html=True)
