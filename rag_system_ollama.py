"""
RAG (Retrieval-Augmented Generation) System for LeadNGN using Local Ollama
Provides intelligent lead insights, company research, and personalized outreach
"""

import os
import json
import logging
import requests
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, urljoin
import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class LeadRAGSystem:
    """RAG system for intelligent lead analysis and content generation using local Ollama"""
    
    def __init__(self):
        self.ai_available = False
        self.model_name = "llama2:13b"
        self.setup_ollama()
        self.knowledge_base = {}
        
    def setup_ollama(self):
        """Initialize local Ollama client"""
        try:
            # Test connection to local Ollama instance
            response = requests.get('http://localhost:11434/api/tags', timeout=5)
            if response.status_code == 200:
                self.ai_available = True
                logger.info("Ollama local LLM client initialized successfully")
            else:
                logger.warning("Ollama service not available on localhost:11434")
                self.ai_available = False
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            logger.info("Please ensure Ollama is running with: ollama run llama2:13b")
            self.ai_available = False
    
    def call_ollama_api(self, prompt: str, task_type: str = "general") -> Dict[str, Any]:
        """Call local Ollama API for text generation"""
        
        # Customize system prompt based on task type
        if task_type == "lead_analysis":
            system_prompt = """You are a B2B lead analysis expert. Analyze the provided lead data and respond with a JSON object containing:
{
  "lead_priority": "high|medium|low",
  "key_insights": ["insight1", "insight2", "insight3"],
  "pain_points": ["pain1", "pain2"],
  "outreach_recommendations": ["rec1", "rec2"],
  "best_contact_method": "email|phone|linkedin",
  "optimal_timing": "business hours description",
  "next_steps": ["step1", "step2", "step3"]
}
Be concise and actionable. Focus on business value and conversion opportunities."""
        elif task_type == "outreach":
            system_prompt = """You are a B2B outreach specialist. Create personalized, professional outreach content. Respond with JSON:
{
  "subject": "compelling subject line",
  "full_message": "complete email text with greeting, value proposition, and call to action"
}
Make it personalized, valuable, and action-oriented. Avoid spam language."""
        else:
            system_prompt = "You are a helpful business intelligence assistant. Provide clear, actionable insights."
        
        full_prompt = f"{system_prompt}\n\nAnalyze this lead data:\n{prompt}"
        
        try:
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': self.model_name,
                    'prompt': full_prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.3,
                        'top_p': 0.9,
                        'top_k': 40
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')
                
                # Try to extract JSON from the response
                try:
                    # Look for JSON content in the response
                    json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    else:
                        # Fallback structured response
                        return self.create_fallback_response(task_type, generated_text)
                except json.JSONDecodeError:
                    return self.create_fallback_response(task_type, generated_text)
            else:
                raise Exception(f"Ollama API returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return self.create_fallback_response(task_type, str(e))
    
    def create_fallback_response(self, task_type: str, content: str) -> Dict[str, Any]:
        """Create structured fallback response when JSON parsing fails"""
        if task_type == "lead_analysis":
            return {
                "lead_priority": "medium",
                "key_insights": [content[:200] + "..." if len(content) > 200 else content],
                "pain_points": ["Analysis available in raw format"],
                "outreach_recommendations": ["Review the generated analysis"],
                "best_contact_method": "email",
                "optimal_timing": "business hours",
                "next_steps": ["Follow up based on analysis"]
            }
        elif task_type == "outreach":
            return {
                "subject": "Business Partnership Opportunity",
                "full_message": content[:500] + "..." if len(content) > 500 else content
            }
        else:
            return {"analysis": content}
    
    def gather_lead_context(self, lead) -> Dict[str, Any]:
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
    
    def extract_basic_lead_info(self, lead) -> Dict[str, Any]:
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
            'source': lead.source,
            'created_at': lead.created_at.isoformat() if lead.created_at else None
        }
    
    def research_company(self, lead) -> Dict[str, Any]:
        """Research company information from web sources"""
        research = {
            'website_content': {},
            'news_mentions': [],
            'social_presence': {}
        }
        
        try:
            if lead.website:
                research['website_content'] = self.scrape_company_website(lead.website)
            
            research['news_mentions'] = self.search_company_news(lead.company_name, lead.location)
            
        except Exception as e:
            logger.warning(f"Error researching company {lead.company_name}: {e}")
        
        return research
    
    def scrape_company_website(self, website_url: str) -> Dict[str, Any]:
        """Scrape company website for business intelligence"""
        content = {
            'main_text': '',
            'services': [],
            'about_info': '',
            'contact_info': {},
            'technology_indicators': []
        }
        
        try:
            # Use trafilatura for clean text extraction
            downloaded = trafilatura.fetch_url(website_url)
            if downloaded:
                text = trafilatura.extract(downloaded)
                if text:
                    content['main_text'] = text[:2000]  # Limit text length
            
            # Get HTML for additional analysis
            response = requests.get(website_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract services/offerings
                service_keywords = ['service', 'solution', 'offer', 'product']
                for keyword in service_keywords:
                    elements = soup.find_all(text=re.compile(keyword, re.I))
                    for element in elements[:3]:
                        if len(element.strip()) > 10:
                            content['services'].append(element.strip()[:100])
                
                # Look for technology indicators
                tech_indicators = soup.find_all(['script', 'link', 'meta'])
                for indicator in tech_indicators[:5]:
                    if indicator.get('src') or indicator.get('href'):
                        url = indicator.get('src') or indicator.get('href')
                        if any(tech in url.lower() for tech in ['wordpress', 'shopify', 'wix', 'squarespace']):
                            content['technology_indicators'].append(url.lower())
                
        except Exception as e:
            logger.warning(f"Error scraping website {website_url}: {e}")
        
        return content
    
    def search_company_news(self, company_name: str, location: str = None) -> List[Dict[str, str]]:
        """Search for recent news and mentions about the company"""
        news_items = []
        
        try:
            # Simple search approach using DuckDuckGo-like queries
            search_query = f"{company_name}"
            if location:
                search_query += f" {location}"
            
            # Note: In a production environment, you would integrate with news APIs
            # For now, return placeholder structure
            news_items.append({
                'title': f"Industry news related to {company_name}",
                'snippet': f"Local business information for {company_name} in {location or 'their area'}",
                'source': 'Local business directory',
                'date': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.warning(f"Error searching news for {company_name}: {e}")
        
        return news_items
    
    def get_industry_insights(self, industry: str) -> Dict[str, Any]:
        """Get industry-specific insights and trends"""
        if not industry:
            return {}
        
        # Industry-specific pain points and trends
        industry_data = {
            'HVAC': {
                'common_pain_points': [
                    'Seasonal demand fluctuations',
                    'Emergency service scheduling',
                    'Skilled technician shortage',
                    'Equipment maintenance tracking'
                ],
                'technology_adoption': [
                    'Smart thermostat integration',
                    'Mobile scheduling apps',
                    'IoT monitoring systems'
                ],
                'typical_challenges': [
                    'Customer retention',
                    'Inventory management',
                    'Emergency response times'
                ]
            },
            'Plumbing': {
                'common_pain_points': [
                    'Emergency call management',
                    'Parts inventory tracking',
                    'Permit and code compliance',
                    'Customer communication'
                ],
                'technology_adoption': [
                    'Digital inspection tools',
                    'Customer management systems',
                    'Online booking platforms'
                ],
                'typical_challenges': [
                    'Service area optimization',
                    'Pricing transparency',
                    'Quality assurance'
                ]
            },
            'Dental': {
                'common_pain_points': [
                    'Patient scheduling conflicts',
                    'Insurance claim processing',
                    'Equipment maintenance costs',
                    'Patient retention'
                ],
                'technology_adoption': [
                    'Digital imaging systems',
                    'Patient management software',
                    'Online appointment booking'
                ],
                'typical_challenges': [
                    'New patient acquisition',
                    'Treatment plan communication',
                    'Regulatory compliance'
                ]
            },
            'Legal Services': {
                'common_pain_points': [
                    'Case management complexity',
                    'Client communication',
                    'Document organization',
                    'Billing transparency'
                ],
                'technology_adoption': [
                    'Legal practice management software',
                    'Document automation tools',
                    'Client portals'
                ],
                'typical_challenges': [
                    'Client acquisition',
                    'Time tracking accuracy',
                    'Competitive differentiation'
                ]
            }
        }
        
        return industry_data.get(industry, {
            'common_pain_points': ['Customer acquisition', 'Operational efficiency'],
            'technology_adoption': ['Digital marketing', 'Customer management'],
            'typical_challenges': ['Competition', 'Growth management']
        })
    
    def analyze_web_presence(self, website_url: str) -> Dict[str, Any]:
        """Analyze company's web presence and digital maturity"""
        analysis = {
            'ssl_enabled': False,
            'mobile_friendly': False,
            'contact_accessibility': 0,
            'content_quality': 0,
            'technology_stack': []
        }
        
        try:
            # Check SSL
            if website_url.startswith('https://'):
                analysis['ssl_enabled'] = True
            
            # Fetch and analyze webpage
            response = requests.get(website_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Check mobile responsiveness indicators
                viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
                if viewport_meta:
                    analysis['mobile_friendly'] = True
                
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
    
    def analyze_contact_patterns(self, lead) -> Dict[str, Any]:
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
                if domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                    analysis['email_domain_type'] = 'personal_domain'
                else:
                    analysis['email_domain_type'] = 'business_domain'
            
            # Analyze phone format
            if lead.phone:
                phone_clean = re.sub(r'[^\d]', '', lead.phone)
                if len(phone_clean) == 10:
                    if '-' in lead.phone or '.' in lead.phone:
                        analysis['phone_format'] = 'formatted_us'
                    elif '(' in lead.phone and ')' in lead.phone:
                        analysis['phone_format'] = 'parentheses_format'
                    else:
                        analysis['phone_format'] = 'plain_digits'
                elif len(phone_clean) == 11 and phone_clean.startswith('1'):
                    analysis['phone_format'] = 'us_with_country_code'
            
            # Calculate contact completeness
            completeness = 0
            if lead.email:
                completeness += 25
            if lead.phone:
                completeness += 25
            if lead.website:
                completeness += 20
            if lead.contact_name:
                completeness += 15
            if lead.location:
                completeness += 15
            
            analysis['contact_completeness'] = completeness
            
            # Professional indicators
            if lead.website and lead.website.startswith('https://'):
                analysis['professional_indicators'].append('SSL_certificate')
            
            if lead.email and analysis['email_domain_type'] == 'business_domain':
                analysis['professional_indicators'].append('business_email_domain')
            
            if lead.phone and analysis['phone_format'] in ['formatted_us', 'parentheses_format']:
                analysis['professional_indicators'].append('formatted_phone')
            
        except Exception as e:
            logger.warning(f"Error analyzing contact patterns for lead {lead.id}: {e}")
        
        return analysis
    
    def generate_lead_insights(self, lead) -> Dict[str, Any]:
        """Generate AI-powered insights about a lead using local Ollama"""
        if not self.ai_available:
            return {
                'error': 'Local Ollama LLM not available. Please start Ollama with: ollama run llama2:13b',
                'key_insights': ['Local AI model required for analysis'],
                'lead_priority': 'unknown'
            }
        
        try:
            # Gather all available context
            context = self.gather_lead_context(lead)
            
            # Create a comprehensive prompt for the AI
            prompt = self.build_insight_prompt(context)
            
            # Call local Ollama API
            insights = self.call_ollama_api(prompt, "lead_analysis")
            
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
        - Contact: {basic_info.get('contact_name')}
        - Quality Score: {basic_info.get('quality_score')}/100

        CONTACT DETAILS:
        - Email: {basic_info.get('email')}
        - Phone: {basic_info.get('phone')}
        - Website: {basic_info.get('website')}
        - Contact Completeness: {contact_analysis.get('contact_completeness', 0)}%

        WEB PRESENCE:
        - SSL Enabled: {web_presence.get('ssl_enabled', False)}
        - Mobile Friendly: {web_presence.get('mobile_friendly', False)}
        - Contact Accessibility: {web_presence.get('contact_accessibility', 0)}/10

        INDUSTRY CONTEXT:
        - Common Pain Points: {', '.join(industry_insights.get('common_pain_points', []))}
        - Technology Trends: {', '.join(industry_insights.get('technology_adoption', []))}

        Please analyze this lead and respond with a JSON object containing:
        - lead_priority: high/medium/low
        - key_insights: array of 3-5 actionable insights
        - pain_points: array of likely business challenges
        - outreach_recommendations: array of approach suggestions
        - best_contact_method: email/phone/website
        - optimal_timing: recommended outreach timing
        - next_steps: array of specific action items
        """
        
        return prompt
    
    def calculate_confidence_score(self, context: Dict[str, Any]) -> float:
        """Calculate confidence score based on available data quality"""
        score = 0.0
        
        basic_info = context.get('basic_info', {})
        contact_analysis = context.get('contact_analysis', {})
        web_presence = context.get('web_presence', {})
        
        # Basic information completeness (40% weight)
        if basic_info.get('company_name'):
            score += 0.1
        if basic_info.get('industry'):
            score += 0.1
        if basic_info.get('location'):
            score += 0.1
        if basic_info.get('email'):
            score += 0.1
        
        # Contact quality (30% weight)
        contact_completeness = contact_analysis.get('contact_completeness', 0)
        score += (contact_completeness / 100) * 0.3
        
        # Web presence (30% weight)
        if web_presence.get('ssl_enabled'):
            score += 0.1
        if web_presence.get('mobile_friendly'):
            score += 0.1
        if web_presence.get('contact_accessibility', 0) > 5:
            score += 0.1
        
        return min(score, 1.0)
    
    def generate_personalized_outreach(self, lead, outreach_type: str = 'email') -> Dict[str, str]:
        """Generate personalized outreach content using local Ollama"""
        if not self.ai_available:
            return {
                'error': 'Local Ollama LLM not available. Please start Ollama with: ollama run llama2:13b',
                'subject': 'Business Partnership Opportunity',
                'full_message': 'Please configure local AI to generate personalized outreach.'
            }
        
        try:
            # First generate insights for the lead
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
            """
            
            # Call local Ollama API for outreach generation
            outreach_content = self.call_ollama_api(prompt, "outreach")
            outreach_content['generated_at'] = datetime.utcnow().isoformat()
            
            return outreach_content
            
        except Exception as e:
            logger.error(f"Error generating outreach for lead {lead.id}: {e}")
            return {'error': str(e)}


# Global RAG system instance
rag_system = LeadRAGSystem()