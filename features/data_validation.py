"""
Data Quality & Validation System for LeadNGN
Real-time email verification, phone validation, and data freshness tracking
"""

import logging
import re
import requests
import dns.resolver
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from models import Lead, db

logger = logging.getLogger(__name__)

class DataValidator:
    """Comprehensive data validation and quality management"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.phone_pattern = re.compile(r'^\+?1?[2-9]\d{2}[2-9]\d{2}\d{4}$')
    
    def validate_lead_data(self, lead_id: int, deep_validation: bool = False) -> Dict:
        """Comprehensive lead data validation"""
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return {'error': 'Lead not found'}
            
            validation_results = {
                'lead_id': lead_id,
                'company_name': lead.company_name,
                'validation_timestamp': datetime.utcnow().isoformat(),
                'overall_score': 0,
                'validations': {}
            }
            
            # Email validation
            email_validation = self._validate_email(lead.email, deep_validation)
            validation_results['validations']['email'] = email_validation
            
            # Phone validation
            phone_validation = self._validate_phone(lead.phone)
            validation_results['validations']['phone'] = phone_validation
            
            # Website validation
            website_validation = self._validate_website(lead.website)
            validation_results['validations']['website'] = website_validation
            
            # Data freshness check
            freshness_check = self._check_data_freshness(lead)
            validation_results['validations']['data_freshness'] = freshness_check
            
            # Company name validation
            company_validation = self._validate_company_name(lead.company_name)
            validation_results['validations']['company_name'] = company_validation
            
            # Calculate overall validation score
            validation_results['overall_score'] = self._calculate_validation_score(validation_results['validations'])
            
            # Update lead with validation data
            self._update_lead_validation_data(lead, validation_results)
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Lead validation error for {lead_id}: {e}")
            return {'error': f'Validation failed: {str(e)}'}
    
    def bulk_validate_leads(self, lead_ids: List[int]) -> Dict:
        """Bulk validation for multiple leads"""
        try:
            results = {
                'total_leads': len(lead_ids),
                'validated_leads': 0,
                'failed_validations': 0,
                'validation_summary': {
                    'high_quality': 0,
                    'medium_quality': 0,
                    'low_quality': 0
                },
                'individual_results': []
            }
            
            for lead_id in lead_ids:
                validation_result = self.validate_lead_data(lead_id, deep_validation=False)
                
                if 'error' not in validation_result:
                    results['validated_leads'] += 1
                    score = validation_result['overall_score']
                    
                    if score >= 80:
                        results['validation_summary']['high_quality'] += 1
                    elif score >= 60:
                        results['validation_summary']['medium_quality'] += 1
                    else:
                        results['validation_summary']['low_quality'] += 1
                else:
                    results['failed_validations'] += 1
                
                results['individual_results'].append(validation_result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Bulk validation error: {e}")
            return {'error': f'Bulk validation failed: {str(e)}'}
    
    def _validate_email(self, email: str, deep_validation: bool = False) -> Dict:
        """Validate email address with optional deep verification"""
        if not email:
            return {
                'valid': False,
                'score': 0,
                'reason': 'Email address missing',
                'deliverable': False
            }
        
        # Basic format validation
        if not self.email_pattern.match(email):
            return {
                'valid': False,
                'score': 0,
                'reason': 'Invalid email format',
                'deliverable': False
            }
        
        domain = email.split('@')[1]
        
        # MX record validation
        mx_valid = self._check_mx_record(domain)
        
        validation_result = {
            'valid': True,
            'score': 70,  # Base score for valid format
            'domain': domain,
            'mx_record_valid': mx_valid,
            'deliverable': mx_valid
        }
        
        if mx_valid:
            validation_result['score'] += 20  # Boost for valid MX
        
        # Deep validation using external service (would require API key)
        if deep_validation:
            # Placeholder for ZeroBounce/Hunter.io integration
            # In production, this would make API calls
            validation_result.update({
                'disposable': False,
                'catch_all': False,
                'role_account': 'unknown',
                'free_email': domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com'],
                'confidence_score': 85
            })
            
            if not validation_result['free_email']:
                validation_result['score'] += 10  # Business email bonus
        
        return validation_result
    
    def _validate_phone(self, phone: str) -> Dict:
        """Validate phone number format and dialability"""
        if not phone:
            return {
                'valid': False,
                'score': 0,
                'reason': 'Phone number missing',
                'dialable': False
            }
        
        # Clean phone number
        cleaned_phone = re.sub(r'[^\d+]', '', phone)
        
        # Basic format validation
        if not self.phone_pattern.match(cleaned_phone):
            return {
                'valid': False,
                'score': 30,
                'reason': 'Invalid phone format',
                'dialable': False,
                'cleaned_number': cleaned_phone
            }
        
        # Extract area code for US numbers
        area_code = None
        if len(cleaned_phone) >= 10:
            area_code = cleaned_phone[-10:-7]
        
        return {
            'valid': True,
            'score': 85,
            'dialable': True,
            'area_code': area_code,
            'cleaned_number': cleaned_phone,
            'format': 'US_PHONE'
        }
    
    def _validate_website(self, website: str) -> Dict:
        """Validate website URL and accessibility"""
        if not website:
            return {
                'valid': False,
                'score': 0,
                'reason': 'Website URL missing',
                'accessible': False
            }
        
        # Ensure URL has protocol
        if not website.startswith(('http://', 'https://')):
            website = 'https://' + website
        
        try:
            # Quick accessibility check
            response = requests.head(website, timeout=5, allow_redirects=True)
            accessible = response.status_code < 400
            
            return {
                'valid': True,
                'score': 90 if accessible else 60,
                'accessible': accessible,
                'status_code': response.status_code,
                'final_url': response.url,
                'has_ssl': website.startswith('https://')
            }
            
        except Exception as e:
            return {
                'valid': True,
                'score': 40,
                'accessible': False,
                'reason': f'Connection error: {str(e)[:50]}',
                'has_ssl': website.startswith('https://')
            }
    
    def _validate_company_name(self, company_name: str) -> Dict:
        """Validate company name quality"""
        if not company_name:
            return {
                'valid': False,
                'score': 0,
                'reason': 'Company name missing'
            }
        
        # Basic quality checks
        score = 50  # Base score
        issues = []
        
        if len(company_name) < 3:
            issues.append('Very short name')
            score -= 30
        elif len(company_name) > 100:
            issues.append('Unusually long name')
            score -= 10
        
        # Check for common business suffixes
        business_suffixes = ['LLC', 'Inc', 'Corp', 'Company', 'Co', 'Ltd', 'LTD']
        has_suffix = any(suffix in company_name.upper() for suffix in business_suffixes)
        if has_suffix:
            score += 20
        
        # Check for suspicious patterns
        if any(char in company_name for char in ['@', 'http', 'www']):
            issues.append('Contains suspicious characters')
            score -= 40
        
        return {
            'valid': score > 0,
            'score': max(0, score),
            'has_business_suffix': has_suffix,
            'issues': issues,
            'length': len(company_name)
        }
    
    def _check_data_freshness(self, lead: Lead) -> Dict:
        """Check how fresh/stale the lead data is"""
        now = datetime.utcnow()
        created_date = lead.created_at
        
        days_old = (now - created_date).days
        
        # Calculate freshness score
        if days_old <= 7:
            freshness_score = 100
            status = 'fresh'
        elif days_old <= 30:
            freshness_score = 80
            status = 'recent'
        elif days_old <= 90:
            freshness_score = 60
            status = 'aging'
        else:
            freshness_score = 30
            status = 'stale'
        
        return {
            'score': freshness_score,
            'status': status,
            'days_old': days_old,
            'created_date': created_date.isoformat(),
            'last_validated': getattr(lead, 'last_validated', None),
            'needs_revalidation': days_old > 30
        }
    
    def _check_mx_record(self, domain: str) -> bool:
        """Check if domain has valid MX record"""
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            return len(mx_records) > 0
        except:
            return False
    
    def _calculate_validation_score(self, validations: Dict) -> int:
        """Calculate overall validation score from individual validations"""
        weights = {
            'email': 0.3,
            'phone': 0.2,
            'website': 0.2,
            'company_name': 0.1,
            'data_freshness': 0.2
        }
        
        total_score = 0
        for validation_type, weight in weights.items():
            if validation_type in validations:
                score = validations[validation_type].get('score', 0)
                total_score += score * weight
        
        return int(total_score)
    
    def _update_lead_validation_data(self, lead: Lead, validation_results: Dict):
        """Update lead with validation metadata"""
        try:
            # Store validation timestamp and overall score
            lead.last_validated = datetime.utcnow()
            
            # Update quality score if validation score is higher
            validation_score = validation_results['overall_score']
            if validation_score > (lead.quality_score or 0):
                lead.quality_score = validation_score
            
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to update lead validation data: {e}")
            db.session.rollback()

# Global data validator instance
data_validator = DataValidator()