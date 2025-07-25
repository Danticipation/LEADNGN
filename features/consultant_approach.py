"""
Consultant Approach Email System for LeadNgN
Positions outreach as business consulting rather than sales
"""

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime
from models import Lead, db
from features.email_templates import email_template_manager

logger = logging.getLogger(__name__)

class ConsultantApproach:
    """Consultant-positioned business assessment and email generation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.business_assessment_rules = self._initialize_assessment_rules()
        self.consultant_templates = self._initialize_consultant_templates()
    
    def assess_business_for_consultant_approach(self, lead_id: int) -> Dict:
        """Assess business and recommend consultant approach"""
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return {'error': 'Lead not found'}
            
            # Get AI analysis data - use existing lead attributes if ai_analysis not available
            ai_data = {}
            if hasattr(lead, 'ai_analysis') and lead.ai_analysis:
                try:
                    ai_data = json.loads(lead.ai_analysis)
                except:
                    ai_data = {}
            
            # Fallback to basic lead data for assessment
            if not ai_data:
                ai_data = {
                    'company_size': lead.company_size or 'small',
                    'employee_count': getattr(lead, 'employee_count', None) or 5,
                    'revenue_estimate': lead.revenue_estimate or 'small',
                    'quality_score': lead.quality_score or 50
                }
            
            # Determine business type based on AI analysis
            business_type = self._determine_business_type(ai_data, lead)
            
            # Get assessment rules
            assessment_rule = self.business_assessment_rules.get(business_type, 
                                                               self.business_assessment_rules['small_basic'])
            
            return {
                'business_type': business_type,
                'setup_time': assessment_rule['setup_time'],
                'recommendation_focus': assessment_rule['recommendation_focus'],
                'positioning_message': assessment_rule['positioning_message'],
                'template_target': business_type,
                'lead_id': lead_id,
                'company_name': lead.company_name,
                'industry': lead.industry
            }
            
        except Exception as e:
            self.logger.error(f"Business assessment error for lead {lead_id}: {e}")
            return {'error': f'Assessment failed: {str(e)}'}
    
    def generate_consultant_email(self, lead_id: int, template_type: str = 'introduction') -> Dict:
        """Generate consultant-positioned email"""
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return {'error': 'Lead not found'}
            
            # Get business assessment
            assessment = self.assess_business_for_consultant_approach(lead_id)
            if 'error' in assessment:
                return assessment
            
            # Get AI analysis for personalization
            ai_data = {}
            if hasattr(lead, 'ai_analysis') and lead.ai_analysis:
                try:
                    ai_data = json.loads(lead.ai_analysis)
                except:
                    pass
            
            # Use lead attributes for basic personalization if AI analysis not available
            if not ai_data:
                ai_data = {
                    'insights': {
                        'company_analysis': {
                            'strengths': [f'established {lead.industry.lower()} business'],
                            'pain_points': ['operational efficiency', 'customer management', 'automated processes']
                        }
                    }
                }
            
            # Get appropriate consultant template
            template_key = f"{lead.industry}_{assessment['business_type']}_{template_type}"
            template = self._get_consultant_template(lead.industry, assessment['business_type'], template_type)
            
            if not template:
                return {'error': f'No consultant template found for {template_key}'}
            
            # Create personalization data
            personalization = self._create_consultant_personalization(lead, ai_data, assessment)
            
            # Generate email content
            email_body = template['email_body'].format(**personalization)
            subject_options = [subject.format(**personalization) for subject in template['subject_lines']]
            
            return {
                'success': True,
                'email_data': {
                    'subject_options': subject_options,
                    'email_body': email_body,
                    'business_assessment': assessment,
                    'personalization_used': personalization,
                    'template_type': template_type,
                    'consultant_positioning': True
                },
                'lead_id': lead_id,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Consultant email generation error for lead {lead_id}: {e}")
            return {'error': f'Email generation failed: {str(e)}'}
    
    def _determine_business_type(self, ai_data: Dict, lead: Lead) -> str:
        """Determine business type based on AI analysis and lead data"""
        # Use quality score as primary indicator
        quality_score = lead.quality_score or 50
        
        # Use lead attributes
        company_size = lead.company_size or ai_data.get('company_size', 'small')
        employee_count = getattr(lead, 'employee_count', None) or ai_data.get('employee_count', 5)
        revenue_estimate = lead.revenue_estimate or ai_data.get('revenue_estimate', 'small')
        
        # Website quality indicator from AI
        website_quality = ai_data.get('website_quality_score', quality_score)
        
        # Technology adoption indicators
        tech_indicators = ai_data.get('technology_adoption', 'basic')
        
        # Company analysis insights
        company_analysis = ai_data.get('insights', {}).get('company_analysis', {})
        strengths = company_analysis.get('strengths', [])
        
        # Enterprise indicators
        enterprise_signals = [
            website_quality > 80,
            company_size in ['Large', 'Enterprise'],
            revenue_estimate in ['high', '$1M+', 'enterprise'],
            employee_count and employee_count > 50,
            quality_score > 90,
            any('enterprise' in strength.lower() for strength in strengths),
            any('corporation' in strength.lower() for strength in strengths)
        ]
        
        if sum(enterprise_signals) >= 2:
            return 'enterprise'
        
        # Established business indicators
        established_signals = [
            website_quality > 60,
            company_size in ['Medium', 'medium'],
            revenue_estimate in ['medium', '$100K-1M', 'established'],
            employee_count and employee_count > 10,
            quality_score > 70,
            tech_indicators in ['medium', 'high'],
            any('established' in strength.lower() for strength in strengths),
            any('professional' in strength.lower() for strength in strengths)
        ]
        
        if sum(established_signals) >= 2:
            return 'established'
        
        # Default to small/basic
        return 'small_basic'
    
    def _get_consultant_template(self, industry: str, business_type: str, template_type: str) -> Optional[Dict]:
        """Get consultant template by industry, business type, and template type"""
        template_key = f"{industry}_{business_type}_{template_type}"
        return self.consultant_templates.get(template_key)
    
    def _create_consultant_personalization(self, lead: Lead, ai_data: Dict, assessment: Dict) -> Dict:
        """Create personalization data for consultant emails"""
        # Base personalization
        personalization = {
            'contact_name': lead.contact_name or 'there',
            'company_name': lead.company_name,
            'setup_time': assessment['setup_time'],
            'your_name': 'Business Automation Consultant',
            'location': lead.location
        }
        
        # Add consultant-style pain point reference
        personalization['ai_pain_point_reference'] = self._create_consultant_pain_point_reference(ai_data)
        
        # Add industry-specific context
        if lead.industry == 'HVAC':
            city = lead.location.split(',')[0].strip()
            personalization.update({
                'weather_context': f'{city} hitting 115°F',
                'busy_context': 'getting slammed with emergency calls',
                'seasonal_urgency': 'Summer peak season means missed calls = lost revenue'
            })
        elif lead.industry == 'Dental':
            personalization.update({
                'patient_context': 'busy patient schedule',
                'appointment_context': 'appointment booking and patient management',
                'professional_title': 'Dr.'
            })
        elif lead.industry == 'Legal':
            personalization.update({
                'client_context': 'client acquisition and case management',
                'professional_context': 'legal practice automation',
                'professional_title': 'Attorney'
            })
        
        return personalization
    
    def _create_consultant_pain_point_reference(self, ai_data: Dict) -> str:
        """Create consultant-style pain point references"""
        insights = ai_data.get('insights', {})
        company_analysis = insights.get('company_analysis', {})
        pain_points = company_analysis.get('pain_points', [])
        
        # Consultant language focuses on business efficiency, not just problems
        consultant_references = {
            'call_management': "I noticed you might be handling calls manually, which gets overwhelming during peak times like this.",
            'scheduling': "It looks like appointment scheduling could be more streamlined, especially when you're this busy.",
            'customer_tracking': "I see customer information management might be taking more time than it should.",
            'follow_up': "It seems like staying on top of follow-ups gets challenging when you're handling calls all day.",
            'technology': "I can see there are some operational areas where automation could make a huge difference.",
            'growth': "From what I can tell, you're ready for systems that scale with your business growth."
        }
        
        # Match pain points to consultant language
        if pain_points:
            for pain_point in pain_points:
                pain_lower = pain_point.lower()
                if any(word in pain_lower for word in ['call', 'phone', 'answer', 'contact']):
                    return consultant_references['call_management']
                elif any(word in pain_lower for word in ['schedule', 'appointment', 'booking', 'calendar']):
                    return consultant_references['scheduling']
                elif any(word in pain_lower for word in ['customer', 'client', 'track', 'manage']):
                    return consultant_references['customer_tracking']
                elif any(word in pain_lower for word in ['follow', 'communication', 'response']):
                    return consultant_references['follow_up']
                elif any(word in pain_lower for word in ['system', 'technology', 'software']):
                    return consultant_references['technology']
                elif any(word in pain_lower for word in ['growth', 'scale', 'expand']):
                    return consultant_references['growth']
        
        # Default consultant reference
        return consultant_references['technology']
    
    def _initialize_assessment_rules(self) -> Dict:
        """Initialize business assessment rules"""
        return {
            'small_basic': {
                'setup_time': '30-minute setup call',
                'recommendation_focus': 'simple but powerful system that grows with you',
                'positioning_message': 'complete business upgrade'
            },
            'established': {
                'setup_time': '45-minute consultation call',
                'recommendation_focus': 'professional system tailored to your needs',
                'positioning_message': 'streamlined automation solution'
            },
            'enterprise': {
                'setup_time': '60-minute strategy call',
                'recommendation_focus': 'enterprise-level system with full integration',
                'positioning_message': 'comprehensive business automation'
            }
        }
    
    def _initialize_consultant_templates(self) -> Dict:
        """Initialize consultant email templates"""
        return {
            # HVAC Small/Basic Business
            'HVAC_small_basic_introduction': {
                'subject_lines': [
                    "Quick question about {company_name}'s customer tracking",
                    "{contact_name} - upgrade your business systems this weekend?",
                    "From spreadsheets to professional: 30 minutes"
                ],
                'email_body': """Hi {contact_name},

