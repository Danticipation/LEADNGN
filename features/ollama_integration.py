"""
Ollama Integration for LeadNGN
Local AI analysis using Mistral 7B via Ollama
"""

import logging
import json
import re
from typing import Dict, List, Optional
from datetime import datetime
from models import Lead, db

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logging.warning("Ollama not available - install with: pip install ollama")

logger = logging.getLogger(__name__)

class OllamaAnalyzer:
    """Local AI analysis using Mistral 7B via Ollama"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model = 'mistral:7b'
        self.available = OLLAMA_AVAILABLE
    
    def test_connection(self) -> Dict:
        """Test if Ollama and Mistral 7B are working"""
        if not self.available:
            return {
                'status': 'unavailable',
                'error': 'Ollama not installed',
                'solution': 'Run: pip install ollama'
            }
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{
                    'role': 'user', 
                    'content': 'Respond with exactly: {"status": "working", "model": "mistral-7b"}'
                }],
                options={'temperature': 0.1}
            )
            
            response_text = response['message']['content'].strip()
            self.logger.info(f"Ollama test response: {response_text}")
            
            return {
                'status': 'working',
                'model': self.model,
                'response': response_text,
                'available': True
            }
            
        except Exception as e:
            self.logger.error(f"Ollama connection failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'available': False,
                'solution': 'Ensure Ollama is running and mistral:7b model is downloaded'
            }
    
    def analyze_lead_with_ollama(self, lead_data: Dict) -> Dict:
        """Analyze lead using local Mistral 7B via Ollama"""
        if not self.available:
            return self._generate_fallback_analysis(lead_data)
        
        # Create the analysis prompt
        prompt = f"""
You are a business intelligence analyst specializing in B2B lead qualification. Analyze this business and provide structured insights.

BUSINESS INFORMATION:
Company: {lead_data.get('company_name', 'Unknown')}
Website: {lead_data.get('website', 'Not provided')}
Industry: {lead_data.get('industry', 'Unknown')}
Location: {lead_data.get('location', 'Unknown')}
Contact: {lead_data.get('contact_name', 'Unknown')}
Description: {lead_data.get('description', 'Unknown')}

ANALYSIS REQUIREMENTS:
Provide a JSON response with exactly this structure:

{{
    "business_overview": "2-3 sentence summary of the business",
    "pain_points": ["specific challenge 1", "specific challenge 2", "specific challenge 3"],
    "industry_positioning": "brief assessment of their market position",
    "technology_adoption": "basic|medium|advanced",
    "employee_count_estimate": "small|medium|large", 
    "revenue_assessment": "small|medium|high",
    "business_maturity": "startup|established|enterprise",
    "decision_maker_profile": "brief description of likely decision maker",
    "engagement_strategy": "recommended approach for initial contact",
    "automation_opportunities": ["opportunity 1", "opportunity 2", "opportunity 3"],
    "competitive_advantages": ["advantage 1", "advantage 2"],
    "growth_potential": "low|medium|high",
    "seasonal_factors": "any seasonal business considerations",
    "confidence_score": 85,
    "analysis_provider": "ollama_mistral7b"
}}

Focus on identifying automation opportunities and operational challenges that AI agents could solve.

RESPOND ONLY WITH VALID JSON. NO OTHER TEXT.
"""

        try:
            # Call Ollama
            response = ollama.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                options={
                    'temperature': 0.3,  # Lower temperature for more consistent output
                    'top_p': 0.9,
                    'repeat_penalty': 1.1,
                    'num_predict': 800  # Limit response length
                }
            )
            
            # Extract and parse JSON
            response_text = response['message']['content'].strip()
            
            # Clean up response if it has markdown formatting
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            # Parse JSON
            analysis_data = json.loads(response_text)
            
            # Ensure required fields exist
            analysis_data = self._validate_analysis_data(analysis_data)
            
            self.logger.info(f"Ollama analysis completed for {lead_data.get('company_name')}")
            return analysis_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error with Ollama response: {e}")
            self.logger.error(f"Raw response: {response_text}")
            
            # Fallback - try to extract JSON from response
            return self._extract_json_fallback(response_text, lead_data)
            
        except Exception as e:
            self.logger.error(f"Error calling Ollama: {e}")
            return self._generate_fallback_analysis(lead_data)
    
    def generate_consultant_email_ollama(self, lead_id: int) -> Dict:
        """Generate consultant email using Ollama"""
        if not self.available:
            # Fallback to existing consultant approach
            from features.consultant_approach import consultant_approach
            return consultant_approach.generate_consultant_email(lead_id)
        
        try:
            # Get lead and analysis data
            lead = Lead.query.get(lead_id)
            if not lead:
                return {'error': 'Lead not found'}
            
            ai_data = {}
            if lead.ai_analysis:
                try:
                    ai_data = json.loads(lead.ai_analysis)
                except:
                    ai_data = {}
            
            # Assess business type (use existing function)
            from features.consultant_approach import consultant_approach
            assessment = consultant_approach.assess_business_for_consultant_approach(lead_id)
            
            # Create email generation prompt
            prompt = f"""
