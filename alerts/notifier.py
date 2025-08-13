import os
import smtplib
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests

class AlertNotifier:
    """Handles sending notifications for trend alerts"""
    
    def __init__(self):
        self.smtp_server = os.getenv('ALERT_EMAIL_SMTP', 'smtp.gmail.com')
        self.smtp_port = 587
        self.email_user = os.getenv('ALERT_EMAIL_USER')
        self.email_pass = os.getenv('ALERT_EMAIL_PASS')
        self.email_to = os.getenv('ALERT_EMAIL_TO')
        self.webhook_url = os.getenv('ALERT_WEBHOOK_URL')
        
    def send_email(self, subject: str, body: str, html_body: str = None) -> bool:
        """
        Send email notification
        
        Args:
            subject: Email subject line
            body: Plain text body
            html_body: HTML body (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not all([self.email_user, self.email_pass, self.email_to]):
                logging.warning("Email credentials not configured")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_user
            msg['To'] = self.email_to
            
            # Add plain text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Connect and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_pass)
                server.send_message(msg)
            
            logging.info(f"Email sent successfully to {self.email_to}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_webhook(self, data: Dict[str, Any]) -> bool:
        """
        Send webhook notification
        
        Args:
            data: Dictionary of data to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.webhook_url:
                logging.warning("Webhook URL not configured")
                return False
            
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
            
            # Send POST request
            response = requests.post(
                self.webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            response.raise_for_status()
            logging.info(f"Webhook sent successfully to {self.webhook_url}")
            return True
            
        except requests.RequestException as e:
            logging.error(f"Failed to send webhook: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error sending webhook: {str(e)}")
            return False
    
    def send_discord_webhook(self, webhook_url: str, content: str, embeds: List[Dict] = None) -> bool:
        """
        Send Discord webhook notification
        
        Args:
            webhook_url: Discord webhook URL
            content: Message content
            embeds: List of embed objects
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                'content': content,
                'username': 'Social Media RAG Alerts'
            }
            
            if embeds:
                payload['embeds'] = embeds
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            response.raise_for_status()
            logging.info("Discord webhook sent successfully")
            return True
            
        except requests.RequestException as e:
            logging.error(f"Failed to send Discord webhook: {str(e)}")
            return False
    
    def send_trend_alert(self, trend_data: Dict[str, Any], alert_type: str = "high_trend") -> bool:
        """
        Send alert for trending topic
        
        Args:
            trend_data: Dictionary containing trend information
            alert_type: Type of alert being sent
            
        Returns:
            True if any notification method succeeded
        """
        entity = trend_data.get('entity', 'Unknown')
        trend_score = trend_data.get('trend_score', 0)
        platform = trend_data.get('platform', 'Unknown')
        current_count = trend_data.get('current_count', 0)
        growth_rate = trend_data.get('growth_rate', 0)
        
        # Create alert content
        subject = f"🚨 Trending Alert: {entity}"
        
        body = f"""
Social Media RAG Alert

Entity: {entity}
Platform: {platform.title()}
Trend Score: {trend_score:.2f}σ
Current Mentions: {current_count:,}
Growth Rate: {growth_rate:.1%}
Alert Type: {alert_type.replace('_', ' ').title()}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This topic is trending significantly above normal levels. 
Check the dashboard for more details: http://localhost:5000

---
Social Media RAG System
"""
        
        html_body = f"""
<html>
<body>
    <h2>🚨 Social Media RAG Alert</h2>
    
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <h3>{entity}</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px; font-weight: bold;">Platform:</td>
                <td style="padding: 8px;">{platform.title()}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Trend Score:</td>
                <td style="padding: 8px; color: #dc3545;"><strong>{trend_score:.2f}σ</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Current Mentions:</td>
                <td style="padding: 8px;">{current_count:,}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Growth Rate:</td>
                <td style="padding: 8px;">{growth_rate:.1%}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Alert Type:</td>
                <td style="padding: 8px;">{alert_type.replace('_', ' ').title()}</td>
            </tr>
        </table>
    </div>
    
    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <p>This topic is trending significantly above normal levels.</p>
    
    <p><a href="http://localhost:5000" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">View Dashboard</a></p>
    
    <hr style="margin-top: 30px;">
    <p style="color: #666; font-size: 12px;">Social Media RAG System</p>
</body>
</html>
"""
        
        # Try multiple notification methods
        success = False
        
        # Email notification
        if self.send_email(subject, body, html_body):
            success = True
        
        # Webhook notification
        webhook_data = {
            'alert_type': alert_type,
            'entity': entity,
            'platform': platform,
            'trend_score': trend_score,
            'current_count': current_count,
            'growth_rate': growth_rate,
            'timestamp': datetime.now().isoformat(),
            'message': f"Trending alert for {entity} with score {trend_score:.2f}σ"
        }
        
        if self.send_webhook(webhook_data):
            success = True
        
        return success
    
    def send_system_alert(self, message: str, severity: str = "info") -> bool:
        """
        Send system status alert
        
        Args:
            message: Alert message
            severity: Alert severity (info, warning, error, critical)
            
        Returns:
            True if any notification method succeeded
        """
        severity_emojis = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }
        
        emoji = severity_emojis.get(severity, 'ℹ️')
        subject = f"{emoji} Social Media RAG System Alert"
        
        body = f"""
System Alert

Severity: {severity.upper()}
Message: {message}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
Social Media RAG System
"""
        
        # Try email first
        success = False
        if self.send_email(subject, body):
            success = True
        
        # Try webhook
        webhook_data = {
            'alert_type': 'system',
            'severity': severity,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if self.send_webhook(webhook_data):
            success = True
        
        return success
    
    def send_digest_alert(self, trends: List[Dict[str, Any]], period: str = "daily") -> bool:
        """
        Send digest of trending topics
        
        Args:
            trends: List of trending topics
            period: Digest period (daily, weekly)
            
        Returns:
            True if successful
        """
        if not trends:
            return False
        
        subject = f"📊 {period.title()} Trending Topics Digest"
        
        # Create text version
        body = f"""
{period.title()} Trending Topics Digest

Top {len(trends)} trending topics:

"""
        
        for i, trend in enumerate(trends, 1):
            body += f"{i}. {trend.get('entity', 'Unknown')} ({trend.get('platform', 'Unknown')})\n"
            body += f"   Score: {trend.get('trend_score', 0):.2f}σ | Mentions: {trend.get('current_count', 0):,}\n\n"
        
        body += f"""
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

View full dashboard: http://localhost:5000

---
Social Media RAG System
"""
        
        # Create HTML version
        html_body = f"""
<html>
<body>
    <h2>📊 {period.title()} Trending Topics Digest</h2>
    
    <p>Top {len(trends)} trending topics:</p>
    
    <ol>
"""
        
        for trend in trends:
            html_body += f"""
        <li>
            <strong>{trend.get('entity', 'Unknown')}</strong> 
            <span style="color: #666;">({trend.get('platform', 'Unknown')})</span>
            <br>
            <small>
                Score: <strong>{trend.get('trend_score', 0):.2f}σ</strong> | 
                Mentions: <strong>{trend.get('current_count', 0):,}</strong>
            </small>
        </li>
"""
        
        html_body += f"""
    </ol>
    
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <p><a href="http://localhost:5000" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">View Full Dashboard</a></p>
    
    <hr>
    <p style="color: #666; font-size: 12px;">Social Media RAG System</p>
</body>
</html>
"""
        
        return self.send_email(subject, body, html_body)
    
    def test_notifications(self) -> Dict[str, bool]:
        """
        Test all notification methods
        
        Returns:
            Dictionary with test results for each method
        """
        results = {}
        
        test_message = "This is a test notification from Social Media RAG system"
        
        # Test email
        results['email'] = self.send_email(
            "🧪 Test Email Alert",
            test_message
        )
        
        # Test webhook
        results['webhook'] = self.send_webhook({
            'test': True,
            'message': test_message,
            'timestamp': datetime.now().isoformat()
        })
        
        return results

# Global notifier instance
_notifier = None

def get_notifier() -> AlertNotifier:
    """Get or create global notifier instance"""
    global _notifier
    if _notifier is None:
        _notifier = AlertNotifier()
    return _notifier

def send_trend_alert(trend_data: Dict[str, Any], alert_type: str = "high_trend") -> bool:
    """Convenience function to send trend alert"""
    notifier = get_notifier()
    return notifier.send_trend_alert(trend_data, alert_type)

def send_system_alert(message: str, severity: str = "info") -> bool:
    """Convenience function to send system alert"""
    notifier = get_notifier()
    return notifier.send_system_alert(message, severity)
