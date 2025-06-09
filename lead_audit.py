"""
Lead Audit Trail and Versioning System for LeadNGN
Tracks historical changes in lead data, scoring, and insights for team collaboration
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from models import db, Lead
import logging

logger = logging.getLogger(__name__)


class LeadAuditLog(db.Model):
    """Model to track all changes made to leads"""
    __tablename__ = 'lead_audit_log'
    
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('lead.id'), nullable=False)
    change_type = Column(String(50), nullable=False)  # created, updated, scored, analyzed, contacted
    field_name = Column(String(100), nullable=True)  # specific field that changed
    old_value = Column(Text, nullable=True)  # previous value
    new_value = Column(Text, nullable=True)  # new value
    changed_by = Column(String(100), nullable=True)  # user or system
    change_reason = Column(String(255), nullable=True)  # reason for change
    metadata = Column(Text, nullable=True)  # additional context as JSON
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    lead = db.relationship('Lead', backref=db.backref('audit_logs', lazy=True))
    
    def __repr__(self):
        return f'<LeadAuditLog {self.lead_id}: {self.change_type}>'


class LeadAuditManager:
    """Manages lead audit trail and versioning"""
    
    def __init__(self):
        pass
    
    def log_lead_creation(self, lead: Lead, created_by: str = 'system') -> bool:
        """Log initial lead creation"""
        try:
            audit_entry = LeadAuditLog(
                lead_id=lead.id,
                change_type='created',
                new_value=self._serialize_lead_data(lead),
                changed_by=created_by,
                change_reason='Initial lead creation',
                metadata=json.dumps({
                    'source': lead.source,
                    'quality_score': lead.quality_score,
                    'industry': lead.industry
                })
            )
            
            db.session.add(audit_entry)
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log lead creation for {lead.id}: {str(e)}")
            return False
    
    def log_field_change(self, lead: Lead, field_name: str, old_value: Any, 
                        new_value: Any, changed_by: str = 'system', 
                        reason: str = None) -> bool:
        """Log change to a specific field"""
        try:
            audit_entry = LeadAuditLog(
                lead_id=lead.id,
                change_type='updated',
                field_name=field_name,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
                changed_by=changed_by,
                change_reason=reason or f'{field_name} updated',
                metadata=json.dumps({
                    'field_type': type(new_value).__name__,
                    'timestamp': datetime.utcnow().isoformat()
                })
            )
            
            db.session.add(audit_entry)
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log field change for {lead.id}: {str(e)}")
            return False
    
    def log_quality_score_change(self, lead: Lead, old_score: int, new_score: int, 
                                reason: str, changed_by: str = 'system') -> bool:
        """Log quality score changes with detailed reasoning"""
        try:
            audit_entry = LeadAuditLog(
                lead_id=lead.id,
                change_type='scored',
                field_name='quality_score',
                old_value=str(old_score),
                new_value=str(new_score),
                changed_by=changed_by,
                change_reason=reason,
                metadata=json.dumps({
                    'score_delta': new_score - old_score,
                    'score_category': self._categorize_score(new_score),
                    'evaluation_factors': reason
                })
            )
            
            db.session.add(audit_entry)
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log score change for {lead.id}: {str(e)}")
            return False
    
    def log_ai_analysis(self, lead: Lead, analysis_type: str, analysis_data: Dict[str, Any], 
                       changed_by: str = 'ai_system') -> bool:
        """Log AI analysis results"""
        try:
            audit_entry = LeadAuditLog(
                lead_id=lead.id,
                change_type='analyzed',
                field_name=analysis_type,
                new_value=json.dumps(analysis_data, default=str),
                changed_by=changed_by,
                change_reason=f'AI {analysis_type} analysis completed',
                metadata=json.dumps({
                    'analysis_confidence': analysis_data.get('confidence', 0),
                    'ai_provider': analysis_data.get('provider', 'unknown'),
                    'analysis_duration': analysis_data.get('duration', 0)
                })
            )
            
            db.session.add(audit_entry)
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log AI analysis for {lead.id}: {str(e)}")
            return False
    
    def log_contact_attempt(self, lead: Lead, contact_type: str, outcome: str, 
                           contact_data: Dict[str, Any], changed_by: str) -> bool:
        """Log contact attempts and outcomes"""
        try:
            audit_entry = LeadAuditLog(
                lead_id=lead.id,
                change_type='contacted',
                field_name=contact_type,
                new_value=json.dumps(contact_data, default=str),
                changed_by=changed_by,
                change_reason=f'{contact_type} contact attempt - {outcome}',
                metadata=json.dumps({
                    'contact_outcome': outcome,
                    'contact_method': contact_type,
                    'response_expected': contact_data.get('response_expected', False)
                })
            )
            
            db.session.add(audit_entry)
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log contact attempt for {lead.id}: {str(e)}")
            return False
    
    def get_lead_history(self, lead_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get complete history for a lead"""
        try:
            audit_logs = LeadAuditLog.query.filter_by(lead_id=lead_id)\
                .order_by(LeadAuditLog.timestamp.desc())\
                .limit(limit)\
                .all()
            
            history = []
            for log in audit_logs:
                history.append({
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat(),
                    'change_type': log.change_type,
                    'field_name': log.field_name,
                    'old_value': log.old_value,
                    'new_value': log.new_value,
                    'changed_by': log.changed_by,
                    'reason': log.change_reason,
                    'metadata': json.loads(log.metadata) if log.metadata else {}
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get lead history for {lead_id}: {str(e)}")
            return []
    
    def get_field_change_history(self, lead_id: int, field_name: str) -> List[Dict[str, Any]]:
        """Get change history for a specific field"""
        try:
            audit_logs = LeadAuditLog.query.filter_by(
                lead_id=lead_id, 
                field_name=field_name
            ).order_by(LeadAuditLog.timestamp.desc()).all()
            
            changes = []
            for log in audit_logs:
                changes.append({
                    'timestamp': log.timestamp.isoformat(),
                    'old_value': log.old_value,
                    'new_value': log.new_value,
                    'changed_by': log.changed_by,
                    'reason': log.change_reason
                })
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to get field history for {lead_id}.{field_name}: {str(e)}")
            return []
    
    def get_quality_score_evolution(self, lead_id: int) -> Dict[str, Any]:
        """Track quality score changes over time"""
        try:
            score_logs = LeadAuditLog.query.filter_by(
                lead_id=lead_id,
                field_name='quality_score'
            ).order_by(LeadAuditLog.timestamp.asc()).all()
            
            evolution = {
                'lead_id': lead_id,
                'score_history': [],
                'total_changes': len(score_logs),
                'score_trend': 'stable'
            }
            
            scores = []
            for log in score_logs:
                score_data = {
                    'timestamp': log.timestamp.isoformat(),
                    'score': int(log.new_value) if log.new_value else 0,
                    'reason': log.change_reason,
                    'changed_by': log.changed_by
                }
                evolution['score_history'].append(score_data)
                scores.append(int(log.new_value) if log.new_value else 0)
            
            # Determine trend
            if len(scores) >= 2:
                if scores[-1] > scores[0]:
                    evolution['score_trend'] = 'improving'
                elif scores[-1] < scores[0]:
                    evolution['score_trend'] = 'declining'
            
            return evolution
            
        except Exception as e:
            logger.error(f"Failed to get score evolution for {lead_id}: {str(e)}")
            return {'error': str(e)}
    
    def get_team_activity_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get team activity summary for collaboration insights"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            recent_logs = LeadAuditLog.query.filter(
                LeadAuditLog.timestamp >= cutoff_date
            ).all()
            
            activity_summary = {
                'period_days': days,
                'total_changes': len(recent_logs),
                'changes_by_user': {},
                'changes_by_type': {},
                'most_active_leads': {},
                'collaboration_score': 0
            }
            
            for log in recent_logs:
                # Count by user
                user = log.changed_by or 'unknown'
                activity_summary['changes_by_user'][user] = \
                    activity_summary['changes_by_user'].get(user, 0) + 1
                
                # Count by type
                change_type = log.change_type
                activity_summary['changes_by_type'][change_type] = \
                    activity_summary['changes_by_type'].get(change_type, 0) + 1
                
                # Track active leads
                lead_id = str(log.lead_id)
                activity_summary['most_active_leads'][lead_id] = \
                    activity_summary['most_active_leads'].get(lead_id, 0) + 1
            
            # Calculate collaboration score
            unique_users = len(activity_summary['changes_by_user'])
            if unique_users > 1:
                activity_summary['collaboration_score'] = min(100, unique_users * 20)
            
            return activity_summary
            
        except Exception as e:
            logger.error(f"Failed to get team activity summary: {str(e)}")
            return {'error': str(e)}
    
    def revert_lead_field(self, lead_id: int, field_name: str, target_timestamp: str, 
                         reverted_by: str) -> bool:
        """Revert a field to a previous value"""
        try:
            # Find the target audit log
            target_log = LeadAuditLog.query.filter_by(
                lead_id=lead_id,
                field_name=field_name
            ).filter(
                LeadAuditLog.timestamp <= datetime.fromisoformat(target_timestamp)
            ).order_by(LeadAuditLog.timestamp.desc()).first()
            
            if not target_log:
                return False
            
            # Get current lead
            lead = Lead.query.get(lead_id)
            if not lead:
                return False
            
            # Get current value
            current_value = getattr(lead, field_name, None)
            
            # Set new value
            setattr(lead, field_name, target_log.new_value)
            
            # Log the reversion
            self.log_field_change(
                lead, field_name, current_value, target_log.new_value,
                reverted_by, f'Reverted to {target_timestamp}'
            )
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to revert field {field_name} for lead {lead_id}: {str(e)}")
            return False
    
    def _serialize_lead_data(self, lead: Lead) -> str:
        """Serialize lead data for audit logging"""
        return json.dumps({
            'company_name': lead.company_name,
            'contact_name': lead.contact_name,
            'email': lead.email,
            'phone': lead.phone,
            'website': lead.website,
            'industry': lead.industry,
            'location': lead.location,
            'quality_score': lead.quality_score,
            'lead_status': lead.lead_status
        }, default=str)
    
    def _categorize_score(self, score: int) -> str:
        """Categorize quality score"""
        if score >= 80:
            return 'high'
        elif score >= 60:
            return 'medium'
        elif score >= 40:
            return 'low'
        else:
            return 'very_low'


# Global audit manager instance
audit_manager = LeadAuditManager()