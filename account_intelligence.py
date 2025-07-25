"""
Account-Based Intelligence System for LeadNgN
Groups leads by corporate domain and tracks intent clusters for enterprise sales
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import func
from models import Lead, LeadInteraction, db
import logging

logger = logging.getLogger(__name__)


class AccountIntelligenceEngine:
    """Manages account-based lead grouping and intent analysis"""
    
    def __init__(self):
        self.domain_pattern = re.compile(r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
        
    def extract_domain_from_email(self, email: str) -> Optional[str]:
        """Extract domain from email address"""
        if not email:
            return None
            
        match = self.domain_pattern.search(email.lower())
        return match.group(1) if match else None
    
    def group_leads_by_account(self, leads: List[Lead]) -> Dict[str, Dict[str, Any]]:
        """Group leads by corporate domain for account-based analysis"""
        try:
            accounts = defaultdict(lambda: {
                'domain': '',
                'leads': [],
                'total_leads': 0,
                'contact_count': 0,
                'quality_scores': [],
                'industries': set(),
                'locations': set(),
                'departments': set(),
                'interaction_count': 0,
                'last_activity': None,
                'account_value': 0
            })
            
            # Process leads and group by domain
            for lead in leads:
                domain = self.extract_domain_from_email(lead.email)
                if not domain or self._is_personal_email_domain(domain):
                    # Create individual account for personal emails
                    domain = f"individual_{lead.id}"
                
                account = accounts[domain]
                account['domain'] = domain
                account['leads'].append({
                    'id': lead.id,
                    'name': lead.contact_name,
                    'email': lead.email,
                    'phone': lead.phone,
                    'quality_score': lead.quality_score,
                    'status': lead.lead_status,
                    'title': self._extract_title_from_name(lead.contact_name),
                    'department': self._infer_department(lead.contact_name, lead.email)
                })
                
                account['total_leads'] += 1
                if lead.contact_name:
                    account['contact_count'] += 1
                if lead.quality_score:
                    account['quality_scores'].append(lead.quality_score)
                if lead.industry:
                    account['industries'].add(lead.industry)
                if lead.location:
                    account['locations'].add(lead.location)
                
                # Infer department from email/name
                dept = self._infer_department(lead.contact_name, lead.email)
                if dept:
                    account['departments'].add(dept)
                
                # Count interactions
                interactions = LeadInteraction.query.filter_by(lead_id=lead.id).count()
                account['interaction_count'] += interactions
                
                # Track last activity
                last_interaction = LeadInteraction.query.filter_by(lead_id=lead.id).order_by(
                    LeadInteraction.interaction_date.desc()
                ).first()
                
                if last_interaction:
                    if not account['last_activity'] or last_interaction.interaction_date > account['last_activity']:
                        account['last_activity'] = last_interaction.interaction_date
            
            # Calculate account metrics
            for domain, account in accounts.items():
                if account['quality_scores']:
                    account['avg_quality'] = sum(account['quality_scores']) / len(account['quality_scores'])
                    account['max_quality'] = max(account['quality_scores'])
                else:
                    account['avg_quality'] = 0
                    account['max_quality'] = 0
                
                # Convert sets to lists for JSON serialization
                account['industries'] = list(account['industries'])
                account['locations'] = list(account['locations'])
                account['departments'] = list(account['departments'])
                
                # Calculate account value score
                account['account_value'] = self._calculate_account_value(account)
            
            return dict(accounts)
            
        except Exception as e:
            logger.error(f"Error grouping leads by account: {str(e)}")
            return {}
    
    def analyze_account_intent(self, domain: str) -> Dict[str, Any]:
        """Analyze buying intent signals for an account"""
        try:
            # Get all leads for this domain
            leads = Lead.query.filter(Lead.email.like(f'%@{domain}')).all()
            
            if not leads:
                return {'error': 'No leads found for this domain'}
            
            intent_signals = {
                'domain': domain,
                'total_touchpoints': len(leads),
                'unique_contacts': len([l for l in leads if l.contact_name]),
                'department_spread': len(set([self._infer_department(l.contact_name, l.email) for l in leads if l.contact_name])),
                'quality_trend': [],
                'engagement_level': 0,
                'buying_signals': [],
                'recommended_actions': []
            }
            
            # Analyze quality trend over time
            leads_by_date = sorted(leads, key=lambda x: x.created_at)
            for lead in leads_by_date:
                intent_signals['quality_trend'].append({
                    'date': lead.created_at.isoformat(),
                    'score': lead.quality_score
                })
            
            # Calculate engagement level
            total_interactions = sum([
                LeadInteraction.query.filter_by(lead_id=lead.id).count() 
                for lead in leads
            ])
            intent_signals['engagement_level'] = min(100, (total_interactions / len(leads)) * 20)
            
            # Identify buying signals
            high_quality_leads = [l for l in leads if l.quality_score >= 80]
            if len(high_quality_leads) >= 2:
                intent_signals['buying_signals'].append('Multiple high-quality contacts identified')
            
            if intent_signals['department_spread'] >= 3:
                intent_signals['buying_signals'].append('Cross-departmental interest detected')
            
            recent_leads = [l for l in leads if l.created_at >= datetime.utcnow() - timedelta(days=30)]
            if len(recent_leads) >= 2:
                intent_signals['buying_signals'].append('Recent repeated engagement')
            
            # Generate recommendations
            if intent_signals['engagement_level'] < 20:
                intent_signals['recommended_actions'].append('Initiate multi-touch campaign')
            
            if high_quality_leads:
                intent_signals['recommended_actions'].append('Focus on decision-maker outreach')
            
            if intent_signals['department_spread'] >= 2:
                intent_signals['recommended_actions'].append('Coordinate account-based approach')
            
            return intent_signals
            
        except Exception as e:
            logger.error(f"Error analyzing account intent for {domain}: {str(e)}")
            return {'error': str(e)}
    
    def get_account_hierarchy(self, domain: str) -> Dict[str, Any]:
        """Identify organizational hierarchy within an account"""
        try:
            leads = Lead.query.filter(Lead.email.like(f'%@{domain}')).all()
            
            hierarchy = {
                'domain': domain,
                'executives': [],
                'managers': [],
                'staff': [],
                'technical': [],
                'unknown': []
            }
            
            for lead in leads:
                category = self._categorize_contact_level(lead.contact_name, lead.email)
                hierarchy[category].append({
                    'id': lead.id,
                    'name': lead.contact_name,
                    'email': lead.email,
                    'phone': lead.phone,
                    'quality_score': lead.quality_score,
                    'department': self._infer_department(lead.contact_name, lead.email)
                })
            
            return hierarchy
            
        except Exception as e:
            logger.error(f"Error getting account hierarchy for {domain}: {str(e)}")
            return {'error': str(e)}
    
    def _is_personal_email_domain(self, domain: str) -> bool:
        """Check if domain is a personal email provider"""
        personal_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
            'aol.com', 'icloud.com', 'protonmail.com', 'live.com'
        }
        return domain.lower() in personal_domains
    
    def _extract_title_from_name(self, name: str) -> Optional[str]:
        """Extract potential title information from contact name"""
        if not name:
            return None
            
        title_indicators = [
            'CEO', 'CTO', 'CFO', 'COO', 'VP', 'Vice President', 'President',
            'Director', 'Manager', 'Lead', 'Senior', 'Principal', 'Head',
            'Supervisor', 'Coordinator', 'Specialist', 'Analyst', 'Engineer'
        ]
        
        name_upper = name.upper()
        for indicator in title_indicators:
            if indicator.upper() in name_upper:
                return indicator
        
        return None
    
    def _infer_department(self, name: str, email: str) -> Optional[str]:
        """Infer department from name and email patterns"""
        if not name and not email:
            return None
        
        text_to_analyze = f"{name or ''} {email or ''}".lower()
        
        department_keywords = {
            'Sales': ['sales', 'business development', 'bd', 'account', 'revenue'],
            'Marketing': ['marketing', 'brand', 'content', 'social', 'campaign'],
            'Engineering': ['engineering', 'tech', 'dev', 'software', 'code'],
            'Operations': ['operations', 'ops', 'logistics', 'supply'],
            'Finance': ['finance', 'accounting', 'budget', 'controller'],
            'HR': ['hr', 'human resources', 'talent', 'people', 'recruiting'],
            'Executive': ['ceo', 'cto', 'cfo', 'president', 'founder'],
            'IT': ['it', 'admin', 'support', 'help', 'desk']
        }
        
        for dept, keywords in department_keywords.items():
            for keyword in keywords:
                if keyword in text_to_analyze:
                    return dept
        
        return 'General'
    
    def _categorize_contact_level(self, name: str, email: str) -> str:
        """Categorize contact by organizational level"""
        text_to_analyze = f"{name or ''} {email or ''}".lower()
        
        if any(title in text_to_analyze for title in ['ceo', 'cto', 'cfo', 'president', 'founder', 'owner']):
            return 'executives'
        elif any(title in text_to_analyze for title in ['vp', 'vice president', 'director', 'head']):
            return 'executives'
        elif any(title in text_to_analyze for title in ['manager', 'supervisor', 'lead', 'principal']):
            return 'managers'
        elif any(title in text_to_analyze for title in ['engineer', 'developer', 'admin', 'analyst']):
            return 'technical'
        elif name and email:
            return 'staff'
        else:
            return 'unknown'
    
    def _calculate_account_value(self, account: Dict[str, Any]) -> int:
        """Calculate overall account value score (0-100)"""
        score = 0
        
        # Base score from average quality
        score += account['avg_quality'] * 0.4
        
        # Bonus for multiple contacts
        if account['contact_count'] > 1:
            score += min(20, account['contact_count'] * 5)
        
        # Bonus for department diversity
        if len(account['departments']) > 1:
            score += min(15, len(account['departments']) * 5)
        
        # Bonus for interactions
        if account['interaction_count'] > 0:
            score += min(10, account['interaction_count'] * 2)
        
        # Bonus for recent activity
        if account['last_activity'] and account['last_activity'] >= datetime.utcnow() - timedelta(days=30):
            score += 15
        
        return min(100, int(score))
    
    def get_top_accounts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top accounts by value score"""
        try:
            all_leads = Lead.query.all()
            accounts = self.group_leads_by_account(all_leads)
            
            # Sort by account value and return top accounts
            sorted_accounts = sorted(
                accounts.values(), 
                key=lambda x: x['account_value'], 
                reverse=True
            )
            
            return sorted_accounts[:limit]
            
        except Exception as e:
            logger.error(f"Error getting top accounts: {str(e)}")
            return []


# Global account intelligence instance
account_intelligence = AccountIntelligenceEngine()