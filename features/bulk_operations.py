"""
Bulk Operations & User Experience Enhancements for LeadNGN
Bulk actions, saved filters, and lead health scoring
"""

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from models import Lead, db
from sqlalchemy import and_, or_

logger = logging.getLogger(__name__)

class BulkOperationsManager:
    """Manage bulk operations and enhanced user experience features"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def bulk_delete_leads(self, lead_ids: List[int], user_id: str = None) -> Dict:
        """Bulk delete multiple leads with audit trail"""
        try:
            if not lead_ids:
                return {'error': 'No lead IDs provided'}
            
            # Get leads to delete
            leads_to_delete = Lead.query.filter(Lead.id.in_(lead_ids)).all()
            
            if not leads_to_delete:
                return {'error': 'No valid leads found'}
            
            deleted_count = len(leads_to_delete)
            deleted_companies = [lead.company_name for lead in leads_to_delete]
            
            # Log bulk deletion for audit trail
            self.logger.info(f"Bulk deletion initiated by {user_id}: {deleted_count} leads")
            
            # Delete leads
            for lead in leads_to_delete:
                db.session.delete(lead)
            
            db.session.commit()
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'deleted_companies': deleted_companies,
                'operation': 'bulk_delete',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Bulk delete error: {e}")
            db.session.rollback()
            return {'error': f'Bulk delete failed: {str(e)}'}
    
    def bulk_tag_leads(self, lead_ids: List[int], tags_to_add: List[str], tags_to_remove: List[str] = None) -> Dict:
        """Bulk add/remove tags from multiple leads"""
        try:
            if not lead_ids:
                return {'error': 'No lead IDs provided'}
            
            leads = Lead.query.filter(Lead.id.in_(lead_ids)).all()
            
            if not leads:
                return {'error': 'No valid leads found'}
            
            updated_count = 0
            
            for lead in leads:
                current_tags = lead.get_tags()
                
                # Add new tags
                if tags_to_add:
                    for tag in tags_to_add:
                        if tag not in current_tags:
                            current_tags.append(tag)
                
                # Remove specified tags
                if tags_to_remove:
                    current_tags = [tag for tag in current_tags if tag not in tags_to_remove]
                
                lead.set_tags(current_tags)
                updated_count += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'updated_count': updated_count,
                'tags_added': tags_to_add or [],
                'tags_removed': tags_to_remove or [],
                'operation': 'bulk_tag',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Bulk tag error: {e}")
            db.session.rollback()
            return {'error': f'Bulk tag operation failed: {str(e)}'}
    
    def bulk_update_status(self, lead_ids: List[int], new_status: str) -> Dict:
        """Bulk update lead status"""
        try:
            valid_statuses = ['new', 'contacted', 'qualified', 'converted', 'rejected']
            
            if new_status not in valid_statuses:
                return {'error': f'Invalid status. Must be one of: {valid_statuses}'}
            
            if not lead_ids:
                return {'error': 'No lead IDs provided'}
            
            leads = Lead.query.filter(Lead.id.in_(lead_ids)).all()
            
            if not leads:
                return {'error': 'No valid leads found'}
            
            for lead in leads:
                lead.lead_status = new_status
                lead.updated_at = datetime.utcnow()
                
                if new_status == 'contacted':
                    lead.last_contacted = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'updated_count': len(leads),
                'new_status': new_status,
                'operation': 'bulk_status_update',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Bulk status update error: {e}")
            db.session.rollback()
            return {'error': f'Bulk status update failed: {str(e)}'}
    
    def bulk_export_leads(self, lead_ids: List[int], export_format: str = 'csv') -> Dict:
        """Export multiple leads in specified format"""
        try:
            if not lead_ids:
                return {'error': 'No lead IDs provided'}
            
            leads = Lead.query.filter(Lead.id.in_(lead_ids)).all()
            
            if not leads:
                return {'error': 'No valid leads found'}
            
            export_data = []
            
            for lead in leads:
                lead_data = {
                    'id': lead.id,
                    'company_name': lead.company_name,
                    'contact_name': lead.contact_name,
                    'email': lead.email,
                    'phone': lead.phone,
                    'website': lead.website,
                    'industry': lead.industry,
                    'location': lead.location,
                    'quality_score': lead.quality_score,
                    'lead_status': lead.lead_status,
                    'created_at': lead.created_at.isoformat() if lead.created_at else None,
                    'tags': ', '.join(lead.get_tags()),
                    'notes': lead.notes
                }
                export_data.append(lead_data)
            
            return {
                'success': True,
                'export_count': len(export_data),
                'export_format': export_format,
                'data': export_data,
                'operation': 'bulk_export',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Bulk export error: {e}")
            return {'error': f'Bulk export failed: {str(e)}'}

class SavedFiltersManager:
    """Manage saved search filters for users"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # In production, this would be stored in database
        self.saved_filters = {}
    
    def save_filter(self, filter_name: str, filter_criteria: Dict, user_id: str = None) -> Dict:
        """Save a search filter for reuse"""
        try:
            filter_id = f"{user_id}_{filter_name}" if user_id else filter_name
            
            saved_filter = {
                'filter_name': filter_name,
                'filter_criteria': filter_criteria,
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat(),
                'usage_count': 0
            }
            
            self.saved_filters[filter_id] = saved_filter
            
            return {
                'success': True,
                'filter_id': filter_id,
                'filter_name': filter_name,
                'saved_at': saved_filter['created_at']
            }
            
        except Exception as e:
            self.logger.error(f"Save filter error: {e}")
            return {'error': f'Failed to save filter: {str(e)}'}
    
    def get_saved_filters(self, user_id: str = None) -> Dict:
        """Get all saved filters for a user"""
        try:
            user_filters = []
            
            for filter_id, filter_data in self.saved_filters.items():
                if not user_id or filter_data.get('user_id') == user_id:
                    user_filters.append({
                        'filter_id': filter_id,
                        'filter_name': filter_data['filter_name'],
                        'filter_criteria': filter_data['filter_criteria'],
                        'created_at': filter_data['created_at'],
                        'usage_count': filter_data['usage_count']
                    })
            
            return {
                'success': True,
                'filters': user_filters,
                'total_count': len(user_filters)
            }
            
        except Exception as e:
            self.logger.error(f"Get saved filters error: {e}")
            return {'error': f'Failed to get saved filters: {str(e)}'}
    
    def apply_saved_filter(self, filter_id: str) -> Dict:
        """Apply a saved filter and return matching leads"""
        try:
            if filter_id not in self.saved_filters:
                return {'error': 'Saved filter not found'}
            
            filter_data = self.saved_filters[filter_id]
            filter_criteria = filter_data['filter_criteria']
            
            # Increment usage count
            self.saved_filters[filter_id]['usage_count'] += 1
            
            # Apply filter criteria to find leads
            query = Lead.query
            
            if 'industry' in filter_criteria and filter_criteria['industry']:
                query = query.filter(Lead.industry == filter_criteria['industry'])
            
            if 'location' in filter_criteria and filter_criteria['location']:
                query = query.filter(Lead.location.like(f"%{filter_criteria['location']}%"))
            
            if 'quality_score_min' in filter_criteria:
                query = query.filter(Lead.quality_score >= filter_criteria['quality_score_min'])
            
            if 'status' in filter_criteria and filter_criteria['status']:
                query = query.filter(Lead.lead_status == filter_criteria['status'])
            
            if 'tags' in filter_criteria and filter_criteria['tags']:
                # Tag filtering would require more complex logic
                pass
            
            leads = query.all()
            
            return {
                'success': True,
                'filter_applied': filter_data['filter_name'],
                'matching_leads': len(leads),
                'leads': [{'id': lead.id, 'company_name': lead.company_name, 'industry': lead.industry} for lead in leads]
            }
            
        except Exception as e:
            self.logger.error(f"Apply saved filter error: {e}")
            return {'error': f'Failed to apply saved filter: {str(e)}'}

