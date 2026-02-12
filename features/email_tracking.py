"""
Email Tracking System for LeadNGN
Comprehensive email tracking with opens, clicks, and engagement analytics
"""

import logging
import uuid
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode
from models import Lead, db
import psycopg2
import psycopg2.extras
import os

logger = logging.getLogger(__name__)

class EmailTracker:
    """Comprehensive email tracking and analytics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://yourdomain.com"  # Update with your domain
    
    def generate_tracked_email(self, lead_id: int, template_type: str = 'introduction', 
                             user_id: str = 'system') -> Dict:
        """Generate consultant email with full tracking capabilities"""
        try:
            # Generate base consultant email
            from features.consultant_approach import consultant_approach
            email_data = consultant_approach.generate_consultant_email(lead_id, template_type)
            
            if not email_data.get('success'):
                return email_data
            
            # Create unique tracking ID
            tracking_id = str(uuid.uuid4())
            
            # Get lead information
            lead = Lead.query.get(lead_id)
            if not lead:
                return {'error': 'Lead not found'}
            
            # Extract email components
            email_body = email_data['email_data']['email_body']
            subject_line = email_data['email_data']['subject_options'][0]
            
            # Add tracking to all links
            tracked_email_body = self._add_tracking_to_links(email_body, tracking_id)
            
            # Add tracking pixel (invisible 1x1 image)
            tracking_pixel = f'<img src="{self.base_url}/track/open/{tracking_id}" width="1" height="1" style="display:none;" alt="" />'
            
            # Convert to HTML format and add tracking pixel
            html_email_body = self._convert_to_html(tracked_email_body)
            html_email_body += f'\n{tracking_pixel}'
            
            # Store email in tracking database
            sent_email_id = self._store_email_for_tracking(
                lead_id=lead_id,
                template_type=template_type,
                subject_line=subject_line,
                email_body=html_email_body,
                recipient_email=lead.email,
                tracking_id=tracking_id,
                sent_by=user_id
            )
            
            # Update email data with tracking information
            email_data['tracking'] = {
                'tracking_id': tracking_id,
                'sent_email_id': sent_email_id,
                'tracking_enabled': True,
                'tracking_pixel_url': f"{self.base_url}/track/open/{tracking_id}",
                'analytics_url': f"{self.base_url}/api/email-tracking-stats?email_id={sent_email_id}"
            }
            
            # Replace email body with tracked version
            email_data['email_data']['email_body'] = html_email_body
            email_data['email_data']['tracking_id'] = tracking_id
            
            return email_data
            
        except Exception as e:
            self.logger.error(f"Email tracking generation error for lead {lead_id}: {e}")
            return {'error': f'Failed to generate tracked email: {str(e)}'}
    
    def record_tracking_event(self, tracking_id: str, event_type: str, 
                            ip_address: str = None, user_agent: str = None, 
                            click_url: str = None, metadata: Dict = None) -> bool:
        """Record email tracking event"""
        try:
            # Get sent_email_id from tracking_id
            query = "SELECT id FROM sent_emails WHERE tracking_id = %s"
            
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cur = conn.cursor()
            cur.execute(query, (tracking_id,))
            result = cur.fetchone()
            
            if not result:
                self.logger.error(f"No email found for tracking ID: {tracking_id}")
                return False
            
            sent_email_id = result[0]
            
            # Insert tracking event
            insert_query = """
                INSERT INTO email_tracking_events 
                (sent_email_id, event_type, ip_address, user_agent, click_url, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cur.execute(insert_query, (
                sent_email_id, 
                event_type, 
                ip_address, 
                user_agent, 
                click_url, 
                psycopg2.extras.Json(metadata) if metadata else None
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            self.logger.info(f"Recorded {event_type} event for tracking ID: {tracking_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording tracking event: {e}")
            return False
    
    def get_email_tracking_stats(self, lead_id: int = None, days: int = 30, 
                               email_id: int = None) -> Dict:
        """Get comprehensive email tracking statistics"""
        try:
            base_query = """
                SELECT 
                    se.id,
                    se.lead_id,
                    se.template_type,
                    se.subject_line,
                    se.recipient_email,
                    se.sent_at,
                    se.sent_by,
                    l.company_name,
                    l.contact_name,
                    COUNT(CASE WHEN ete.event_type = 'open' THEN 1 END) as opens,
                    COUNT(CASE WHEN ete.event_type = 'click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN ete.event_type = 'reply' THEN 1 END) as replies,
                    MAX(CASE WHEN ete.event_type = 'open' THEN ete.event_timestamp END) as last_opened,
                    MAX(CASE WHEN ete.event_type = 'click' THEN ete.event_timestamp END) as last_clicked,
                    MIN(ete.event_timestamp) as first_interaction
                FROM sent_emails se
                LEFT JOIN lead l ON se.lead_id = l.id
                LEFT JOIN email_tracking_events ete ON se.id = ete.sent_email_id
                WHERE se.sent_at >= NOW() - INTERVAL '%s days'
            """
            
            params = [days]
            
            if lead_id:
                base_query += " AND se.lead_id = %s"
                params.append(lead_id)
            
            if email_id:
                base_query += " AND se.id = %s"
                params.append(email_id)
            
            base_query += """
                GROUP BY se.id, se.lead_id, se.template_type, se.subject_line, 
                         se.recipient_email, se.sent_at, se.sent_by, l.company_name, l.contact_name
                ORDER BY se.sent_at DESC
            """
            
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(base_query, params)
            emails = cur.fetchall()
            
            # Calculate summary statistics
            total_sent = len(emails)
            total_opens = sum(email['opens'] for email in emails)
            total_clicks = sum(email['clicks'] for email in emails)
            total_replies = sum(email['replies'] for email in emails)
            
            # Calculate rates
            open_rate = (total_opens / total_sent * 100) if total_sent > 0 else 0
            click_rate = (total_clicks / total_sent * 100) if total_sent > 0 else 0
            reply_rate = (total_replies / total_sent * 100) if total_sent > 0 else 0
            
            # Get engagement timeline
            timeline_query = """
                SELECT 
                    DATE(ete.event_timestamp) as date,
                    ete.event_type,
                    COUNT(*) as count
                FROM email_tracking_events ete
                JOIN sent_emails se ON ete.sent_email_id = se.id
                WHERE se.sent_at >= NOW() - INTERVAL '%s days'
            """
            
            timeline_params = [days]
            
            if lead_id:
                timeline_query += " AND se.lead_id = %s"
                timeline_params.append(lead_id)
            
            timeline_query += """
                GROUP BY DATE(ete.event_timestamp), ete.event_type
                ORDER BY date DESC
            """
            
            cur.execute(timeline_query, timeline_params)
            timeline_data = cur.fetchall()
            
            cur.close()
            conn.close()
            
            return {
                'success': True,
                'summary': {
                    'total_sent': total_sent,
                    'total_opens': total_opens,
                    'total_clicks': total_clicks,
                    'total_replies': total_replies,
                    'open_rate': round(open_rate, 2),
                    'click_rate': round(click_rate, 2),
                    'reply_rate': round(reply_rate, 2),
                    'engagement_score': round((open_rate + click_rate + reply_rate * 2) / 4, 2)
                },
                'emails': [dict(email) for email in emails],
                'timeline': [dict(event) for event in timeline_data],
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting email tracking stats: {e}")
            return {'error': f'Failed to get tracking stats: {str(e)}'}
    
    def get_lead_email_performance(self, lead_id: int) -> Dict:
        """Get email performance metrics for a specific lead"""
        try:
            stats = self.get_email_tracking_stats(lead_id=lead_id, days=365)  # Full year
            
            if not stats.get('success'):
                return stats
            
            emails = stats['emails']
            
            if not emails:
                return {
                    'lead_id': lead_id,
                    'total_emails_sent': 0,
                    'engagement_level': 'no_data',
                    'recommendations': ['Send initial consultant introduction email']
                }
            
            # Analyze engagement patterns
            total_emails = len(emails)
            engaged_emails = len([e for e in emails if e['opens'] > 0 or e['clicks'] > 0])
            engagement_rate = (engaged_emails / total_emails * 100) if total_emails > 0 else 0
            
            # Determine engagement level
            if engagement_rate >= 70:
                engagement_level = 'highly_engaged'
            elif engagement_rate >= 40:
                engagement_level = 'moderately_engaged'
            elif engagement_rate >= 20:
                engagement_level = 'low_engagement'
            else:
                engagement_level = 'unresponsive'
            
            # Generate recommendations
            recommendations = self._generate_engagement_recommendations(
                engagement_level, stats['summary'], emails
            )
            
            return {
                'lead_id': lead_id,
                'total_emails_sent': total_emails,
                'engagement_rate': round(engagement_rate, 2),
                'engagement_level': engagement_level,
                'last_email_sent': emails[0]['sent_at'] if emails else None,
                'best_performing_subject': self._get_best_subject_line(emails),
                'recommendations': recommendations,
                'summary_stats': stats['summary']
            }
            
        except Exception as e:
            self.logger.error(f"Error getting lead email performance: {e}")
            return {'error': f'Failed to get lead performance: {str(e)}'}
    
    def _add_tracking_to_links(self, email_body: str, tracking_id: str) -> str:
        """Add click tracking to all URLs in email body"""
        # Find all URLs in the email
        url_pattern = r'https?://[^\s<>"\']*'
        
        def replace_url(match):
            original_url = match.group(0)
            # Create tracking redirect URL
            tracking_params = urlencode({
                'tid': tracking_id,
                'url': original_url
            })
            return f'{self.base_url}/track/click?{tracking_params}'
        
        return re.sub(url_pattern, replace_url, email_body)
    
    def _convert_to_html(self, text_email: str) -> str:
        """Convert plain text email to HTML format"""
        # Simple text to HTML conversion
        html_email = text_email.replace('\n\n', '</p><p>')
        html_email = html_email.replace('\n', '<br>')
        html_email = f'<p>{html_email}</p>'
        
        # Add basic HTML structure
        return f"""
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            {html_email}
        </body>
        </html>
        """
    
    def _store_email_for_tracking(self, lead_id: int, template_type: str, 
                                subject_line: str, email_body: str, 
                                recipient_email: str, tracking_id: str, 
                                sent_by: str) -> int:
        """Store email in tracking database"""
        try:
            query = """
                INSERT INTO sent_emails (lead_id, template_type, subject_line, email_body, 
                                       recipient_email, tracking_id, sent_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cur = conn.cursor()
            cur.execute(query, (
                lead_id, template_type, subject_line, email_body, 
                recipient_email, tracking_id, sent_by
            ))
            
            result = cur.fetchone()
            sent_email_id = result[0] if result else None
            
            conn.commit()
            cur.close()
            conn.close()
            
            return sent_email_id
            
        except Exception as e:
            self.logger.error(f"Error storing email for tracking: {e}")
            return None
    
    def _generate_engagement_recommendations(self, engagement_level: str, 
                                           summary_stats: Dict, emails: List) -> List[str]:
        """Generate actionable recommendations based on engagement patterns"""
        recommendations = []
        
        if engagement_level == 'highly_engaged':
            recommendations.extend([
                "Schedule follow-up consultation call",
                "Send detailed case study or ROI analysis",
                "Propose specific implementation timeline"
            ])
        elif engagement_level == 'moderately_engaged':
            recommendations.extend([
                "Send value-focused follow-up email",
                "Try different subject line approaches",
                "Include specific pain point solutions"
            ])
        elif engagement_level == 'low_engagement':
            recommendations.extend([
                "Switch to phone outreach approach",
                "Try shorter, more direct email format",
                "Include compelling statistics or testimonials"
            ])
        else:  # unresponsive
            recommendations.extend([
                "Pause email outreach for 30 days",
                "Try LinkedIn or phone contact",
                "Re-evaluate lead qualification"
            ])
        
        # Add performance-specific recommendations
        if summary_stats['open_rate'] < 20:
            recommendations.append("Test more compelling subject lines")
        
        if summary_stats['click_rate'] < 5:
            recommendations.append("Include more actionable calls-to-action")
        
        return recommendations[:3]  # Return top 3 recommendations
    
    def _get_best_subject_line(self, emails: List) -> str:
        """Find the best performing subject line"""
        if not emails:
            return None
        
        # Sort by engagement (opens + clicks)
        sorted_emails = sorted(emails, 
                             key=lambda x: x['opens'] + x['clicks'], 
                             reverse=True)
        
        return sorted_emails[0]['subject_line'] if sorted_emails else None

# Global email tracker instance
email_tracker = EmailTracker()
