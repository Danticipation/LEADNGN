"""
Email Deliverability and Validation System for LeadNgN
Ensures high deliverability rates for outreach campaigns
"""

import os
import re
import dns.resolver
import requests
import logging
from typing import Dict, List, Any, Optional
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

class EmailDeliverabilityChecker:
    """Comprehensive email deliverability analysis and validation"""
    
    def __init__(self):
        self.mx_cache = {}
        self.domain_cache = {}
    
    def validate_email_comprehensive(self, email: str) -> Dict[str, Any]:
        """Comprehensive email validation with deliverability scoring"""
        result = {
            "email": email,
            "is_valid": False,
            "deliverability_score": 0,
            "issues": [],
            "recommendations": [],
            "mx_records": [],
            "domain_info": {}
        }
        
        try:
            # Basic email validation
            validation = validate_email(email)
            normalized_email = validation.email
            domain = validation.domain
            
            result["normalized_email"] = normalized_email
            result["domain"] = domain
            result["is_valid"] = True
            
            # Domain and MX record analysis
            mx_info = self.check_mx_records(domain)
            result["mx_records"] = mx_info["records"]
            result["mx_valid"] = mx_info["valid"]
            
            # Domain reputation check
            domain_rep = self.check_domain_reputation(domain)
            result["domain_info"] = domain_rep
            
            # Calculate deliverability score
            score = self.calculate_deliverability_score(email, domain, mx_info, domain_rep)
            result["deliverability_score"] = score
            
            # Generate recommendations
            result["recommendations"] = self.generate_recommendations(email, domain, score)
            
        except EmailNotValidError as e:
            result["issues"].append(f"Invalid email format: {str(e)}")
        except Exception as e:
            logger.error(f"Email validation error: {str(e)}")
            result["issues"].append(f"Validation error: {str(e)}")
        
        return result
    
    def check_mx_records(self, domain: str) -> Dict[str, Any]:
        """Check MX records for domain"""
        if domain in self.mx_cache:
            return self.mx_cache[domain]
        
        mx_info = {
            "valid": False,
            "records": [],
            "primary_mx": None
        }
        
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            for mx in mx_records:
                mx_info["records"].append({
                    "priority": mx.preference,
                    "exchange": str(mx.exchange).rstrip('.')
                })
            
            if mx_info["records"]:
                mx_info["valid"] = True
                mx_info["primary_mx"] = min(mx_info["records"], key=lambda x: x["priority"])
            
        except dns.resolver.NXDOMAIN:
            mx_info["error"] = "Domain does not exist"
        except dns.resolver.NoAnswer:
            mx_info["error"] = "No MX records found"
        except Exception as e:
            mx_info["error"] = f"DNS lookup failed: {str(e)}"
        
        self.mx_cache[domain] = mx_info
        return mx_info
    
    def check_domain_reputation(self, domain: str) -> Dict[str, Any]:
        """Check domain reputation and characteristics"""
        if domain in self.domain_cache:
            return self.domain_cache[domain]
        
        domain_info = {
            "is_business_domain": False,
            "is_freemail": False,
            "has_website": False,
            "domain_age_indicator": "unknown",
            "reputation_score": 50  # Default neutral score
        }
        
        try:
            # Check if it's a business domain vs freemail
            freemail_providers = {
                'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
                'aol.com', 'icloud.com', 'mail.com', 'protonmail.com'
            }
            
            domain_info["is_freemail"] = domain.lower() in freemail_providers
            domain_info["is_business_domain"] = not domain_info["is_freemail"]
            
            # Check if domain has active website
            try:
                response = requests.head(f"https://{domain}", timeout=5)
                domain_info["has_website"] = response.status_code < 400
                domain_info["website_status"] = response.status_code
            except:
                try:
                    response = requests.head(f"http://{domain}", timeout=5)
                    domain_info["has_website"] = response.status_code < 400
                    domain_info["website_status"] = response.status_code
                except:
                    domain_info["has_website"] = False
            
            # Calculate reputation score
            if domain_info["is_business_domain"]:
                domain_info["reputation_score"] += 30
            if domain_info["has_website"]:
                domain_info["reputation_score"] += 20
            
        except Exception as e:
            logger.error(f"Domain reputation check failed: {str(e)}")
        
        self.domain_cache[domain] = domain_info
        return domain_info
    
    def calculate_deliverability_score(self, email: str, domain: str, mx_info: Dict, domain_info: Dict) -> int:
        """Calculate overall deliverability score (0-100)"""
        score = 0
        
        # Base score for valid email format
        score += 20
        
        # MX record validation
        if mx_info.get("valid"):
            score += 25
        
        # Domain characteristics
        if domain_info.get("is_business_domain"):
            score += 20
        elif domain_info.get("is_freemail"):
            score += 10  # Freemail is still deliverable, just lower priority
        
        # Website presence
        if domain_info.get("has_website"):
            score += 15
        
        # Email structure analysis
        local_part = email.split('@')[0]
        if self.is_professional_email_format(local_part):
            score += 10
        
        # Role-based email detection (lower score)
        if self.is_role_based_email(local_part):
            score -= 15
        
        # Disposable email detection
        if self.is_disposable_email(domain):
            score -= 50
        
        return max(0, min(100, score))
    
    def is_professional_email_format(self, local_part: str) -> bool:
        """Check if email follows professional naming conventions"""
        # Professional patterns: firstname.lastname, firstnamelastname, first.last
        professional_patterns = [
            r'^[a-zA-Z]+\.[a-zA-Z]+$',  # john.doe
            r'^[a-zA-Z]+[a-zA-Z]+$',    # johndoe (reasonable length)
            r'^[a-zA-Z]\.[a-zA-Z]+$',   # j.doe
        ]
        
        for pattern in professional_patterns:
            if re.match(pattern, local_part) and len(local_part) > 3:
                return True
        return False
    
    def is_role_based_email(self, local_part: str) -> bool:
        """Check if email is role-based (info@, admin@, etc.)"""
        role_keywords = {
            'info', 'admin', 'support', 'contact', 'sales', 'marketing',
            'noreply', 'no-reply', 'help', 'service', 'team', 'office'
        }
        return local_part.lower() in role_keywords
    
    def is_disposable_email(self, domain: str) -> bool:
        """Check if domain is a disposable email provider"""
        disposable_domains = {
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'temp-mail.org', 'throwaway.email'
        }
        return domain.lower() in disposable_domains
    
    def generate_recommendations(self, email: str, domain: str, score: int) -> List[str]:
        """Generate actionable recommendations for email outreach"""
        recommendations = []
        
        if score >= 80:
            recommendations.append("Excellent deliverability - prioritize for outreach")
        elif score >= 60:
            recommendations.append("Good deliverability - suitable for campaigns")
        elif score >= 40:
            recommendations.append("Moderate deliverability - consider email warming")
        else:
            recommendations.append("Poor deliverability - verify contact or find alternative")
        
        domain_info = self.domain_cache.get(domain, {})
        
        if domain_info.get("is_freemail"):
            recommendations.append("Freemail address - consider LinkedIn outreach as backup")
        
        if not domain_info.get("has_website"):
            recommendations.append("Domain has no website - verify business is active")
        
        local_part = email.split('@')[0]
        if self.is_role_based_email(local_part):
            recommendations.append("Role-based email - may have multiple recipients")
        
        if score < 50:
            recommendations.append("Consider phone outreach as primary method")
        
        return recommendations
    
    def validate_outreach_setup(self, sender_domain: str) -> Dict[str, Any]:
        """Validate sender domain configuration for outreach"""
        setup_check = {
            "domain": sender_domain,
            "spf_valid": False,
            "dkim_suggested": True,
            "dmarc_recommended": True,
            "mx_configured": False,
            "setup_score": 0,
            "recommendations": []
        }
        
        try:
            # Check SPF record
            try:
                txt_records = dns.resolver.resolve(sender_domain, 'TXT')
                for record in txt_records:
                    if 'v=spf1' in str(record):
                        setup_check["spf_valid"] = True
                        setup_check["spf_record"] = str(record)
                        break
            except:
                pass
            
            # Check MX records for sending domain
            mx_info = self.check_mx_records(sender_domain)
            setup_check["mx_configured"] = mx_info["valid"]
            
            # Calculate setup score
            if setup_check["spf_valid"]:
                setup_check["setup_score"] += 40
            if setup_check["mx_configured"]:
                setup_check["setup_score"] += 30
            
            # Generate recommendations
            if not setup_check["spf_valid"]:
                setup_check["recommendations"].append("Add SPF record to prevent spoofing")
            if not setup_check["mx_configured"]:
                setup_check["recommendations"].append("Configure MX records for domain")
            
            setup_check["recommendations"].append("Configure DKIM signing for authentication")
            setup_check["recommendations"].append("Set up DMARC policy for domain protection")
            
        except Exception as e:
            logger.error(f"Setup validation error: {str(e)}")
            setup_check["error"] = str(e)
        
        return setup_check
    
    def bulk_validate_leads(self, leads: List[Any]) -> Dict[str, Any]:
        """Validate email deliverability for multiple leads"""
        results = {
            "total_leads": len(leads),
            "validated_count": 0,
            "high_deliverability": 0,
            "medium_deliverability": 0,
            "low_deliverability": 0,
            "invalid_emails": 0,
            "leads": []
        }
        
        for lead in leads:
            if not lead.email:
                continue
            
            validation = self.validate_email_comprehensive(lead.email)
            lead_result = {
                "lead_id": lead.id,
                "company_name": lead.company_name,
                "email": lead.email,
                "deliverability_score": validation["deliverability_score"],
                "is_valid": validation["is_valid"],
                "recommendations": validation["recommendations"]
            }
            
            results["leads"].append(lead_result)
            results["validated_count"] += 1
            
            if validation["is_valid"]:
                if validation["deliverability_score"] >= 70:
                    results["high_deliverability"] += 1
                elif validation["deliverability_score"] >= 40:
                    results["medium_deliverability"] += 1
                else:
                    results["low_deliverability"] += 1
            else:
                results["invalid_emails"] += 1
        
        return results


class EmailWarmupIntegration:
    """Integration with email warmup services"""
    
    def __init__(self):
        self.warmup_providers = {
            'mailreach': {
                'api_url': 'https://api.mailreach.co/v1',
                'supported': True
            },
            'warmupinbox': {
                'api_url': 'https://api.warmupinbox.com/v1',
                'supported': True
            }
        }
    
    def check_email_warmup_status(self, email: str, provider: str = 'mailreach') -> Dict[str, Any]:
        """Check if email is properly warmed up"""
        # This would integrate with actual warmup service APIs
        # For now, return structured placeholder data
        return {
            "email": email,
            "is_warmed": False,
            "warmup_days": 0,
            "reputation_score": 50,
            "daily_limit": 50,
            "recommendation": "Start warmup process before campaign launch"
        }
    
    def suggest_warmup_schedule(self, email_count: int, campaign_start_date: str) -> Dict[str, Any]:
        """Suggest email warmup schedule for campaign"""
        return {
            "total_emails": email_count,
            "recommended_warmup_days": min(30, max(7, email_count // 10)),
            "daily_increase": "10-20% per day",
            "starting_volume": 5,
            "target_volume": min(100, email_count // 2),
            "campaign_readiness": campaign_start_date
        }