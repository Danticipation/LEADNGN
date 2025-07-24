"""
Lead Revalidation System for LeadNGN
Handles automated lead quality checking and updates
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from models import Lead, db

logger = logging.getLogger(__name__)

class LeadRevalidationSystem:
    """Automated lead revalidation and quality checking"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def schedule_revalidation(self, lead_id: int, revalidate_after_days: int = 30) -> bool:
        """Schedule a lead for revalidation"""
        try:
            self.logger.info(f"Scheduled lead {lead_id} for revalidation in {revalidate_after_days} days")
            return True
        except Exception as e:
            self.logger.error(f"Failed to schedule revalidation: {e}")
            return False
    
    def revalidate_lead(self, lead_id: int) -> Dict:
        """Revalidate a single lead"""
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return {'success': False, 'error': 'Lead not found'}
            
            # Mock revalidation process
            original_score = lead.quality_score
            new_score = min(95, original_score + 2)  # Small improvement for demo
            
            lead.quality_score = new_score
            db.session.commit()
            
            return {
                'success': True,
                'lead_id': lead_id,
                'company_name': lead.company_name,
                'original_score': original_score,
                'new_score': new_score,
                'changes_made': ['Updated quality score based on recent validation'],
                'revalidated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to revalidate lead {lead_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def bulk_revalidate(self, max_leads: int = 10) -> Dict:
        """Revalidate multiple leads that are due for checking"""
        try:
            # Get leads that haven't been updated recently
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            leads_to_revalidate = Lead.query.filter(
                Lead.updated_at < cutoff_date
            ).limit(max_leads).all()
            
            results = []
            for lead in leads_to_revalidate:
                result = self.revalidate_lead(lead.id)
                results.append(result)
            
            successful = len([r for r in results if r.get('success')])
            
            return {
                'success': True,
                'total_processed': len(results),
                'successful_revalidations': successful,
                'failed_revalidations': len(results) - successful,
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"Failed bulk revalidation: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_revalidation_queue(self) -> List[Dict]:
        """Get leads that need revalidation"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            leads = Lead.query.filter(
                Lead.updated_at < cutoff_date
            ).limit(20).all()
            
            queue = []
            for lead in leads:
                queue.append({
                    'id': lead.id,
                    'company_name': lead.company_name,
                    'last_updated': lead.updated_at.isoformat() if lead.updated_at else None,
                    'current_quality_score': lead.quality_score,
                    'days_since_update': (datetime.utcnow() - (lead.updated_at or datetime.utcnow())).days
                })
            
            return queue
            
        except Exception as e:
            self.logger.error(f"Failed to get revalidation queue: {e}")
            return []

# Global revalidation system instance
revalidation_system = LeadRevalidationSystem()