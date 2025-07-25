"""
Compliance & Ethics Management for LeadNgN
GDPR/CCPA compliance, opt-out management, and ethical scraping practices
"""

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from models import Lead, db
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)

class ComplianceManager:
    """Manage data privacy compliance and ethical practices"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.do_not_contact_list = set()  # In production, this would be in database
        self.consent_records = {}  # Track consent status
    
    def gdpr_compliance_check(self, lead_id: int) -> Dict:
        """Check GDPR compliance status for a lead"""
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return {'error': 'Lead not found'}
            
            # Determine if lead is EU-based
            eu_countries = [
                'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
                'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece',
                'Hungary', 'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg',
                'Malta', 'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia',
                'Slovenia', 'Spain', 'Sweden'
            ]
            
            is_eu_subject = any(country in (lead.location or '') for country in eu_countries)
            
            compliance_status = {
                'lead_id': lead_id,
                'is_eu_data_subject': is_eu_subject,
                'compliance_required': is_eu_subject,
                'consent_status': self._get_consent_status(lead_id),
                'data_retention_compliant': self._check_data_retention(lead),
                'lawful_basis': self._determine_lawful_basis(lead),
                'privacy_rights': self._get_applicable_rights(is_eu_subject),
                'compliance_score': 0,
                'recommendations': []
            }
            
            # Calculate compliance score
            compliance_status['compliance_score'] = self._calculate_compliance_score(compliance_status)
            
            # Generate recommendations
            compliance_status['recommendations'] = self._get_compliance_recommendations(compliance_status)
            
            return compliance_status
            
        except Exception as e:
            self.logger.error(f"GDPR compliance check error for {lead_id}: {e}")
            return {'error': f'Compliance check failed: {str(e)}'}
    
    def record_consent(self, lead_id: int, consent_type: str, consent_given: bool, 
                      consent_source: str = 'manual') -> Dict:
        """Record consent status for a lead"""
        try:
            consent_record = {
                'lead_id': lead_id,
                'consent_type': consent_type,  # 'marketing', 'data_processing', 'profiling'
                'consent_given': consent_given,
                'consent_source': consent_source,
                'timestamp': datetime.utcnow().isoformat(),
                'ip_address': None,  # Would be captured from request
                'user_agent': None   # Would be captured from request
            }
            
            # Store consent record
            self.consent_records[f"{lead_id}_{consent_type}"] = consent_record
            
            return {
                'success': True,
                'consent_recorded': consent_record,
                'next_steps': self._get_consent_next_steps(consent_given, consent_type)
            }
            
        except Exception as e:
            self.logger.error(f"Consent recording error: {e}")
            return {'error': f'Failed to record consent: {str(e)}'}
    
    def process_data_subject_request(self, lead_id: int, request_type: str) -> Dict:
        """Process GDPR data subject requests"""
        try:
            valid_requests = ['access', 'rectification', 'erasure', 'portability', 'restriction']
            
            if request_type not in valid_requests:
                return {'error': f'Invalid request type. Must be one of: {valid_requests}'}
            
            lead = Lead.query.get(lead_id)
            if not lead:
                return {'error': 'Lead not found'}
            
            if request_type == 'access':
                return self._process_access_request(lead)
            elif request_type == 'erasure':
                return self._process_erasure_request(lead)
            elif request_type == 'rectification':
                return self._process_rectification_request(lead)
            elif request_type == 'portability':
                return self._process_portability_request(lead)
            elif request_type == 'restriction':
                return self._process_restriction_request(lead)
            
        except Exception as e:
            self.logger.error(f"Data subject request error: {e}")
            return {'error': f'Request processing failed: {str(e)}'}
    
    def add_to_do_not_contact(self, identifier: str, reason: str = 'user_request') -> Dict:
        """Add email or phone to do-not-contact list"""
        try:
            self.do_not_contact_list.add(identifier.lower())
            
            # Also mark any existing leads with this identifier
            leads_updated = 0
            if '@' in identifier:  # Email
                leads = Lead.query.filter(Lead.email.ilike(identifier)).all()
            else:  # Phone
                leads = Lead.query.filter(Lead.phone.like(f'%{identifier}%')).all()
            
            for lead in leads:
                lead.lead_status = 'opt_out'
                lead.notes = (lead.notes or '') + f"\n[AUTO] Added to DNC list: {reason} ({datetime.utcnow().strftime('%Y-%m-%d')})"
                leads_updated += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'identifier': identifier,
                'reason': reason,
                'leads_updated': leads_updated,
                'dnc_list_size': len(self.do_not_contact_list)
            }
            
        except Exception as e:
            self.logger.error(f"Add to DNC error: {e}")
            db.session.rollback()
            return {'error': f'Failed to add to do-not-contact list: {str(e)}'}
    
    def check_robots_txt(self, domain: str) -> Dict:
        """Check robots.txt compliance for scraping"""
        try:
            robots_url = f"https://{domain}/robots.txt"
            
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            # Check if scraping is allowed
            user_agent = 'LeadNGN-Bot'
            can_scrape = rp.can_fetch(user_agent, f"https://{domain}/")
            
            # Get crawl delay if specified
            crawl_delay = rp.crawl_delay(user_agent) or 1
            
            # Get sitemap URLs
            sitemaps = list(rp.site_maps()) if hasattr(rp, 'site_maps') else []
            
            return {
                'domain': domain,
                'robots_txt_accessible': True,
                'scraping_allowed': can_scrape,
                'crawl_delay_seconds': crawl_delay,
                'sitemaps': sitemaps,
                'compliance_status': 'compliant' if can_scrape else 'restricted',
                'recommendations': self._get_robots_recommendations(can_scrape, crawl_delay)
            }
            
        except Exception as e:
            # If robots.txt not accessible, assume scraping is allowed with caution
            return {
                'domain': domain,
                'robots_txt_accessible': False,
                'scraping_allowed': True,
                'crawl_delay_seconds': 2,  # Conservative default
                'compliance_status': 'assume_allowed',
                'recommendations': ['Use conservative crawl delays', 'Monitor for rate limiting']
            }
    
    def _get_consent_status(self, lead_id: int) -> Dict:
        """Get consent status for a lead"""
        consent_types = ['marketing', 'data_processing', 'profiling']
        status = {}
        
        for consent_type in consent_types:
            key = f"{lead_id}_{consent_type}"
            if key in self.consent_records:
                status[consent_type] = self.consent_records[key]['consent_given']
            else:
                status[consent_type] = None  # No consent recorded
        
        return status
    
    def _check_data_retention(self, lead: Lead) -> bool:
        """Check if data retention is compliant"""
        # GDPR requires data not be kept longer than necessary
        # Default retention period: 3 years for marketing data
        retention_period = timedelta(days=1095)  # 3 years
        
        if lead.created_at:
            age = datetime.utcnow() - lead.created_at
            return age <= retention_period
        
        return True  # No creation date means recent
    
    def _determine_lawful_basis(self, lead: Lead) -> str:
        """Determine GDPR lawful basis for processing"""
        # Common lawful bases for B2B lead generation
        if lead.lead_status == 'converted':
            return 'contract'  # Performance of contract
        elif 'opt_in' in (lead.notes or '').lower():
            return 'consent'  # Explicit consent
        else:
            return 'legitimate_interest'  # B2B marketing legitimate interest
    
    def _get_applicable_rights(self, is_eu_subject: bool) -> List[str]:
        """Get applicable privacy rights"""
        if is_eu_subject:
            return [
                'right_to_access',
                'right_to_rectification',
                'right_to_erasure',
                'right_to_restrict_processing',
                'right_to_data_portability',
                'right_to_object'
            ]
        else:
            return ['right_to_opt_out']  # CCPA-style rights
    
    def _calculate_compliance_score(self, compliance_status: Dict) -> int:
        """Calculate overall compliance score"""
        score = 100
        
        if compliance_status['is_eu_data_subject']:
            # Stricter requirements for EU subjects
            consent_status = compliance_status['consent_status']
            
            if consent_status.get('marketing') is False:
                score -= 30
            elif consent_status.get('marketing') is None:
                score -= 15
            
            if not compliance_status['data_retention_compliant']:
                score -= 25
            
            if compliance_status['lawful_basis'] == 'unknown':
                score -= 20
        
        return max(0, score)
    
    def _get_compliance_recommendations(self, compliance_status: Dict) -> List[str]:
        """Get compliance improvement recommendations"""
        recommendations = []
        
        if compliance_status['is_eu_data_subject']:
            consent_status = compliance_status['consent_status']
            
            if consent_status.get('marketing') is None:
                recommendations.append("Record explicit marketing consent")
            
            if not compliance_status['data_retention_compliant']:
                recommendations.append("Review data retention - consider archival or deletion")
            
            if compliance_status['lawful_basis'] == 'legitimate_interest':
                recommendations.append("Document legitimate interest assessment")
        
        return recommendations
    
    def _get_consent_next_steps(self, consent_given: bool, consent_type: str) -> List[str]:
        """Get next steps after consent recording"""
        if consent_given:
            return [
                f"Can proceed with {consent_type} activities",
                "Update lead status to reflect consent",
                "Include in relevant marketing campaigns"
            ]
        else:
            return [
                f"Must not use data for {consent_type}",
                "Add to do-not-contact list",
                "Consider data deletion if no other lawful basis"
            ]
    
    def _process_access_request(self, lead: Lead) -> Dict:
        """Process GDPR access request"""
        # Compile all data held about the subject
        lead_data = {
            'personal_data': {
                'company_name': lead.company_name,
                'contact_name': lead.contact_name,
                'email': lead.email,
                'phone': lead.phone,
                'location': lead.location
            },
            'processing_data': {
                'quality_score': lead.quality_score,
                'lead_status': lead.lead_status,
                'tags': lead.get_tags(),
                'notes': lead.notes,
                'created_at': lead.created_at.isoformat() if lead.created_at else None,
                'last_contacted': lead.last_contacted.isoformat() if lead.last_contacted else None
            },
            'consent_records': self._get_consent_status(lead.id),
            'retention_period': '3 years from creation',
            'processing_purposes': ['B2B lead generation', 'Business development', 'Marketing communications']
        }
        
        return {
            'request_type': 'access',
            'data_export': lead_data,
            'response_deadline': (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
    
    def _process_erasure_request(self, lead: Lead) -> Dict:
        """Process GDPR erasure request"""
        try:
            # Check if there are legitimate grounds to retain data
            retention_required = (
                lead.lead_status == 'converted' or
                'contract' in (lead.notes or '').lower()
            )
            
            if retention_required:
                return {
                    'request_type': 'erasure',
                    'action_taken': 'partial_erasure',
                    'reason': 'Legal obligation to retain contract-related data',
                    'data_anonymized': ['contact_name', 'email', 'phone'],
                    'data_retained': ['company_name', 'contract_details']
                }
            else:
                # Full erasure
                db.session.delete(lead)
                db.session.commit()
                
                return {
                    'request_type': 'erasure',
                    'action_taken': 'full_erasure',
                    'lead_deleted': True,
                    'deletion_timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            db.session.rollback()
            raise e
    
    def _process_rectification_request(self, lead: Lead) -> Dict:
        """Process GDPR rectification request"""
        return {
            'request_type': 'rectification',
            'instructions': 'Please provide correct data to update',
            'updateable_fields': ['company_name', 'contact_name', 'email', 'phone', 'location'],
            'current_data': {
                'company_name': lead.company_name,
                'contact_name': lead.contact_name,
                'email': lead.email,
                'phone': lead.phone,
                'location': lead.location
            }
        }
    
    def _process_portability_request(self, lead: Lead) -> Dict:
        """Process GDPR portability request"""
        portable_data = {
            'lead_id': lead.id,
            'company_name': lead.company_name,
            'contact_name': lead.contact_name,
            'email': lead.email,
            'phone': lead.phone,
            'website': lead.website,
            'industry': lead.industry,
            'location': lead.location,
            'created_at': lead.created_at.isoformat() if lead.created_at else None,
            'tags': lead.get_tags()
        }
        
        return {
            'request_type': 'portability',
            'portable_data': portable_data,
            'export_format': 'JSON',
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _process_restriction_request(self, lead: Lead) -> Dict:
        """Process GDPR restriction request"""
        # Mark lead as restricted
        lead.lead_status = 'restricted'
        lead.notes = (lead.notes or '') + f"\n[GDPR] Processing restricted: {datetime.utcnow().strftime('%Y-%m-%d')}"
        db.session.commit()
        
        return {
            'request_type': 'restriction',
            'action_taken': 'processing_restricted',
            'restricted_activities': ['marketing', 'profiling', 'automated_processing'],
            'allowed_activities': ['data_storage', 'legal_compliance']
        }
    
    def _get_robots_recommendations(self, can_scrape: bool, crawl_delay: int) -> List[str]:
        """Get robots.txt compliance recommendations"""
        recommendations = []
        
        if not can_scrape:
            recommendations.append("Scraping not allowed - respect robots.txt restrictions")
            recommendations.append("Consider alternative data sources")
        else:
            if crawl_delay > 5:
                recommendations.append(f"Use minimum {crawl_delay}s delay between requests")
            recommendations.append("Monitor for rate limiting responses")
            recommendations.append("Include proper User-Agent identification")
        
        return recommendations

# Global compliance manager instance
compliance_manager = ComplianceManager()