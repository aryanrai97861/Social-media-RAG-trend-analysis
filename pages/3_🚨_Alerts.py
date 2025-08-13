import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from database.schema import get_engine
from alerts.notifier import AlertNotifier
from utils.config import load_config

st.set_page_config(
    page_title="Alerts & Monitoring",
    page_icon="🚨",
    layout="wide"
)

config = load_config()

def load_alert_history():
    """Load alert history from database"""
    try:
        engine = get_engine()
        
        # Create alerts table if it doesn't exist
        with engine.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    threshold_value REAL,
                    actual_value REAL,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            conn.commit()
        
        df = pd.read_sql("""
            SELECT * FROM alert_history
            ORDER BY created_at DESC
            LIMIT 100
        """, engine)
        
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at'])
        
        return df
    
    except Exception as e:
        st.error(f"Error loading alert history: {str(e)}")
        return pd.DataFrame()

def save_alert_config(config_data):
    """Save alert configuration"""
    try:
        with open('data/alert_config.json', 'w') as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving alert config: {str(e)}")
        return False

def load_alert_config():
    """Load alert configuration"""
    try:
        with open('data/alert_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Default configuration
        return {
            'trend_threshold': 2.0,
            'growth_threshold': 1.0,
            'volume_threshold': 100,
            'keywords': [],
            'enabled': True,
            'notification_methods': ['email'],
            'check_interval': 300  # 5 minutes
        }
    except Exception as e:
        st.error(f"Error loading alert config: {str(e)}")
        return {}

def create_alert(entity, alert_type, threshold_value, actual_value, message):
    """Create a new alert"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute("""
                INSERT INTO alert_history (entity, alert_type, threshold_value, actual_value, message)
                VALUES (?, ?, ?, ?, ?)
            """, (entity, alert_type, threshold_value, actual_value, message))
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Error creating alert: {str(e)}")
        return False

def main():
    st.title("🚨 Alerts & Monitoring")
    st.markdown("Configure alerts and monitor significant trend changes")
    
    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Configuration", "📋 Active Alerts", "📊 Alert History", "🧪 Test Alerts"])
    
    with tab1:
        st.subheader("Alert Configuration")
        
        # Load current configuration
        current_config = load_alert_config()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🎯 Threshold Settings")
            
            trend_threshold = st.number_input(
                "Trend Score Threshold (σ)",
                min_value=0.5,
                max_value=10.0,
                value=current_config.get('trend_threshold', 2.0),
                step=0.1,
                help="Alert when trend score exceeds this value"
            )
            
            growth_threshold = st.number_input(
                "Growth Rate Threshold (%)",
                min_value=0.1,
                max_value=10.0,
                value=current_config.get('growth_threshold', 1.0),
                step=0.1,
                help="Alert when growth rate exceeds this percentage"
            )
            
            volume_threshold = st.number_input(
                "Volume Threshold (mentions)",
                min_value=10,
                max_value=10000,
                value=current_config.get('volume_threshold', 100),
                step=10,
                help="Alert when mention count exceeds this value"
            )
            
            check_interval = st.selectbox(
                "Check Interval",
                [60, 300, 900, 1800, 3600],  # 1min, 5min, 15min, 30min, 1hour
                index=1,
                format_func=lambda x: f"{x//60} minutes" if x < 3600 else f"{x//3600} hour(s)"
            )
        
        with col2:
            st.markdown("### 🔔 Notification Settings")
            
            # Keywords to monitor
            keywords_text = st.text_area(
                "Keywords to Monitor (one per line)",
                value="\n".join(current_config.get('keywords', [])),
                height=100,
                help="Enter keywords that should trigger alerts"
            )
            keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
            
            # Notification methods
            notification_methods = st.multiselect(
                "Notification Methods",
                ['email', 'webhook', 'discord'],
                default=current_config.get('notification_methods', ['email'])
            )
            
            # Email settings
            if 'email' in notification_methods:
                st.markdown("**Email Configuration**")
                email_enabled = bool(config.get('ALERT_EMAIL_TO'))
                if email_enabled:
                    st.success(f"✅ Email alerts configured for: {config.get('ALERT_EMAIL_TO', 'Not configured')}")
                else:
                    st.warning("⚠️ Email not configured. Add email settings to environment variables.")
            
            # Webhook settings
            if 'webhook' in notification_methods:
                st.markdown("**Webhook Configuration**")
                webhook_url = config.get('ALERT_WEBHOOK_URL')
                if webhook_url:
                    st.success("✅ Webhook URL configured")
                else:
                    st.warning("⚠️ Webhook URL not configured. Add ALERT_WEBHOOK_URL to environment variables.")
            
            # Global enable/disable
            alerts_enabled = st.toggle("Enable Alerts", value=current_config.get('enabled', True))
        
        # Save configuration
        if st.button("💾 Save Alert Configuration", type="primary"):
            new_config = {
                'trend_threshold': trend_threshold,
                'growth_threshold': growth_threshold,
                'volume_threshold': volume_threshold,
                'keywords': keywords,
                'enabled': alerts_enabled,
                'notification_methods': notification_methods,
                'check_interval': check_interval
            }
            
            if save_alert_config(new_config):
                st.success("✅ Alert configuration saved successfully!")
                st.rerun()
        
        # Configuration preview
        st.markdown("### 📋 Current Configuration Preview")
        st.json(current_config)
    
    with tab2:
        st.subheader("📋 Active Monitoring")
        
        # Current trending topics that might trigger alerts
        try:
            engine = get_engine()
            current_config = load_alert_config()
            
            # Get current trends that exceed thresholds
            trending_df = pd.read_sql(f"""
                SELECT entity, trend_score, growth_rate, current_count, created_at, platform
                FROM trends
                WHERE trend_score >= {current_config.get('trend_threshold', 2.0)}
                   OR growth_rate >= {current_config.get('growth_threshold', 1.0) / 100}
                   OR current_count >= {current_config.get('volume_threshold', 100)}
                ORDER BY trend_score DESC
                LIMIT 20
            """, engine)
            
            if not trending_df.empty:
                st.success(f"🔍 Monitoring {len(trending_df)} topics exceeding alert thresholds")
                
                for idx, trend in trending_df.iterrows():
                    with st.expander(f"🚨 {trend['entity']} - Score: {trend['trend_score']:.2f}"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Trend Score", f"{trend['trend_score']:.2f}σ")
                            if trend['trend_score'] >= current_config.get('trend_threshold', 2.0):
                                st.error("⚠️ Exceeds threshold!")
                        
                        with col2:
                            st.metric("Growth Rate", f"{trend['growth_rate']:.1%}")
                            if trend['growth_rate'] >= current_config.get('growth_threshold', 1.0) / 100:
                                st.error("⚠️ Exceeds threshold!")
                        
                        with col3:
                            st.metric("Mentions", trend['current_count'])
                            if trend['current_count'] >= current_config.get('volume_threshold', 100):
                                st.error("⚠️ Exceeds threshold!")
                        
                        st.write(f"**Platform:** {trend['platform']}")
                        st.write(f"**Last Updated:** {trend['created_at']}")
                        
                        # Manual alert trigger
                        if st.button(f"🚨 Send Alert for {trend['entity']}", key=f"alert_{idx}"):
                            success = create_alert(
                                trend['entity'],
                                'manual',
                                current_config.get('trend_threshold', 2.0),
                                trend['trend_score'],
                                f"Manual alert triggered for {trend['entity']} with trend score {trend['trend_score']:.2f}"
                            )
                            if success:
                                st.success("Alert created!")
                                st.rerun()
            
            else:
                st.info("No topics currently exceed alert thresholds.")
        
        except Exception as e:
            st.error(f"Error loading monitoring data: {str(e)}")
        
        # System status
        st.markdown("### 🖥️ System Status")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if current_config.get('enabled', False):
                st.success("🟢 Alerts Enabled")
            else:
                st.error("🔴 Alerts Disabled")
        
        with col2:
            methods = current_config.get('notification_methods', [])
            st.info(f"📬 Methods: {', '.join(methods) if methods else 'None'}")
        
        with col3:
            interval = current_config.get('check_interval', 300)
            st.info(f"⏱️ Check Every: {interval//60} min")
    
    with tab3:
        st.subheader("📊 Alert History")
        
        # Load and display alert history
        alert_history = load_alert_history()
        
        if not alert_history.empty:
            # Summary stats
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_alerts = len(alert_history)
                st.metric("Total Alerts", total_alerts)
            
            with col2:
                recent_alerts = len(alert_history[
                    alert_history['created_at'] > datetime.now() - timedelta(days=1)
                ])
                st.metric("Last 24h", recent_alerts)
            
            with col3:
                active_alerts = len(alert_history[alert_history['status'] == 'active'])
                st.metric("Active", active_alerts)
            
            with col4:
                avg_score = alert_history['actual_value'].mean()
                st.metric("Avg Score", f"{avg_score:.1f}")
            
            # Filters
            col1, col2, col3 = st.columns(3)
            with col1:
                alert_types = ['All'] + alert_history['alert_type'].unique().tolist()
                selected_type = st.selectbox("Alert Type", alert_types)
            
            with col2:
                date_range = st.selectbox("Date Range", 
                    ['All Time', 'Last 24 Hours', 'Last 7 Days', 'Last 30 Days'])
            
            with col3:
                status_filter = st.selectbox("Status", ['All', 'active', 'resolved'])
            
            # Apply filters
            filtered_alerts = alert_history.copy()
            
            if selected_type != 'All':
                filtered_alerts = filtered_alerts[filtered_alerts['alert_type'] == selected_type]
            
            if date_range != 'All Time':
                days_map = {
                    'Last 24 Hours': 1,
                    'Last 7 Days': 7,
                    'Last 30 Days': 30
                }
                cutoff_date = datetime.now() - timedelta(days=days_map[date_range])
                filtered_alerts = filtered_alerts[filtered_alerts['created_at'] >= cutoff_date]
            
            if status_filter != 'All':
                filtered_alerts = filtered_alerts[filtered_alerts['status'] == status_filter]
            
            # Display alerts
            if not filtered_alerts.empty:
                for idx, alert in filtered_alerts.iterrows():
                    with st.expander(
                        f"{alert['alert_type'].title()} Alert: {alert['entity']} - {alert['created_at'].strftime('%Y-%m-%d %H:%M')}"
                    ):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Message:** {alert['message']}")
                            st.write(f"**Entity:** {alert['entity']}")
                            st.write(f"**Threshold:** {alert['threshold_value']}")
                            st.write(f"**Actual Value:** {alert['actual_value']}")
                        
                        with col2:
                            status_color = "🟢" if alert['status'] == 'resolved' else "🔴"
                            st.write(f"**Status:** {status_color} {alert['status'].title()}")
                            
                            if alert['status'] == 'active':
                                if st.button(f"Mark Resolved", key=f"resolve_{alert['id']}"):
                                    # Update status
                                    try:
                                        engine = get_engine()
                                        with engine.connect() as conn:
                                            conn.execute(
                                                "UPDATE alert_history SET status = 'resolved' WHERE id = ?",
                                                (alert['id'],)
                                            )
                                            conn.commit()
                                        st.success("Alert marked as resolved!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error updating alert: {str(e)}")
            else:
                st.info("No alerts match the selected criteria.")
        
        else:
            st.info("No alert history available.")
    
    with tab4:
        st.subheader("🧪 Test Alert System")
        
        # Test notification methods
        st.markdown("Test your notification configuration:")
        
        test_entity = st.text_input("Test Entity", value="test_topic")
        test_message = st.text_area("Test Message", value="This is a test alert from the Social Media RAG system.")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📧 Test Email Alert"):
                try:
                    notifier = AlertNotifier()
                    success = notifier.send_email(
                        subject=f"Test Alert: {test_entity}",
                        body=test_message
                    )
                    if success:
                        st.success("✅ Email sent successfully!")
                    else:
                        st.error("❌ Email sending failed. Check configuration.")
                except Exception as e:
                    st.error(f"Email test error: {str(e)}")
        
        with col2:
            if st.button("🌐 Test Webhook Alert"):
                try:
                    notifier = AlertNotifier()
                    success = notifier.send_webhook({
                        'entity': test_entity,
                        'message': test_message,
                        'timestamp': datetime.now().isoformat(),
                        'type': 'test'
                    })
                    if success:
                        st.success("✅ Webhook sent successfully!")
                    else:
                        st.error("❌ Webhook sending failed. Check configuration.")
                except Exception as e:
                    st.error(f"Webhook test error: {str(e)}")
        
        with col3:
            if st.button("💾 Test Database Alert"):
                success = create_alert(
                    test_entity,
                    'test',
                    1.0,
                    2.0,
                    test_message
                )
                if success:
                    st.success("✅ Database alert created!")
                    st.rerun()
                else:
                    st.error("❌ Database alert creation failed.")
        
        # Alert simulation
        st.markdown("### 🎭 Simulate Alert Conditions")
        
        if st.button("🚨 Simulate High Trend Alert"):
            # Create a simulated high-trend alert
            create_alert(
                "simulated_viral_topic",
                "trend_spike",
                2.0,
                4.5,
                "Simulated viral topic detected with trend score 4.5σ - significantly above threshold of 2.0σ"
            )
            st.success("Simulated alert created! Check the Alert History tab.")
            st.rerun()

if __name__ == "__main__":
    main()