class LeadHealthScorer:
    """Calculate comprehensive lead health scores"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_lead_health_score(self, lead_id: int) -> Dict:
        """Calculate comprehensive lead health score"""
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return {'error': 'Lead not found'}
            
            # Base quality score (0-100)
            quality_score = lead.quality_score or 50
            
            # Age factor (newer is better)
            age_score = self._calculate_age_score(lead)
            
            # Engagement score (based on interactions)
            engagement_score = self._calculate_engagement_score(lead)
            
            # Data completeness score
            completeness_score = self._calculate_completeness_score(lead)
            
            # Validation score (if available)
            validation_score = getattr(lead, 'validation_score', 70)
            
            # Weighted health score calculation (handle None values)
            health_score = (
                (quality_score or 50) * 0.3 +
                (age_score or 50) * 0.2 +
                (engagement_score or 50) * 0.2 +
                (completeness_score or 50) * 0.15 +
                (validation_score or 50) * 0.15
            )
            
            # Determine health status
            if health_score >= 80:
                health_status = 'excellent'
                priority = 'high'
            elif health_score >= 65:
                health_status = 'good'
                priority = 'medium'
            elif health_score >= 50:
                health_status = 'fair'
                priority = 'medium'
            else:
                health_status = 'poor'
                priority = 'low'
            
            return {
                'lead_id': lead_id,
                'company_name': lead.company_name,
                'health_score': round(health_score, 1),
                'health_status': health_status,
                'priority': priority,
                'score_breakdown': {
                    'quality_score': quality_score,
                    'age_score': age_score,
                    'engagement_score': engagement_score,
                    'completeness_score': completeness_score,
                    'validation_score': validation_score
                },
                'recommendations': self._get_health_recommendations(health_score, lead),
                'calculated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Lead health scoring error for {lead_id}: {e}")
            return {'error': f'Health scoring failed: {str(e)}'}
    
    def _calculate_age_score(self, lead: Lead) -> float:
        """Calculate score based on lead age"""
        if not lead.created_at:
            return 50.0
        
        days_old = (datetime.utcnow() - lead.created_at).days
        
        if days_old <= 7:
            return 100.0
        elif days_old <= 30:
            return 85.0
        elif days_old <= 90:
            return 70.0
        elif days_old <= 180:
            return 55.0
        else:
            return 30.0
    
    def _calculate_engagement_score(self, lead: Lead) -> float:
        """Calculate score based on engagement history"""
        # Check if lead has been contacted
        if lead.last_contacted:
            days_since_contact = (datetime.utcnow() - lead.last_contacted).days
            if days_since_contact <= 7:
                return 90.0
            elif days_since_contact <= 30:
                return 75.0
            else:
                return 60.0
        
        # Check lead status
        status_scores = {
            'new': 50.0,
            'contacted': 70.0,
            'qualified': 85.0,
            'converted': 100.0,
            'rejected': 20.0
        }
        
        return status_scores.get(lead.lead_status, 50.0)
    
    def _calculate_completeness_score(self, lead: Lead) -> float:
        """Calculate score based on data completeness"""
        fields_to_check = [
            lead.company_name,
            lead.contact_name,
            lead.email,
            lead.phone,
            lead.website,
            lead.industry,
            lead.location
        ]
        
        filled_fields = sum(1 for field in fields_to_check if field and field.strip())
        completeness_percentage = (filled_fields / len(fields_to_check)) * 100
        
        return completeness_percentage
    
    def _get_health_recommendations(self, health_score: float, lead: Lead) -> List[str]:
        """Get actionable recommendations to improve lead health"""
        recommendations = []
        
        if health_score < 50:
            recommendations.append("Consider data validation and cleanup")
        
        if not lead.email:
            recommendations.append("Add email address for better outreach")
        
        if not lead.phone:
            recommendations.append("Add phone number for multi-channel contact")
        
        if not lead.last_contacted:
            recommendations.append("Schedule initial outreach contact")
        
        if lead.lead_status == 'new':
            recommendations.append("Update lead status after contact attempts")
        
        if not lead.notes:
            recommendations.append("Add notes with lead context and insights")
        
        return recommendations[:3]  # Return top 3 recommendations

# Global instances
bulk_operations_manager = BulkOperationsManager()
saved_filters_manager = SavedFiltersManager()
lead_health_scorer = LeadHealthScorer()