You are an expert B2B email copywriter specializing in business automation consulting. Write a personalized consultant-style email.

LEAD INFORMATION:
Company: {lead.company_name}
Contact: {lead.contact_name or 'Business Owner'}
Industry: {lead.industry}
Location: {lead.location}
Business Type: {assessment['business_type']}
Setup Time: {assessment['setup_time']}
Pain Points: {ai_data.get('pain_points', ['operational efficiency', 'customer management', 'business automation'])}

EMAIL REQUIREMENTS:
- Consultant positioning (expert advisor, not vendor)
- Focus on complete business automation solution
- Professional but conversational tone
- Include specific pain point reference
- Free consultation offer
- {assessment['setup_time']} call duration

Generate 3 subject line options and 1 email body.

RESPOND IN THIS EXACT JSON FORMAT:
{{
    "subject_lines": [
        "subject option 1",
        "subject option 2", 
        "subject option 3"
    ],
    "email_body": "full email text here with proper formatting"
}}

RESPOND ONLY WITH VALID JSON. NO OTHER TEXT.
"""

            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                options={
                    'temperature': 0.4,
                    'top_p': 0.9,
                    'num_predict': 1000
                }
            )
            
            response_text = response['message']['content'].strip()
            
            # Clean markdown formatting
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            email_data = json.loads(response_text)
            
            # Add additional metadata
            email_data['business_assessment'] = assessment
            email_data['personalization_used'] = {
                'contact_name': lead.contact_name or 'there',
                'company_name': lead.company_name,
                'business_type': assessment['business_type'],
                'setup_time': assessment['setup_time'],
                'ai_provider': 'ollama_mistral7b'
            }
            
            # Add consultant positioning flag
            email_data['consultant_positioning'] = True
            email_data['template_type'] = 'consultant_introduction'
            
            return {
                'success': True,
                'email_data': email_data,
                'generated_at': datetime.utcnow().isoformat(),
                'lead_id': lead_id,
                'ai_provider': 'ollama_mistral7b'
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Email JSON parsing error: {e}")
            # Fallback to existing system
            from features.consultant_approach import consultant_approach
            return consultant_approach.generate_consultant_email(lead_id)
            
        except Exception as e:
            self.logger.error(f"Error generating email with Ollama: {e}")
            # Fallback to existing system
            from features.consultant_approach import consultant_approach
            return consultant_approach.generate_consultant_email(lead_id)
    
    def _extract_json_fallback(self, text: str, lead_data: Dict) -> Dict:
        """Try to extract JSON from malformed response"""
        # Look for JSON-like structure
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Return minimal structure if all else fails
        return self._generate_fallback_analysis(lead_data)
    
    def _generate_fallback_analysis(self, lead_data: Dict) -> Dict:
        """Generate basic fallback analysis when Ollama fails"""
        company_name = lead_data.get('company_name', 'Unknown Company')
        industry = lead_data.get('industry', 'Unknown')
        
        return {
            "business_overview": f"{company_name} is a {industry.lower()} business that could benefit from automation solutions.",
            "pain_points": [
                "Manual process inefficiencies",
                "Customer communication challenges", 
                "Data management complexity"
            ],
            "industry_positioning": "Standard market participant",
            "technology_adoption": "medium",
            "employee_count_estimate": "medium",
            "revenue_assessment": "medium",
            "business_maturity": "established",
            "decision_maker_profile": "Business owner or operations manager",
            "engagement_strategy": "Professional consultation approach",
            "automation_opportunities": [
                "Customer service automation",
                "Appointment scheduling",
                "Lead management"
            ],
            "competitive_advantages": ["Local market presence", "Industry experience"],
            "growth_potential": "medium",
            "seasonal_factors": "Standard business patterns",
            "confidence_score": 65,
            "analysis_provider": "fallback_system"
        }
    
    def _validate_analysis_data(self, data: Dict) -> Dict:
        """Ensure analysis data has all required fields"""
        required_fields = {
            'business_overview': 'Professional business analysis',
            'pain_points': ['Business efficiency challenges'],
            'industry_positioning': 'Market participant',
            'technology_adoption': 'medium',
            'employee_count_estimate': 'medium',
            'revenue_assessment': 'medium',
            'business_maturity': 'established',
            'decision_maker_profile': 'Business decision maker',
            'engagement_strategy': 'Professional approach',
            'automation_opportunities': ['Process improvement'],
            'competitive_advantages': ['Industry expertise'],
            'growth_potential': 'medium',
            'seasonal_factors': 'Standard patterns',
            'confidence_score': 70,
            'analysis_provider': 'ollama_mistral7b'
        }
        
        for field, default in required_fields.items():
            if field not in data or not data[field]:
                data[field] = default
        
        return data

# Global Ollama analyzer instance
ollama_analyzer = OllamaAnalyzer()