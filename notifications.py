"""
Real-Time Notifications and Alerts System for LeadNgN
Provides instant alerts for high-value lead discoveries and campaign milestones
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from models import Lead, ScrapingSession, db
import logging

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manages real-time notifications and alerts for LeadNgN"""
    
    def __init__(self):
        self.slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
        self.email_alerts_enabled = os.environ.get('EMAIL_ALERTS_ENABLED', 'false').lower() == 'true'
        self.high_score_threshold = int(os.environ.get('HIGH_SCORE_THRESHOLD', '80'))
        
    def send_high_value_lead_alert(self, lead: Lead) -> Dict[str, Any]:
        """Send alert when a high-value lead is discovered"""
        try:
            if lead.quality_score >= self.high_score_threshold:
                alert_data = {
                    'type': 'high_value_lead',
                    'lead_id': lead.id,
                    'company': lead.company_name,
                    'industry': lead.industry,
                    'score': lead.quality_score,
                    'contact': lead.contact_name,
                    'email': lead.email,
                    'phone': lead.phone,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Send Slack notification
                if self.slack_webhook_url:
                    self._send_slack_alert(alert_data)
                
                # Log the alert
                logger.info(f"High-value lead alert sent for {lead.company_name} (Score: {lead.quality_score})")
                
                return {'success': True, 'alert_sent': True}
            
            return {'success': True, 'alert_sent': False, 'reason': 'Score below threshold'}
            
        except Exception as e:
            logger.error(f"Failed to send high-value lead alert: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_scraping_completion_alert(self, session: ScrapingSession) -> Dict[str, Any]:
        """Send alert when scraping session completes with results"""
        try:
            if session.status == 'completed' and session.leads_found > 0:
                high_quality_count = Lead.query.filter(
                    Lead.source.like(f'%{session.id}%'),
                    Lead.quality_score >= self.high_score_threshold
                ).count()
                
                alert_data = {
                    'type': 'scraping_completion',
                    'session_id': session.id,
                    'session_name': session.session_name,
                    'total_leads': session.leads_found,
                    'high_quality_leads': high_quality_count,
                    'industry': session.target_industry,
                    'location': session.target_location,
                    'success_rate': session.success_rate,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                if self.slack_webhook_url:
                    self._send_slack_scraping_alert(alert_data)
                
                logger.info(f"Scraping completion alert sent for session {session.session_name}")
                return {'success': True, 'alert_sent': True}
            
            return {'success': True, 'alert_sent': False, 'reason': 'No leads found or session not completed'}
            
        except Exception as e:
            logger.error(f"Failed to send scraping completion alert: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_response_rate_alert(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send alert for significant response rate changes"""
        try:
            response_rate = campaign_data.get('response_rate', 0)
            threshold = float(os.environ.get('RESPONSE_RATE_THRESHOLD', '15.0'))
            
            if response_rate >= threshold:
                alert_data = {
                    'type': 'high_response_rate',
                    'campaign': campaign_data.get('campaign_name', 'Unknown'),
                    'response_rate': response_rate,
                    'responses': campaign_data.get('responses', 0),
                    'sent': campaign_data.get('sent', 0),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                if self.slack_webhook_url:
                    self._send_slack_response_alert(alert_data)
                
                return {'success': True, 'alert_sent': True}
            
            return {'success': True, 'alert_sent': False, 'reason': 'Response rate below threshold'}
            
        except Exception as e:
            logger.error(f"Failed to send response rate alert: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _send_slack_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send high-value lead alert to Slack"""
        try:
            slack_message = {
                "text": f"🎯 High-Value Lead Discovered!",
                "attachments": [
                    {
                        "color": "good",
                        "fields": [
                            {
                                "title": "Company",
                                "value": alert_data['company'],
                                "short": True
                            },
                            {
                                "title": "Industry", 
                                "value": alert_data['industry'],
                                "short": True
                            },
                            {
                                "title": "Quality Score",
                                "value": f"{alert_data['score']}/100",
                                "short": True
                            },
                            {
                                "title": "Contact",
                                "value": alert_data['contact'] or "Not specified",
                                "short": True
                            },
                            {
                                "title": "Email",
                                "value": alert_data['email'] or "Not available",
                                "short": False
                            },
                            {
                                "title": "Phone",
                                "value": alert_data['phone'] or "Not available",
                                "short": False
                            }
                        ],
                        "footer": "LeadNGN Alert System",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            response = requests.post(self.slack_webhook_url, json=slack_message, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {str(e)}")
            return False
    
    def _send_slack_scraping_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send scraping completion alert to Slack"""
        try:
            slack_message = {
                "text": f"🔍 Scraping Session Completed!",
                "attachments": [
                    {
                        "color": "warning",
                        "fields": [
                            {
                                "title": "Session",
                                "value": alert_data['session_name'],
                                "short": True
                            },
                            {
                                "title": "Industry",
                                "value": alert_data['industry'] or "All",
                                "short": True
                            },
                            {
                                "title": "Total Leads",
                                "value": str(alert_data['total_leads']),
                                "short": True
                            },
                            {
                                "title": "High-Quality Leads",
                                "value": str(alert_data['high_quality_leads']),
                                "short": True
                            },
                            {
                                "title": "Success Rate",
                                "value": f"{alert_data['success_rate']:.1f}%",
                                "short": True
                            },
                            {
                                "title": "Location",
                                "value": alert_data['location'] or "Not specified",
                                "short": True
                            }
                        ],
                        "footer": "LeadNGN Scraping System",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            response = requests.post(self.slack_webhook_url, json=slack_message, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send Slack scraping alert: {str(e)}")
            return False
    
    def _send_slack_response_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send response rate alert to Slack"""
        try:
            slack_message = {
                "text": f"📈 High Response Rate Alert!",
                "attachments": [
                    {
                        "color": "#36a64f",
                        "fields": [
                            {
                                "title": "Campaign",
                                "value": alert_data['campaign'],
                                "short": True
                            },
                            {
                                "title": "Response Rate",
                                "value": f"{alert_data['response_rate']:.1f}%",
                                "short": True
                            },
                            {
                                "title": "Responses",
                                "value": f"{alert_data['responses']}/{alert_data['sent']}",
                                "short": True
                            }
                        ],
                        "footer": "LeadNGN Campaign Analytics",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            response = requests.post(self.slack_webhook_url, json=slack_message, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send Slack response alert: {str(e)}")
            return False
    
    def get_alert_settings(self) -> Dict[str, Any]:
        """Get current notification settings"""
        return {
            'slack_enabled': bool(self.slack_webhook_url),
            'email_alerts_enabled': self.email_alerts_enabled,
            'high_score_threshold': self.high_score_threshold,
            'response_rate_threshold': float(os.environ.get('RESPONSE_RATE_THRESHOLD', '15.0'))
        }
    
    def test_notifications(self) -> Dict[str, Any]:
        """Test notification system with sample data"""
        try:
            if self.slack_webhook_url:
                test_message = {
                    "text": "🧪 LeadNGN Notification Test",
                    "attachments": [
                        {
                            "color": "good",
                            "text": "Notification system is working correctly!",
                            "footer": "LeadNGN Test Alert",
                            "ts": int(datetime.utcnow().timestamp())
                        }
                    ]
                }
                
                response = requests.post(self.slack_webhook_url, json=test_message, timeout=10)
                
                if response.status_code == 200:
                    return {'success': True, 'message': 'Test notification sent successfully'}
                else:
                    return {'success': False, 'error': f'Slack webhook returned {response.status_code}'}
            else:
                return {'success': False, 'error': 'No Slack webhook URL configured'}
                
        except Exception as e:
            logger.error(f"Failed to test notifications: {str(e)}")
            return {'success': False, 'error': str(e)}


# Global notification manager instance
notification_manager = NotificationManager()