{weather_context} - I bet you're {busy_context} at {company_name}.

{ai_pain_point_reference}

Quick question: What's your current system for tracking customers and appointments? Spreadsheet? Notebook? Just memory?

Here's what I'm thinking: Let's get you set up with a complete system that runs your business automatically. AI handles calls, books appointments, sends follow-ups, tracks everything.

I'll recommend exactly what works best for a business your size - nothing complicated, just professional and automatic.

{setup_time} and you're running like a much bigger company.

Worth upgrading this weekend?

Best,
{your_name}

P.S. Going from "hoping you don't miss calls" to "capturing everything automatically" is a game-changer."""
            },
            
            # HVAC Established Business
            'HVAC_established_introduction': {
                'subject_lines': [
                    "{contact_name} - making {company_name} run automatically",
                    "HVAC automation consultation for established businesses",
                    "Summer heat wave: time to automate {company_name}?"
                ],
                'email_body': """Hi {contact_name},

With {weather_context}, {company_name} is probably handling more calls than your current system can manage efficiently.

{ai_pain_point_reference}

I specialize in taking established HVAC businesses and making them run completely automatically. Whether you need better system integration, automated follow-ups, or just want to capture every call - I can design the right solution.

{setup_time} where I'll:
✓ Assess your current setup
✓ Recommend the best automation approach  
✓ Get your AI agent live for weekend testing
✓ Show you exactly how much more efficient you could be

