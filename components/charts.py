import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_trend_chart(data, title="Trend Analysis"):
    """Create a trend line chart"""
    fig = px.line(
        data,
        x='date',
        y='trend_score',
        color='entity',
        title=title,
        labels={'trend_score': 'Trend Score (σ)', 'date': 'Date'}
    )
    
    # Add threshold line
    fig.add_hline(
        y=2.0,
        line_dash="dash",
        line_color="red",
        annotation_text="Alert Threshold (2σ)"
    )
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Trend Score (σ)",
        hovermode='x unified'
    )
    
    return fig

def create_heatmap(data, x_col, y_col, value_col, title="Heatmap"):
    """Create a heatmap visualization"""
    fig = px.density_heatmap(
        data,
        x=x_col,
        y=y_col,
        z=value_col,
        title=title,
        color_continuous_scale="Viridis"
    )
    
    fig.update_layout(
        xaxis_title=x_col.replace('_', ' ').title(),
        yaxis_title=y_col.replace('_', ' ').title()
    )
    
    return fig

def create_sentiment_chart(data, title="Sentiment Distribution"):
    """Create sentiment analysis chart"""
    if 'sentiment' not in data.columns:
        return None
    
    sentiment_counts = data['sentiment'].value_counts()
    
    fig = px.pie(
        values=sentiment_counts.values,
        names=sentiment_counts.index,
        title=title,
        color_discrete_map={
            'positive': '#28a745',
            'negative': '#dc3545',
            'neutral': '#6c757d'
        }
    )
    
    return fig

def create_platform_comparison(data, title="Platform Comparison"):
    """Create platform comparison chart"""
    platform_stats = data.groupby('platform').agg({
        'trend_score': 'mean',
        'current_count': 'sum',
        'entity': 'count'
    }).reset_index()
    
    platform_stats.columns = ['Platform', 'Avg Trend Score', 'Total Mentions', 'Unique Topics']
    
    fig = px.bar(
        platform_stats,
        x='Platform',
        y='Total Mentions',
        title=title,
        color='Avg Trend Score',
        color_continuous_scale='Viridis'
    )
    
    return fig

def create_time_series_chart(data, date_col, value_col, title="Time Series"):
    """Create time series chart with moving average"""
    # Sort by date
    data_sorted = data.sort_values(date_col)
    
    # Calculate 7-day moving average
    data_sorted['moving_avg'] = data_sorted[value_col].rolling(window=7, min_periods=1).mean()
    
    fig = go.Figure()
    
    # Add actual values
    fig.add_trace(go.Scatter(
        x=data_sorted[date_col],
        y=data_sorted[value_col],
        mode='lines+markers',
        name='Actual',
        line=dict(color='lightblue', width=1),
        marker=dict(size=4)
    ))
    
    # Add moving average
    fig.add_trace(go.Scatter(
        x=data_sorted[date_col],
        y=data_sorted['moving_avg'],
        mode='lines',
        name='7-day Moving Average',
        line=dict(color='red', width=2)
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=value_col.replace('_', ' ').title(),
        hovermode='x unified'
    )
    
    return fig

def create_growth_rate_chart(data, title="Growth Rate Analysis"):
    """Create growth rate visualization"""
    if 'growth_rate' not in data.columns:
        return None
    
    # Create bins for growth rates
    data['growth_bin'] = pd.cut(
        data['growth_rate'],
        bins=[-np.inf, -0.5, -0.1, 0.1, 0.5, 1.0, np.inf],
        labels=['Large Decline', 'Decline', 'Stable', 'Growth', 'High Growth', 'Viral']
    )
    
    growth_counts = data['growth_bin'].value_counts()
    
    fig = px.bar(
        x=growth_counts.index,
        y=growth_counts.values,
        title=title,
        labels={'x': 'Growth Category', 'y': 'Number of Topics'},
        color=growth_counts.values,
        color_continuous_scale='RdYlGn'
    )
    
    return fig

def create_word_cloud_chart(text_data, title="Word Cloud"):
    """Create word frequency chart (alternative to word cloud)"""
    from collections import Counter
    import re
    
    # Simple word extraction
    words = []
    for text in text_data:
        words.extend(re.findall(r'\b[a-zA-Z]{3,}\b', text.lower()))
    
    # Remove common stop words
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'this', 'that'}
    words = [word for word in words if word not in stop_words]
    
    word_counts = Counter(words).most_common(20)
    
    if not word_counts:
        return None
    
    words, counts = zip(*word_counts)
    
    fig = px.bar(
        x=list(counts),
        y=list(words),
        orientation='h',
        title=title,
        labels={'x': 'Frequency', 'y': 'Words'}
    )
    
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    
    return fig

def create_engagement_scatter(data, title="Engagement vs Trend Score"):
    """Create scatter plot of engagement metrics vs trend scores"""
    if 'current_count' not in data.columns or 'trend_score' not in data.columns:
        return None
    
    fig = px.scatter(
        data,
        x='current_count',
        y='trend_score',
        size='growth_rate' if 'growth_rate' in data.columns else None,
        color='platform' if 'platform' in data.columns else None,
        hover_data=['entity'] if 'entity' in data.columns else None,
        title=title,
        labels={
            'current_count': 'Mention Count',
            'trend_score': 'Trend Score (σ)'
        }
    )
    
    # Add trend line
    if len(data) > 1:
        z = np.polyfit(data['current_count'], data['trend_score'], 1)
        p = np.poly1d(z)
        
        fig.add_trace(go.Scatter(
            x=data['current_count'].sort_values(),
            y=p(data['current_count'].sort_values()),
            mode='lines',
            name='Trend Line',
            line=dict(dash='dash', color='red')
        ))
    
    return fig
