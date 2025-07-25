"""
Data Enrichment Module for LeadNgN
Advanced lead data validation and enhancement capabilities
"""

import requests
import time
import logging
import re
import json
import dns.resolver
from typing import Dict, List, Optional
from urllib.parse import urlparse
from datetime import datetime

logger = logging.getLogger(__name__)

class DataEnrichment:
    """Advanced data enrichment and validation for leads"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def validate_email_deliverability(self, email: str) -> Dict:
        """Validate email deliverability and quality"""
        validation_result = {
            'email': email,
            'is_valid': False,
            'deliverability_score': 0,
            'mx_record_exists': False,
            'domain_reputation': 'unknown',
            'validation_details': {}
        }
        
        try:
            # Basic format validation
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                validation_result['validation_details']['format'] = 'invalid'
                return validation_result
            
            validation_result['validation_details']['format'] = 'valid'
            
            # Extract domain
            domain = email.split('@')[1]
            validation_result['domain'] = domain
            
            # Check MX records
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                validation_result['mx_record_exists'] = len(mx_records) > 0
                validation_result['mx_records'] = [str(mx) for mx in mx_records]
                validation_result['validation_details']['mx_check'] = 'passed'
            except:
                validation_result['validation_details']['mx_check'] = 'failed'
            
            # Domain reputation check (basic)
            domain_score = self._assess_domain_reputation(domain)
            validation_result['domain_reputation'] = domain_score
            
            # Calculate deliverability score
            score = 0
            if validation_result['validation_details']['format'] == 'valid':
                score += 30
            if validation_result['mx_record_exists']:
                score += 40
            if domain_score == 'good':
                score += 30
            elif domain_score == 'neutral':
                score += 20
            
            validation_result['deliverability_score'] = score
            validation_result['is_valid'] = score >= 70
            
        except Exception as e:
            logger.error(f"Email validation error for {email}: {e}")
            validation_result['validation_details']['error'] = str(e)
        
        return validation_result
    
    def _assess_domain_reputation(self, domain: str) -> str:
        """Assess domain reputation"""
        try:
            # Known good domains
            trusted_domains = [
                'gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com',
                'aol.com', 'icloud.com', 'protonmail.com'
            ]
            
            # Suspicious patterns
            suspicious_patterns = [
                'temp', 'fake', 'spam', 'test', 'throwaway', '10min'
            ]
            
            if domain.lower() in trusted_domains:
                return 'good'
            
            if any(pattern in domain.lower() for pattern in suspicious_patterns):
                return 'poor'
            
            # Check if it's a business domain (has company website)
            if self._check_business_domain(domain):
                return 'good'
            
            return 'neutral'
            
        except Exception:
            return 'unknown'
    
    def _check_business_domain(self, domain: str) -> bool:
        """Check if domain appears to be a legitimate business domain"""
        try:
            # Try to access the domain
            response = self.session.get(f'https://www.{domain}', timeout=5)
            if response.status_code == 200:
                content = response.text.lower()
                business_indicators = [
                    'contact', 'about', 'services', 'business', 'company',
                    'professional', 'address', 'phone'
                ]
                return any(indicator in content for indicator in business_indicators)
        except:
            pass
        
        return False
    
    def validate_phone_number(self, phone: str) -> Dict:
        """Validate and format phone number"""
        validation_result = {
            'phone': phone,
            'is_valid': False,
            'formatted': '',
            'type': 'unknown',
            'region': 'unknown'
        }
        
        try:
            # Remove all non-digits
            digits = re.sub(r'\D', '', phone)
            
            # US phone number validation
            if len(digits) == 10:
                # Format as (XXX) XXX-XXXX
                formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                validation_result.update({
                    'is_valid': True,
                    'formatted': formatted,
                    'type': 'landline_or_mobile',
                    'region': 'US'
                })
            elif len(digits) == 11 and digits[0] == '1':
                # US number with country code
                formatted = f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
                validation_result.update({
                    'is_valid': True,
                    'formatted': formatted,
                    'type': 'landline_or_mobile',
                    'region': 'US'
                })
            
        except Exception as e:
            logger.error(f"Phone validation error for {phone}: {e}")
            validation_result['error'] = str(e)
        
        return validation_result
    
    def analyze_website_quality(self, website_url: str) -> Dict:
        """Analyze website quality and business indicators"""
        analysis = {
            'url': website_url,
            'accessible': False,
            'ssl_enabled': False,
            'mobile_friendly': False,
            'professional_design': False,
            'contact_info_present': False,
            'business_indicators': [],
            'technology_stack': [],
            'seo_indicators': {},
            'quality_score': 0
        }
        
        try:
            # Ensure URL has protocol
            if not website_url.startswith(('http://', 'https://')):
                website_url = f'https://{website_url}'
            
            analysis['ssl_enabled'] = website_url.startswith('https://')
            
            # Attempt to access website
            response = self.session.get(website_url, timeout=10)
            
            if response.status_code == 200:
                analysis['accessible'] = True
                content = response.text.lower()
                
                # Check for business indicators
                business_keywords = [
                    'contact us', 'about us', 'services', 'testimonials',
                    'phone', 'email', 'address', 'experience', 'professional'
                ]
                
                for keyword in business_keywords:
                    if keyword in content:
                        analysis['business_indicators'].append(keyword)
                
                analysis['contact_info_present'] = any(
                    indicator in analysis['business_indicators'] 
                    for indicator in ['contact us', 'phone', 'email', 'address']
                )
                
                # Check for mobile viewport
                analysis['mobile_friendly'] = 'viewport' in content and 'width=device-width' in content
                
                # Professional design indicators
                professional_indicators = ['bootstrap', 'jquery', 'css', 'responsive']
                analysis['professional_design'] = any(indicator in content for indicator in professional_indicators)
                
                # SEO indicators
                analysis['seo_indicators'] = {
                    'has_title': '<title>' in content,
                    'has_description': 'description' in content,
                    'has_keywords': 'keywords' in content
                }
            
            # Calculate quality score
            score = 0
            if analysis['accessible']:
                score += 25
            if analysis['ssl_enabled']:
                score += 20
            if analysis['mobile_friendly']:
                score += 15
            if analysis['contact_info_present']:
                score += 20
            if analysis['professional_design']:
                score += 10
            if len(analysis['business_indicators']) >= 3:
                score += 10
            
            analysis['quality_score'] = score
            
        except Exception as e:
            logger.error(f"Website analysis error for {website_url}: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
    def enrich_business_data(self, company_name: str, website: str = None, location: str = None) -> Dict:
        """Enrich business data with additional information"""
        enrichment = {
            'company_name': company_name,
            'business_type': 'unknown',
            'estimated_size': 'unknown',
            'industry_classification': 'unknown',
            'social_presence': {},
            'online_reviews': {},
            'business_age_estimate': 'unknown',
            'enrichment_confidence': 0
        }
        
        try:
            # Analyze business type from name
            enrichment['business_type'] = self._classify_business_type(company_name)
            
            # Estimate business size from name and location
            enrichment['estimated_size'] = self._estimate_business_size(company_name, location)
            
            # Industry classification
            enrichment['industry_classification'] = self._classify_industry(company_name)
            
            # Social media presence check
            if website:
                enrichment['social_presence'] = self._check_social_presence(website)
            
            # Calculate enrichment confidence
            confidence = 0
            if enrichment['business_type'] != 'unknown':
                confidence += 25
            if enrichment['estimated_size'] != 'unknown':
                confidence += 25
            if enrichment['industry_classification'] != 'unknown':
                confidence += 25
            if enrichment['social_presence']:
                confidence += 25
            
            enrichment['enrichment_confidence'] = confidence
            
        except Exception as e:
            logger.error(f"Business enrichment error for {company_name}: {e}")
            enrichment['error'] = str(e)
        
        return enrichment
    
    def _classify_business_type(self, company_name: str) -> str:
        """Classify business type from company name"""
        name_lower = company_name.lower()
        
        if any(word in name_lower for word in ['llc', 'inc', 'corp', 'corporation']):
            return 'corporation'
        elif any(word in name_lower for word in ['group', 'associates', 'partners']):
            return 'partnership'
        elif any(word in name_lower for word in ['services', 'solutions', 'consulting']):
            return 'service_business'
        else:
            return 'small_business'
    
    def _estimate_business_size(self, company_name: str, location: str = None) -> str:
        """Estimate business size from indicators"""
        name_lower = company_name.lower()
        
        large_indicators = ['national', 'international', 'corporation', 'enterprises', 'global']
        medium_indicators = ['regional', 'group', 'associates', 'solutions', 'systems']
        
        if any(indicator in name_lower for indicator in large_indicators):
            return 'large'
        elif any(indicator in name_lower for indicator in medium_indicators):
            return 'medium'
        else:
            return 'small'
    
    def _classify_industry(self, company_name: str) -> str:
        """Classify industry from company name"""
        name_lower = company_name.lower()
        
        industry_keywords = {
            'hvac': ['hvac', 'heating', 'cooling', 'air conditioning', 'climate'],
            'dental': ['dental', 'dentist', 'orthodontic', 'oral'],
            'legal': ['law', 'legal', 'attorney', 'lawyer'],
            'plumbing': ['plumbing', 'plumber', 'drain', 'water'],
            'construction': ['construction', 'builder', 'contractor', 'remodeling'],
            'automotive': ['auto', 'automotive', 'car', 'vehicle'],
            'healthcare': ['medical', 'health', 'clinic', 'care'],
            'technology': ['tech', 'software', 'digital', 'it'],
            'consulting': ['consulting', 'advisory', 'solutions']
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in name_lower for keyword in keywords):
                return industry
        
        return 'general'
    
    def _check_social_presence(self, website: str) -> Dict:
        """Check for social media presence"""
        social_presence = {
            'facebook': False,
            'linkedin': False,
            'twitter': False,
            'instagram': False,
            'youtube': False
        }
        
        try:
            response = self.session.get(website, timeout=5)
            if response.status_code == 200:
                content = response.text.lower()
                
                social_patterns = {
                    'facebook': ['facebook.com', 'fb.com'],
                    'linkedin': ['linkedin.com'],
                    'twitter': ['twitter.com', 'x.com'],
                    'instagram': ['instagram.com'],
                    'youtube': ['youtube.com']
                }
                
                for platform, patterns in social_patterns.items():
                    if any(pattern in content for pattern in patterns):
                        social_presence[platform] = True
        
        except Exception:
            pass
        
        return social_presence
    
    def validate_business_legitimacy(self, lead_data: Dict) -> Dict:
        """Comprehensive business legitimacy validation"""
        validation = {
            'legitimacy_score': 0,
            'trust_indicators': [],
            'red_flags': [],
            'verification_status': 'pending',
            'validation_details': {}
        }
        
        try:
            score = 0
            
            # Email validation
            if lead_data.get('email'):
                email_validation = self.validate_email_deliverability(lead_data['email'])
                if email_validation['is_valid']:
                    score += 25
                    validation['trust_indicators'].append('Valid email address')
                validation['validation_details']['email'] = email_validation
            
            # Phone validation
            if lead_data.get('phone'):
                phone_validation = self.validate_phone_number(lead_data['phone'])
                if phone_validation['is_valid']:
                    score += 20
                    validation['trust_indicators'].append('Valid phone number')
                validation['validation_details']['phone'] = phone_validation
            
            # Website analysis
            if lead_data.get('website'):
                website_analysis = self.analyze_website_quality(lead_data['website'])
                if website_analysis['accessible']:
                    score += 25
                    validation['trust_indicators'].append('Accessible website')
                if website_analysis['ssl_enabled']:
                    score += 10
                    validation['trust_indicators'].append('SSL enabled')
                validation['validation_details']['website'] = website_analysis
            
            # Business data enrichment
            if lead_data.get('company_name'):
                enrichment = self.enrich_business_data(
                    lead_data['company_name'], 
                    lead_data.get('website'),
                    lead_data.get('location')
                )
                if enrichment['enrichment_confidence'] >= 50:
                    score += 20
                    validation['trust_indicators'].append('Business data verified')
                validation['validation_details']['enrichment'] = enrichment
            
            # Set validation status
            validation['legitimacy_score'] = score
            if score >= 80:
                validation['verification_status'] = 'verified'
            elif score >= 60:
                validation['verification_status'] = 'likely_legitimate'
            elif score >= 40:
                validation['verification_status'] = 'needs_review'
            else:
                validation['verification_status'] = 'questionable'
                validation['red_flags'].append('Low validation score')
            
        except Exception as e:
            logger.error(f"Business legitimacy validation error: {e}")
            validation['error'] = str(e)
        
        return validation

# Global instance
data_enricher = DataEnrichment()