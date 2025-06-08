"""
RAG (Retrieval-Augmented Generation) System for LeadNGN
Provides intelligent lead insights, company research, and personalized outreach
"""
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup
from models import Lead, db
import openai

logger = logging.getLogger(__name__)

class LeadRAGSystem:
    """RAG system for intelligent lead analysis and content generation"""
    
    def __init__(self):
        self.openai_client = None
        self.setup_openai()
        self.knowledge_base = {}
        
    def setup_openai(self):
        """Initialize OpenAI client if API key is available"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
        else:
            logger.warning("OpenAI API key not found. RAG functionality will be limited.")
    
    def gather_lead_context(self, lead: Lead) -> Dict[str, Any]:
        """Gather comprehensive context about a lead from multiple sources"""
        context = {
            'basic_info': self.extract_basic_lead_info(lead),
            'company_research': self.research_company(lead),
            'industry_insights': self.get_industry_insights(lead.industry),
            'web_presence': self.analyze_web_presence(lead.website) if lead.website else {},
            'contact_analysis': self.analyze_contact_patterns(lead)
        }
        
        # Store in knowledge base for future retrieval
        self.knowledge_base[lead.id] = context
        
        return context
    
    def extract_basic_lead_info(self, lead: Lead) -> Dict[str, Any]:
        """Extract and structure basic lead information"""
        return {
            'company_name': lead.company_name,
            'industry': lead.industry,
            'location': lead.location,
            'contact_name': lead.contact_name,
            'email': lead.email,
            'phone': lead.phone,
            'website': lead.website,
            'quality_score': lead.quality_score,
            'lead_status': lead.lead_status,
            'company_size': lead.company_size,
            'revenue_estimate': lead.revenue_estimate,
            'employee_count': lead.employee_count,
            'description': lead.description,
            'tags': lead.get_tags(),
            'created_at': lead.created_at.isoformat() if lead.created_at else None
        }
    
    def research_company(self, lead: Lead) -> Dict[str, Any]:
        """Research company information from web sources"""
        research_data = {
            'services_offered': [],
            'competitive_advantages': [],
            'recent_news': [],
            'social_presence': {},
            'business_model': None,
            'target_market': None
        }
        
        try:
            if lead.website:
                # Scrape company website for detailed information
                website_data = self.scrape_company_website(lead.website)
                research_data.update(website_data)
            
            # Search for company news and mentions
            news_data = self.search_company_news(lead.company_name, lead.location)
            research_data['recent_news'] = news_data
            
        except Exception as e:
            logger.warning(f"Error researching company {lead.company_name}: {e}")
        
        return research_data
    
    def scrape_company_website(self, website_url: str) -> Dict[str, Any]:
        """Scrape company website for business intelligence"""
        data = {
            'services_offered': [],
            'about_info': '',
            'key_personnel': [],
            'business_focus': '',
            'certifications': [],
            'service_areas': []
        }
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(website_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract services information
            services_keywords = ['services', 'what we do', 'offerings', 'solutions', 'specialties']
            for keyword in services_keywords:
                services_sections = soup.find_all(text=re.compile(keyword, re.I))
                for section in services_sections:
                    parent = section.parent
                    if parent:
                        services_text = parent.get_text()[:500]
                        if len(services_text) > 50:
                            data['services_offered'].append(services_text.strip())
                            break
            
            # Extract about information
            about_sections = soup.find_all(['div', 'section'], class_=re.compile(r'about|company', re.I))
            for section in about_sections:
                about_text = section.get_text()[:1000]
                if len(about_text) > 100:
                    data['about_info'] = about_text.strip()
                    break
            
            # Look for certifications and credentials
            cert_keywords = ['certified', 'licensed', 'accredited', 'member', 'association']
            page_text = soup.get_text().lower()
            for keyword in cert_keywords:
                if keyword in page_text:
                    # Extract text around certification mentions
                    cert_matches = re.finditer(keyword, page_text)
                    for match in cert_matches:
                        start = max(0, match.start() - 50)
                        end = min(len(page_text), match.end() + 50)
                        cert_context = page_text[start:end].strip()
                        if cert_context not in data['certifications']:
                            data['certifications'].append(cert_context)
            
            # Extract contact and service area information
            location_patterns = [
                r'\b(?:serving|service area|coverage|located in|based in)\s+([A-Za-z\s,]+)',
                r'\b([A-Z][a-z]+,\s*[A-Z]{2})\b'
            ]
            
            for pattern in location_patterns:
                matches = re.findall(pattern, soup.get_text())
                data['service_areas'].extend(matches[:5])  # Limit to 5 areas
            
        except Exception as e:
            logger.warning(f"Error scraping website {website_url}: {e}")
        
        return data
    
    def search_company_news(self, company_name: str, location: str = None) -> List[Dict[str, str]]:
        """Search for recent news and mentions about the company"""
        news_items = []
        
        try:
            # Use web scraping to find news mentions
            search_terms = [company_name]
            if location:
                search_terms.append(location)
            
            # This would typically use a news API, but we'll implement basic web search
            query = " ".join(search_terms) + " news"
            
            # Simulate news search results (in production, you'd use actual news APIs)
            # For now, we'll return empty list but the structure is ready
            
        except Exception as e:
            logger.warning(f"Error searching news for {company_name}: {e}")
        
        return news_items
    
    def get_industry_insights(self, industry: str) -> Dict[str, Any]:
        """Get industry-specific insights and trends"""
        industry_data = {
            'market_trends': [],
            'common_pain_points': [],
            'seasonal_factors': [],
            'regulatory_considerations': [],
            'technology_adoption': [],
            'competitive_landscape': []
        }
        
        # Define industry-specific insights
        industry_insights = {
            'hvac': {
                'common_pain_points': [
                    'Emergency repair calls',
                    'Seasonal demand fluctuations',
                    'Energy efficiency compliance',
                    'Skilled technician shortage'
                ],
                'seasonal_factors': [
                    'High demand in summer/winter',
                    'Maintenance season in spring/fall',
                    'Emergency calls during extreme weather'
                ],
                'technology_adoption': [
                    'Smart thermostats',
                    'IoT monitoring systems',
                    'Energy management software',
                    'Mobile scheduling apps'
                ]
            },
            'plumbing': {
                'common_pain_points': [
                    'Emergency leak calls',
                    'Water damage liability',
                    'Code compliance updates',
                    'Parts availability'
                ],
                'seasonal_factors': [
                    'Frozen pipes in winter',
                    'Increased activity in spring',
                    'Water heater replacements before winter'
                ],
                'technology_adoption': [
                    'Leak detection systems',
                    'Video pipe inspection',
                    'Mobile invoicing',
                    'GPS tracking for trucks'
                ]
            },
            'dental': {
                'common_pain_points': [
                    'Insurance claim processing',
                    'Patient no-shows',
                    'Equipment maintenance costs',
                    'Staff retention'
                ],
                'seasonal_factors': [
                    'End-of-year insurance usage',
                    'Back-to-school checkups',
                    'Holiday scheduling challenges'
                ],
                'technology_adoption': [
                    'Digital X-rays',
                    'Practice management software',
                    'Online appointment booking',
                    'Teledentistry platforms'
                ]
            },
            'legal': {
                'common_pain_points': [
                    'Client acquisition costs',
                    'Billing and time tracking',
                    'Document management',
                    'Regulatory compliance'
                ],
                'seasonal_factors': [
                    'Tax season activity',
                    'End-of-year estate planning',
                    'Summer slowdown for some practices'
                ],
                'technology_adoption': [
                    'Case management software',
                    'Document automation',
                    'Video conferencing',
                    'E-signature platforms'
                ]
            }
        }
        
        industry_key = industry.lower().replace(' ', '_') if industry else 'general'
        if industry_key in industry_insights:
            industry_data.update(industry_insights[industry_key])
        
        return industry_data
    
    def analyze_web_presence(self, website_url: str) -> Dict[str, Any]:
        """Analyze company's web presence and digital maturity"""
        analysis = {
            'domain_age': None,
            'ssl_enabled': False,
            'mobile_friendly': False,
            'social_links': [],
            'contact_accessibility': 0,  # Score 0-10
            'content_quality': 0,  # Score 0-10
            'seo_indicators': []
        }
        
        try:
            # Check SSL
            analysis['ssl_enabled'] = website_url.startswith('https://')
            
            # Basic website analysis
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(website_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for mobile viewport meta tag
            viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
            analysis['mobile_friendly'] = viewport_meta is not None
            
            # Find social media links
            social_domains = ['facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com', 'youtube.com']
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                for domain in social_domains:
                    if domain in href:
                        analysis['social_links'].append(href)
            
            # Analyze contact accessibility
            contact_indicators = ['contact', 'phone', 'email', 'address', 'call']
            contact_score = 0
            page_text = soup.get_text().lower()
            
            for indicator in contact_indicators:
                if indicator in page_text:
                    contact_score += 2
            
            analysis['contact_accessibility'] = min(contact_score, 10)
            
            # Basic content quality assessment
            text_length = len(soup.get_text())
            has_headings = len(soup.find_all(['h1', 'h2', 'h3'])) > 0
            has_images = len(soup.find_all('img')) > 0
            
            content_score = 0
            if text_length > 500:
                content_score += 3
            if has_headings:
                content_score += 3
            if has_images:
                content_score += 2
            if len(soup.find_all('p')) > 3:
                content_score += 2
            
            analysis['content_quality'] = min(content_score, 10)
            
        except Exception as e:
            logger.warning(f"Error analyzing web presence for {website_url}: {e}")
        
        return analysis
    
    def analyze_contact_patterns(self, lead: Lead) -> Dict[str, Any]:
        """Analyze contact information patterns for insights"""
        analysis = {
            'email_domain_type': 'unknown',
            'phone_format': 'unknown',
            'contact_completeness': 0,
            'professional_indicators': []
        }
        
        try:
            # Analyze email domain
            if lead.email:
                domain = lead.email.split('@')[1].lower()
                if domain == lead.website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0] if lead.website else False:
                    analysis['email_domain_type'] = 'business_domain'
                elif domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                    analysis['email_domain_type'] = 'personal_email'
                else:
                    analysis['email_domain_type'] = 'business_email'
            
            # Analyze phone format
            if lead.phone:
                if re.match(r'\(\d{3}\) \d{3}-\d{4}', lead.phone):
                    analysis['phone_format'] = 'formatted_us'
                elif re.match(r'\d{3}-\d{3}-\d{4}', lead.phone):
                    analysis['phone_format'] = 'dash_format'
                else:
                    analysis['phone_format'] = 'other'
            
            # Calculate contact completeness
            completeness = 0
            if lead.email:
                completeness += 25
            if lead.phone:
                completeness += 25
            if lead.website:
                completeness += 20
            if lead.location:
                completeness += 15
            if lead.contact_name:
                completeness += 15
            
            analysis['contact_completeness'] = completeness
            
            # Professional indicators
            if lead.website and lead.website.startswith('https://'):
                analysis['professional_indicators'].append('SSL_certificate')
            
            if lead.email and analysis['email_domain_type'] == 'business_domain':
                analysis['professional_indicators'].append('business_email_domain')
            
            if lead.phone and analysis['phone_format'] in ['formatted_us', 'dash_format']:
                analysis['professional_indicators'].append('formatted_phone')
            
        except Exception as e:
            logger.warning(f"Error analyzing contact patterns for lead {lead.id}: {e}")
        
        return analysis
    
    def generate_lead_insights(self, lead: Lead) -> Dict[str, Any]:
        """Generate AI-powered insights about a lead using RAG"""
        if not self.openai_client:
            return {'error': 'OpenAI API not configured'}
        
        try:
            # Gather all available context
            context = self.gather_lead_context(lead)
            
            # Create a comprehensive prompt for the AI
            prompt = self.build_insight_prompt(context)
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a lead intelligence expert. Analyze the provided lead data and generate actionable business insights. Focus on practical recommendations for sales outreach, pain points, and business opportunities."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            insights = json.loads(response.choices[0].message.content)
            
            # Add metadata
            insights['generated_at'] = datetime.utcnow().isoformat()
            insights['lead_id'] = lead.id
            insights['confidence_score'] = self.calculate_confidence_score(context)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights for lead {lead.id}: {e}")
            return {'error': str(e)}
    
    def build_insight_prompt(self, context: Dict[str, Any]) -> str:
        """Build a comprehensive prompt for AI analysis"""
        basic_info = context.get('basic_info', {})
        company_research = context.get('company_research', {})
        industry_insights = context.get('industry_insights', {})
        web_presence = context.get('web_presence', {})
        contact_analysis = context.get('contact_analysis', {})
        
        prompt = f"""
        Analyze this business lead and provide insights in JSON format:

        COMPANY INFORMATION:
        - Name: {basic_info.get('company_name')}
        - Industry: {basic_info.get('industry')}
        - Location: {basic_info.get('location')}
        - Size: {basic_info.get('company_size')}
        - Quality Score: {basic_info.get('quality_score')}/100

        CONTACT DETAILS:
        - Contact Person: {basic_info.get('contact_name', 'Unknown')}
        - Email: {basic_info.get('email', 'Not provided')}
        - Phone: {basic_info.get('phone', 'Not provided')}
        - Website: {basic_info.get('website', 'Not provided')}

        INDUSTRY CONTEXT:
        - Common Pain Points: {', '.join(industry_insights.get('common_pain_points', []))}
        - Seasonal Factors: {', '.join(industry_insights.get('seasonal_factors', []))}
        - Technology Trends: {', '.join(industry_insights.get('technology_adoption', []))}

        WEB PRESENCE:
        - Contact Accessibility Score: {web_presence.get('contact_accessibility', 0)}/10
        - Content Quality Score: {web_presence.get('content_quality', 0)}/10
        - Mobile Friendly: {web_presence.get('mobile_friendly', False)}
        - SSL Enabled: {web_presence.get('ssl_enabled', False)}

        CONTACT ANALYSIS:
        - Email Type: {contact_analysis.get('email_domain_type', 'unknown')}
        - Contact Completeness: {contact_analysis.get('contact_completeness', 0)}%
        - Professional Indicators: {', '.join(contact_analysis.get('professional_indicators', []))}

        Please provide a JSON response with these fields:
        {{
            "lead_priority": "high|medium|low",
            "key_insights": ["insight1", "insight2", "insight3"],
            "pain_points": ["pain1", "pain2"],
            "outreach_recommendations": ["rec1", "rec2", "rec3"],
            "best_contact_method": "email|phone|website",
            "optimal_timing": "description of best time to contact",
            "value_proposition_angles": ["angle1", "angle2"],
            "competitive_advantages": ["advantage1", "advantage2"],
            "risk_factors": ["risk1", "risk2"],
            "next_steps": ["step1", "step2", "step3"]
        }}
        """
        
        return prompt
    
    def calculate_confidence_score(self, context: Dict[str, Any]) -> float:
        """Calculate confidence score based on available data quality"""
        score = 0.0
        
        basic_info = context.get('basic_info', {})
        web_presence = context.get('web_presence', {})
        contact_analysis = context.get('contact_analysis', {})
        
        # Basic information completeness (40% weight)
        if basic_info.get('email'):
            score += 0.1
        if basic_info.get('phone'):
            score += 0.1
        if basic_info.get('website'):
            score += 0.1
        if basic_info.get('location'):
            score += 0.05
        if basic_info.get('contact_name'):
            score += 0.05
        
        # Web presence quality (30% weight)
        web_score = (web_presence.get('contact_accessibility', 0) + 
                    web_presence.get('content_quality', 0)) / 20.0
        score += web_score * 0.3
        
        # Contact analysis quality (30% weight)
        contact_score = contact_analysis.get('contact_completeness', 0) / 100.0
        score += contact_score * 0.3
        
        return min(score, 1.0)
    
    def generate_personalized_outreach(self, lead: Lead, outreach_type: str = 'email') -> Dict[str, str]:
        """Generate personalized outreach content using RAG"""
        if not self.openai_client:
            return {'error': 'OpenAI API not configured'}
        
        try:
            # Get lead insights
            context = self.gather_lead_context(lead)
            insights = self.generate_lead_insights(lead)
            
            # Build outreach prompt
            prompt = f"""
            Create a personalized {outreach_type} outreach for this business lead:

            COMPANY: {lead.company_name}
            INDUSTRY: {lead.industry}
            LOCATION: {lead.location}
            CONTACT: {lead.contact_name or 'Business Owner'}

            KEY INSIGHTS: {', '.join(insights.get('key_insights', []))}
            PAIN POINTS: {', '.join(insights.get('pain_points', []))}
            RECOMMENDED APPROACH: {', '.join(insights.get('outreach_recommendations', []))}

            Create a professional, personalized {outreach_type} that:
            1. References their specific industry and location
            2. Addresses likely pain points
            3. Offers clear value proposition
            4. Includes soft call-to-action
            5. Maintains professional but friendly tone

            Provide response in JSON format:
            {{
                "subject": "email subject line",
                "opening": "personalized opening paragraph",
                "body": "main message body",
                "closing": "call to action and closing",
                "full_message": "complete formatted message"
            }}
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert at writing personalized {outreach_type} outreach for B2B sales. Create compelling, relevant messages that resonate with local service businesses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=800
            )
            
            outreach_content = json.loads(response.choices[0].message.content)
            outreach_content['generated_at'] = datetime.utcnow().isoformat()
            outreach_content['lead_id'] = lead.id
            outreach_content['outreach_type'] = outreach_type
            
            return outreach_content
            
        except Exception as e:
            logger.error(f"Error generating outreach for lead {lead.id}: {e}")
            return {'error': str(e)}

# Initialize RAG system
rag_system = LeadRAGSystem()