Free trial to prove it works before you commit to anything.

Worth a consultation this week?

Best,
{your_name}

P.S. Most established businesses are surprised at how much manual work they're still doing unnecessarily."""
            },
            
            # HVAC Enterprise
            'HVAC_enterprise_introduction': {
                'subject_lines': [
                    "Enterprise HVAC automation strategy for {company_name}",
                    "{contact_name} - comprehensive business automation consultation",
                    "Scale {company_name} operations with enterprise automation"
                ],
                'email_body': """Dear {contact_name},

As {company_name} continues to grow, I imagine you're looking for ways to scale operations without proportionally increasing overhead.

{ai_pain_point_reference}

I work with enterprise HVAC companies to implement comprehensive automation systems that integrate with existing infrastructure while dramatically improving efficiency.

{setup_time} to discuss:
✓ Current system assessment and integration opportunities
✓ Enterprise-level automation recommendations
✓ ROI projections and implementation timeline
✓ Custom solution design for your specific needs

I can show you exactly how similar companies have achieved 40-60% efficiency gains while reducing operational costs.

Would you be interested in a strategic consultation?

Best regards,
{your_name}

P.S. Enterprise automation isn't just about efficiency - it's about competitive advantage."""
            },
            
            # Dental Small/Basic Business
            'Dental_small_basic_introduction': {
                'subject_lines': [
                    "Quick question about {company_name}'s patient management",
                    "Dr. {contact_name} - automate your practice this week?",
                    "From manual to automated: 30-minute practice upgrade"
                ],
                'email_body': """Hi Dr. {contact_name},

Hope your practice is thriving! I noticed {company_name} and wanted to ask a quick question.

{ai_pain_point_reference}

What's your current system for managing patient appointments and follow-ups? Still doing a lot manually?

Here's what I'm thinking: Let's set up your practice with automated systems that handle appointment booking, patient reminders, follow-ups, and tracking - all running professionally in the background.

{setup_time} and your practice runs like a much larger operation, but it's still your personal touch with patients.

Worth upgrading your systems?

Best,
{your_name}

P.S. Going from "hoping patients remember their appointments" to "automated reminders and follow-ups" typically increases appointment adherence by 40%."""
            },
            
            # Dental Established Business
            'Dental_established_introduction': {
                'subject_lines': [
                    "Practice automation consultation for established dentists",
                    "Dr. {contact_name} - streamline {company_name} operations",
                    "Professional practice automation for busy dentists"
                ],
                'email_body': """Dear Dr. {contact_name},

I can see {company_name} is an established practice with a strong patient base.

{ai_pain_point_reference}

I specialize in helping established dental practices implement professional automation systems that increase efficiency without changing the personal care approach that makes you successful.

{setup_time} where I'll:
✓ Assess your current practice management systems
✓ Recommend automation that fits your workflow
✓ Show you how to increase patient satisfaction and retention
✓ Demonstrate ROI on practice efficiency improvements

Most practices see 25-35% improvement in administrative efficiency while maintaining their personal touch.

Would you be interested in a practice consultation?

Best regards,
{your_name}

P.S. The best practice automation feels invisible to patients but makes your day much easier."""
            },
            
            # Legal Small/Basic Business
            'Legal_small_basic_introduction': {
                'subject_lines': [
                    "Quick question about {company_name}'s client management",
                    "Attorney {contact_name} - automate your practice?",
                    "From manual to professional: law practice automation"
                ],
                'email_body': """Dear Attorney {contact_name},

Hope your practice is going well! I noticed {company_name} and wanted to ask about your current client management system.

{ai_pain_point_reference}

Are you still handling client intake, follow-ups, and case tracking manually? Or using basic systems that require a lot of manual work?

Here's what I'm thinking: Let's set up your practice with automated client management - professional intake processes, automated follow-ups, case tracking, and client communication systems.

{setup_time} and you're operating like a much larger firm while maintaining your personal client relationships.

Worth upgrading your practice systems?

Best,
{your_name}

P.S. Going from "hoping you don't miss client follow-ups" to "automated professional communication" typically increases client satisfaction significantly."""
            },
            
            # Dental Enterprise
            'Dental_enterprise_introduction': {
                'subject_lines': [
                    "Enterprise dental practice automation for {company_name}",
                    "Dr. {contact_name} - comprehensive practice automation strategy",
                    "Scale {company_name} with enterprise practice automation"
                ],
                'email_body': """Dear Dr. {contact_name},

As {company_name} has grown into a significant practice, I imagine you're looking for ways to scale operations while maintaining the quality patient care that made you successful.

{ai_pain_point_reference}

I work with enterprise dental practices to implement comprehensive automation systems that integrate seamlessly with existing practice management while dramatically improving efficiency and patient satisfaction.

{setup_time} to discuss:
✓ Current practice system assessment and integration opportunities
✓ Enterprise-level automation recommendations for multi-location practices
✓ ROI projections and implementation timeline
✓ Custom solution design for your specific practice needs

I can show you exactly how similar practices have achieved 40-60% efficiency gains while actually improving patient relationships and satisfaction scores.

Would you be interested in a strategic practice consultation?

Best regards,
{your_name}

P.S. Enterprise practice automation enhances your professional service delivery rather than replacing the personal touch that makes you successful."""
            },
            
            # Legal Enterprise
            'Legal_enterprise_introduction': {
                'subject_lines': [
                    "Enterprise law practice automation for {company_name}",
                    "Attorney {contact_name} - comprehensive practice automation strategy",
                    "Scale {company_name} with enterprise legal automation"
                ],
                'email_body': """Dear Attorney {contact_name},

As {company_name} has grown into a significant legal practice, I imagine you're looking for ways to scale operations while maintaining the high-quality client service that defines your success.

{ai_pain_point_reference}

I work with enterprise law firms to implement comprehensive automation systems that integrate with existing case management while dramatically improving efficiency and client satisfaction.

{setup_time} to discuss:
✓ Current practice system assessment and integration opportunities
✓ Enterprise-level automation recommendations for multi-location firms
✓ ROI projections and implementation timeline
✓ Custom solution design for your specific practice areas

I can show you exactly how similar firms have achieved 40-60% efficiency gains while actually improving client relationships and satisfaction scores.

Would you be interested in a strategic practice consultation?

Best regards,
{your_name}

P.S. Enterprise legal automation enhances your professional service delivery rather than replacing the client relationships that make you successful."""
            },
            
            # Legal Established Business  
            'Legal_established_introduction': {
                'subject_lines': [
                    "Law practice automation for established attorneys",
                    "Attorney {contact_name} - streamline {company_name} operations",
                    "Professional practice automation consultation"
                ],
                'email_body': """Dear Attorney {contact_name},

I can see {company_name} is an established law practice with a solid client base.

{ai_pain_point_reference}

I work with established legal practices to implement professional automation systems that increase efficiency while maintaining the high-touch client service that makes you successful.

{setup_time} where I'll:
✓ Assess your current case management and client systems
✓ Recommend automation that fits your practice areas
✓ Show you how to improve client communication and satisfaction
✓ Demonstrate efficiency gains and ROI projections

Most practices achieve 30-40% improvement in administrative efficiency while actually improving client relationships.

Would you be interested in a practice consultation?

Best regards,
{your_name}

P.S. The best legal practice automation enhances your professional service rather than replacing it."""
            }
        }

# Global consultant approach instance
consultant_approach = ConsultantApproach()