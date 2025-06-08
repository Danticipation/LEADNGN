"""
RAG (Retrieval-Augmented Generation) System for LeadNGN using OpenAI
Provides intelligent lead insights, company research, and personalized outreach
"""

import os
import json
import re
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
import trafilatura
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LeadRAGSystem:
    """RAG system for intelligent lead analysis and content generation using OpenAI"""
    
    def __init__(self):
        """Initialize the RAG system with OpenAI client"""
        self.openai_client = None
        self.setup_openai()
    
    def setup_openai(self):
        """Initialize OpenAI client"""
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.error("OPENAI_API_KEY not found in environment variables")
                return False
            
            self.openai_client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            return False
    
    def call_openai_api(self, prompt: str, task_type: str = "general") -> Dict[str, Any]:
        """Call OpenAI API for text generation"""
        try:
            if not self.openai_client:
                raise Exception("OpenAI client not initialized")
            
            # Use different models and parameters based on task type
            if task_type == "analysis":
                model = "gpt-4o"  # Latest OpenAI model
                max_tokens = 1500
                temperature = 0.3
            elif task_type == "outreach":
                model = "gpt-4o"
                max_tokens = 800
                temperature = 0.7
            else:
                model = "gpt-4o"
                max_tokens = 1000
                temperature = 0.5
            
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert business analyst and sales strategist. Provide detailed, actionable insights in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.info(f"OpenAI API call successful for task: {task_type}")
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response, returning raw content")
                return self.create_fallback_response(task_type, content)
                
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            return self.create_fallback_response(task_type, f"Error: {str(e)}")
    
    def create_fallback_response(self, task_type: str, content: str) -> Dict[str, Any]:
        """Create structured fallback response when JSON parsing fails"""
        if task_type == "analysis":
            return {
                "business_intelligence": {
                    "overview": content[:200] + "..." if len(content) > 200 else content,
                    "pain_points": ["Analysis unavailable - API response format issue"],
                    "opportunities": ["Please try again or check API configuration"],
                    "industry_position": "Unable to determine"
                },
                "engagement_strategy": {
                    "approach": "Direct outreach recommended",
                    "timing": "Immediate follow-up",
                    "key_messages": ["Focus on core value proposition"]
                },
                "confidence_score": 0.3,
                "next_steps": ["Retry analysis", "Manual research recommended"]
            }
        elif task_type == "outreach":
            return {
                "subject_line": "Partnership Opportunity",
                "email_content": "Hello,\n\nI hope this message finds you well. I wanted to reach out regarding potential opportunities for collaboration.\n\nBest regards",
                "key_points": ["Generic outreach due to API issue"],
                "tone": "Professional",
                "follow_up_strategy": "Manual personalization needed"
            }
        else:
            return {
                "status": "error",
                "message": content,
                "recommendation": "Please try again or contact support"
            }
    
    def gather_lead_context(self, lead) -> Dict[str, Any]:
        """Gather comprehensive context about a lead from multiple sources"""
        context = {
            "basic_info": self.extract_basic_lead_info(lead),
            "company_research": {},
            "industry_insights": {},
            "web_presence": {},
            "contact_analysis": {}
        }
        
        try:
            # Company research
            if lead.website:
                context["company_research"] = self.research_company(lead)
                context["web_presence"] = self.analyze_web_presence(lead.website)
            
            # Industry insights
            if lead.industry:
                context["industry_insights"] = self.get_industry_insights(lead.industry)
            
            # Contact pattern analysis
            context["contact_analysis"] = self.analyze_contact_patterns(lead)
            
        except Exception as e:
            logger.error(f"Error gathering lead context: {str(e)}")
            context["errors"] = [str(e)]
        
        return context
    
    def extract_basic_lead_info(self, lead) -> Dict[str, Any]:
        """Extract and structure basic lead information"""
        return {
            "company_name": lead.company_name,
            "contact_name": lead.contact_name,
            "email": lead.email,
            "phone": lead.phone,
            "website": lead.website,
            "industry": lead.industry,
            "location": lead.location,
            "company_size": lead.company_size,
            "quality_score": lead.quality_score,
            "status": lead.lead_status,
            "source": lead.source,
            "description": lead.description,
            "revenue_estimate": lead.revenue_estimate,
            "employee_count": lead.employee_count,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "tags": lead.get_tags() if hasattr(lead, 'get_tags') else [],
            "social_media": lead.get_social_media() if hasattr(lead, 'get_social_media') else {}
        }
    
    def research_company(self, lead) -> Dict[str, Any]:
        """Research company information from web sources"""
        research_data = {
            "website_analysis": {},
            "news_mentions": [],
            "business_intelligence": {}
        }
        
        try:
            if lead.website:
                research_data["website_analysis"] = self.scrape_company_website(lead.website)
            
            if lead.company_name:
                research_data["news_mentions"] = self.search_company_news(
                    lead.company_name, 
                    lead.location
                )
        except Exception as e:
            logger.error(f"Error researching company: {str(e)}")
            research_data["error"] = str(e)
        
        return research_data
    
    def scrape_company_website(self, website_url: str) -> Dict[str, Any]:
        """Scrape company website for business intelligence"""
        try:
            # Add protocol if missing
            if not website_url.startswith(('http://', 'https://')):
                website_url = 'https://' + website_url
            
            # Download and extract text content
            downloaded = trafilatura.fetch_url(website_url)
            if not downloaded:
                return {"error": "Could not download website content"}
            
            text_content = trafilatura.extract(downloaded)
            if not text_content:
                return {"error": "Could not extract text from website"}
            
            # Extract structured information
            website_data = {
                "content_summary": text_content[:500] + "..." if len(text_content) > 500 else text_content,
                "content_length": len(text_content),
                "url": website_url,
                "extracted_at": datetime.now().isoformat()
            }
            
            # Extract key business information
            website_data["services"] = self.extract_services_from_text(text_content)
            website_data["contact_info"] = self.extract_contact_info_from_text(text_content)
            
            return website_data
            
        except Exception as e:
            logger.error(f"Error scraping website {website_url}: {str(e)}")
            return {"error": str(e), "url": website_url}
    
    def extract_services_from_text(self, text: str) -> List[str]:
        """Extract services/offerings from website text"""
        services = []
        service_keywords = [
            'services', 'solutions', 'offerings', 'products', 'specializes',
            'provides', 'offers', 'delivers', 'expertise', 'capabilities'
        ]
        
        for keyword in service_keywords:
            pattern = rf'{keyword}[:\s]+([^.!?]*)'
            matches = re.findall(pattern, text.lower(), re.IGNORECASE)
            for match in matches[:3]:  # Limit to first 3 matches
                if len(match.strip()) > 10:
                    services.append(match.strip()[:100])
        
        return list(set(services))[:5]  # Return unique services, max 5
    
    def extract_contact_info_from_text(self, text: str) -> Dict[str, str]:
        """Extract contact information from website text"""
        contact_info = {}
        
        # Email extraction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact_info["emails"] = list(set(emails))[:3]
        
        # Phone extraction
        phone_pattern = r'(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact_info["phones"] = list(set(phones))[:3]
        
        return contact_info
    
    def search_company_news(self, company_name: str, location: str = None) -> List[Dict[str, str]]:
        """Search for recent news and mentions about the company"""
        # This is a simplified implementation
        # In production, you might use news APIs like NewsAPI, Google News API, etc.
        news_items = []
        
        try:
            # Simulate news search results
            search_query = f"{company_name}"
            if location:
                search_query += f" {location}"
            
            # Return structured placeholder data
            news_items = [
                {
                    "title": f"Recent developments for {company_name}",
                    "summary": "Company continues to grow in the local market",
                    "source": "Industry Research",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "relevance": "medium"
                }
            ]
            
        except Exception as e:
            logger.error(f"Error searching company news: {str(e)}")
        
        return news_items
    
    def get_industry_insights(self, industry: str) -> Dict[str, Any]:
        """Get industry-specific insights and trends"""
        insights = {
            "industry": industry,
            "trends": [],
            "challenges": [],
            "opportunities": [],
            "key_metrics": {}
        }
        
        # Industry-specific insights
        industry_data = {
            "HVAC": {
                "trends": ["Smart home integration", "Energy efficiency focus", "Preventive maintenance"],
                "challenges": ["Seasonal demand fluctuation", "Skilled labor shortage", "Equipment costs"],
                "opportunities": ["Smart thermostat installation", "Energy audits", "Maintenance contracts"]
            },
            "Dental": {
                "trends": ["Teledentistry", "Digital imaging", "Cosmetic procedures growth"],
                "challenges": ["Insurance limitations", "Patient acquisition", "Technology costs"],
                "opportunities": ["Cosmetic dentistry", "Orthodontics", "Preventive care programs"]
            },
            "Legal": {
                "trends": ["Legal tech adoption", "Remote consultations", "Specialization"],
                "challenges": ["Client acquisition", "Billing transparency", "Competition"],
                "opportunities": ["Estate planning", "Business law", "Digital marketing"]
            }
        }
        
        if industry in industry_data:
            insights.update(industry_data[industry])
        else:
            insights["trends"] = ["Digital transformation", "Customer experience focus"]
            insights["challenges"] = ["Market competition", "Cost management"]
            insights["opportunities"] = ["Process optimization", "Technology adoption"]
        
        return insights
    
    def analyze_web_presence(self, website_url: str) -> Dict[str, Any]:
        """Analyze company's web presence and digital maturity"""
        analysis = {
            "website_quality": "unknown",
            "digital_maturity": "unknown",
            "online_presence": {},
            "recommendations": []
        }
        
        try:
            if website_url:
                # Basic website analysis
                response = requests.get(website_url, timeout=10)
                if response.status_code == 200:
                    analysis["website_quality"] = "good"
                    analysis["digital_maturity"] = "moderate"
                else:
                    analysis["website_quality"] = "poor"
                    analysis["digital_maturity"] = "low"
                    
                analysis["recommendations"] = [
                    "Consider mobile optimization",
                    "Implement SEO best practices",
                    "Add contact forms and CTAs"
                ]
                
        except Exception as e:
            logger.error(f"Error analyzing web presence: {str(e)}")
            analysis["error"] = str(e)
        
        return analysis
    
    def analyze_contact_patterns(self, lead) -> Dict[str, Any]:
        """Analyze contact information patterns for insights"""
        analysis = {
            "email_domain": None,
            "phone_format": None,
            "contact_completeness": 0,
            "professionalism_score": 0
        }
        
        contact_fields = [lead.email, lead.phone, lead.contact_name, lead.website]
        analysis["contact_completeness"] = sum(1 for field in contact_fields if field) / len(contact_fields)
        
        if lead.email:
            domain = lead.email.split('@')[-1] if '@' in lead.email else None
            analysis["email_domain"] = domain
            
            # Professional email scoring
            if domain and domain != lead.company_name.lower().replace(' ', '') + '.com':
                analysis["professionalism_score"] += 0.3
            if not any(char.isdigit() for char in lead.email.split('@')[0]):
                analysis["professionalism_score"] += 0.2
        
        if lead.phone:
            analysis["phone_format"] = "formatted" if re.match(r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$', lead.phone) else "unformatted"
        
        return analysis
    
    def generate_lead_insights(self, lead) -> Dict[str, Any]:
        """Generate AI-powered insights about a lead using OpenAI"""
        try:
            # Gather comprehensive context
            context = self.gather_lead_context(lead)
            
            # Build prompt for AI analysis
            prompt = self.build_insight_prompt(context)
            
            # Get AI analysis
            insights = self.call_openai_api(prompt, "analysis")
            
            # Add metadata
            insights["generated_at"] = datetime.now().isoformat()
            insights["confidence_score"] = self.calculate_confidence_score(context)
            insights["data_sources"] = list(context.keys())
            
            logger.info(f"Generated insights for lead: {lead.company_name}")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating lead insights: {str(e)}")
            return {
                "error": str(e),
                "business_intelligence": {
                    "overview": f"Unable to analyze {lead.company_name} due to system error",
                    "pain_points": ["Analysis temporarily unavailable"],
                    "opportunities": ["Manual research recommended"],
                    "industry_position": "Unknown"
                },
                "engagement_strategy": {
                    "approach": "Direct contact recommended",
                    "timing": "Immediate",
                    "key_messages": ["Focus on core value proposition"]
                },
                "confidence_score": 0.2,
                "generated_at": datetime.now().isoformat()
            }
    
    def build_insight_prompt(self, context: Dict[str, Any]) -> str:
        """Build a comprehensive prompt for AI analysis"""
        basic_info = context.get("basic_info", {})
        company_research = context.get("company_research", {})
        industry_insights = context.get("industry_insights", {})
        
        prompt = f"""
Analyze this business lead and provide comprehensive insights in JSON format:

COMPANY INFORMATION:
- Name: {basic_info.get('company_name', 'Unknown')}
- Industry: {basic_info.get('industry', 'Unknown')}
- Location: {basic_info.get('location', 'Unknown')}
- Size: {basic_info.get('company_size', 'Unknown')}
- Website: {basic_info.get('website', 'None')}
- Revenue Estimate: {basic_info.get('revenue_estimate', 'Unknown')}
- Employee Count: {basic_info.get('employee_count', 'Unknown')}

CONTACT INFORMATION:
- Contact: {basic_info.get('contact_name', 'Unknown')}
- Email: {basic_info.get('email', 'None')}
- Phone: {basic_info.get('phone', 'None')}

RESEARCH DATA:
- Website Analysis: {company_research.get('website_analysis', {})}
- Industry Trends: {industry_insights.get('trends', [])}
- Industry Challenges: {industry_insights.get('challenges', [])}

Provide analysis in this exact JSON structure:
{{
    "business_intelligence": {{
        "overview": "2-3 sentence business overview and market position",
        "pain_points": ["list", "of", "likely", "business", "pain", "points"],
        "opportunities": ["list", "of", "growth", "opportunities"],
        "industry_position": "assessment of their market position",
        "decision_makers": ["likely", "decision", "maker", "roles"],
        "budget_indicators": "assessment of budget capacity"
    }},
    "engagement_strategy": {{
        "approach": "recommended engagement approach",
        "timing": "best time to contact",
        "key_messages": ["primary", "value", "propositions", "to", "emphasize"],
        "objection_handling": ["likely", "objections", "and", "responses"],
        "follow_up_strategy": "recommended follow-up approach"
    }},
    "lead_scoring": {{
        "interest_level": "high/medium/low",
        "buying_readiness": "ready/researching/not_ready",
        "authority_level": "decision_maker/influencer/gatekeeper",
        "fit_score": "excellent/good/fair/poor"
    }},
    "next_steps": ["specific", "actionable", "next", "steps"]
}}
"""
        return prompt
    
    def calculate_confidence_score(self, context: Dict[str, Any]) -> float:
        """Calculate confidence score based on available data quality"""
        score = 0.0
        
        basic_info = context.get("basic_info", {})
        
        # Basic information completeness (40% of score)
        required_fields = ['company_name', 'industry', 'email', 'website']
        completed_fields = sum(1 for field in required_fields if basic_info.get(field))
        score += (completed_fields / len(required_fields)) * 0.4
        
        # Additional research data (30% of score)
        if context.get("company_research", {}).get("website_analysis"):
            score += 0.15
        if context.get("industry_insights", {}).get("trends"):
            score += 0.15
        
        # Contact quality (20% of score)
        contact_analysis = context.get("contact_analysis", {})
        score += contact_analysis.get("contact_completeness", 0) * 0.2
        
        # Data recency and source reliability (10% of score)
        score += 0.1  # Base score for real-time analysis
        
        return min(1.0, max(0.0, score))
    
    def generate_personalized_outreach(self, lead, outreach_type: str = 'email') -> Dict[str, str]:
        """Generate personalized outreach content using OpenAI"""
        try:
            # Gather context for personalization
            context = self.gather_lead_context(lead)
            
            # Build outreach prompt
            prompt = self.build_outreach_prompt(context, outreach_type)
            
            # Generate content using OpenAI
            outreach_content = self.call_openai_api(prompt, "outreach")
            
            # Add metadata
            outreach_content["generated_at"] = datetime.now().isoformat()
            outreach_content["lead_id"] = lead.id
            outreach_content["outreach_type"] = outreach_type
            
            logger.info(f"Generated {outreach_type} outreach for: {lead.company_name}")
            return outreach_content
            
        except Exception as e:
            logger.error(f"Error generating outreach content: {str(e)}")
            return {
                "subject_line": f"Partnership Opportunity - {lead.company_name}",
                "email_content": f"Hello {lead.contact_name or 'there'},\n\nI hope this message finds you well. I wanted to reach out to discuss potential opportunities for {lead.company_name}.\n\nBest regards",
                "key_points": ["Generic template due to generation error"],
                "tone": "Professional",
                "follow_up_strategy": "Manual personalization needed",
                "error": str(e)
            }
    
    def build_outreach_prompt(self, context: Dict[str, Any], outreach_type: str) -> str:
        """Build prompt for personalized outreach generation"""
        basic_info = context.get("basic_info", {})
        company_research = context.get("company_research", {})
        industry_insights = context.get("industry_insights", {})
        
        prompt = f"""
Generate a personalized {outreach_type} outreach for this business lead:

COMPANY DETAILS:
- Company: {basic_info.get('company_name', 'Unknown')}
- Contact: {basic_info.get('contact_name', 'Unknown')}
- Industry: {basic_info.get('industry', 'Unknown')}
- Location: {basic_info.get('location', 'Unknown')}
- Website: {basic_info.get('website', 'None')}

BUSINESS CONTEXT:
- Industry Trends: {industry_insights.get('trends', [])}
- Industry Challenges: {industry_insights.get('challenges', [])}
- Company Services: {company_research.get('website_analysis', {}).get('services', [])}

OUTREACH REQUIREMENTS:
- Type: {outreach_type}
- Tone: Professional but friendly
- Length: Concise (under 200 words for email)
- Focus: Value proposition and mutual benefit
- Call to action: Request meeting/call

Generate response in this JSON format:
{{
    "subject_line": "compelling email subject line",
    "email_content": "personalized email body with specific value proposition",
    "key_points": ["main", "value", "points", "highlighted"],
    "tone": "description of tone used",
    "follow_up_strategy": "recommended follow-up approach",
    "personalization_elements": ["specific", "personal", "touches", "used"]
}}
"""
        return prompt