"""
Industry-Specific Email Templates for LeadNgN
Smart templates that adapt to lead insights and seasonal factors
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from models import Lead, db

logger = logging.getLogger(__name__)

class EmailTemplateManager:
    """Manages industry-specific email templates with AI personalization"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.templates = self._initialize_templates()
    
    def generate_email(self, lead_id: int, template_type: str, ai_insights: Dict = None) -> Dict:
        """Generate personalized email for a lead"""
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                return {'error': 'Lead not found'}
            
            template = self._get_template(lead.industry, template_type)
            if not template:
                return {'error': f'Template not found for {lead.industry} - {template_type}'}
            
            # Personalize template with lead data and AI insights
            personalized_email = self._personalize_template(template, lead, ai_insights)
            
            return {
                'success': True,
                'lead_id': lead_id,
                'template_type': template_type,
                'industry': lead.industry,
                'email': personalized_email,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Email generation error for lead {lead_id}: {e}")
            return {'error': f'Email generation failed: {str(e)}'}
    
    def get_available_templates(self, industry: str) -> List[str]:
        """Get available template types for an industry"""
        return list(self.templates.get(industry, {}).keys())
    
    def _initialize_templates(self) -> Dict:
        """Initialize industry-specific email templates"""
        return {
            'HVAC': {
                'introduction': {
                    'subject': 'Optimize Your {company_name} HVAC Operations - {seasonal_hook}',
                    'body': '''Dear {contact_name},

I hope this email finds you well during this {current_season} season when HVAC demand is {seasonal_demand}.

I came across {company_name} and was impressed by your {company_strength}. As a {industry} business owner in {location}, you understand the challenges of {industry_pain_points}.

{value_proposition}

{seasonal_relevance}

I'd love to discuss how we can help {company_name} achieve:
• {benefit_1}
• {benefit_2}  
• {benefit_3}

Would you be available for a brief 15-minute call this week to explore how this could benefit your operations?

Best regards,
{sender_name}

P.S. {personalized_ps}''',
                    'tone': 'professional_friendly',
                    'seasonal_hooks': {
                        'summer': 'Peak Cooling Season Efficiency',
                        'winter': 'Heating System Optimization',
                        'spring': 'Maintenance Season Planning',
                        'fall': 'Winter Preparation Strategy'
                    }
                },
                'follow_up': {
                    'subject': 'Following up on {company_name} HVAC efficiency opportunity',
                    'body': '''Hi {contact_name},

I wanted to follow up on my previous email about optimizing {company_name}'s HVAC operations.

{follow_up_reason}

Based on your {company_size} operation in {location}, I believe there's significant potential for:
{specific_opportunity}

{urgency_factor}

I have a brief window this {preferred_day} or {alternative_day} for a quick call. Would either work for your schedule?

Looking forward to connecting,
{sender_name}''',
                    'tone': 'persistent_helpful'
                },
                'value_proposition': {
                    'subject': '{roi_focused_subject} - {company_name}',
                    'body': '''Hello {contact_name},

Every HVAC business owner I speak with shares the same challenges:
{pain_point_1}
{pain_point_2}
{pain_point_3}

Here's how successful HVAC companies like {company_name} are solving these:

{solution_showcase}

The results speak for themselves:
• {metric_1}
• {metric_2}
• {metric_3}

{social_proof}

I'd be happy to show you exactly how this would work for {company_name}. 

Can we schedule a brief call to discuss your specific situation?

{call_to_action}

Best,
{sender_name}''',
                    'tone': 'results_focused'
                }
            },
            'Dental': {
                'introduction': {
                    'subject': 'Grow {company_name} Patient Base - {seasonal_hook}',
                    'body': '''Dear Dr. {contact_name},

I hope you're having a successful {current_period} with your practice.

I noticed {company_name} serves the {location} community, and I was impressed by your commitment to {dental_focus}. 

{practice_compliment}

As a dental practice owner, you're likely facing challenges like:
• {dental_challenge_1}
• {dental_challenge_2}
• {dental_challenge_3}

{value_proposition}

{seasonal_relevance}

I'd love to discuss how we can help {company_name} achieve:
• {benefit_1}
• {benefit_2}
• {benefit_3}

Would you have 15 minutes this week for a brief conversation about growing your practice?

Best regards,
{sender_name}

P.S. {dental_ps}''',
                    'tone': 'respectful_professional',
                    'seasonal_hooks': {
                        'january': 'New Year, New Smiles Campaign',
                        'august': 'Back-to-School Dental Health',
                        'november': 'Holiday Smile Makeovers',
                        'year_round': 'Patient Growth Strategy'
                    }
                },
                'follow_up': {
                    'subject': 'Quick follow-up for Dr. {contact_name}',
                    'body': '''Hello Dr. {contact_name},

I wanted to follow up on my email about growing {company_name}'s patient base.

{dental_follow_up_reason}

I understand how busy dental practices can be, especially during {current_period}. That's exactly why the practices I work with see such strong results - we handle the marketing so you can focus on patient care.

{specific_dental_opportunity}

Would a brief call this {preferred_day} work for your schedule?

Best,
{sender_name}''',
                    'tone': 'understanding_professional'
                },
                'value_proposition': {
                    'subject': 'Increase Patient Revenue by {percentage}% - {company_name}',
                    'body': '''Dear Dr. {contact_name},

Most dental practices are missing out on significant revenue growth because they're not effectively reaching potential patients in their area.

Here's what I've seen work for dental practices in {location}:

{dental_success_story}

The practices that implement this strategy typically see:
• {dental_metric_1}
• {dental_metric_2}
• {dental_metric_3}

{dental_social_proof}

I'd be happy to share exactly how this would work for {company_name}.

Are you available for a brief call to discuss your practice growth goals?

{dental_cta}

Best regards,
{sender_name}''',
                    'tone': 'data_driven'
                }
            },
            'Legal': {
                'introduction': {
                    'subject': 'Grow {company_name} Client Base - {legal_specialization}',
                    'body': '''Dear {attorney_title} {contact_name},

I hope this email finds you well.

I came across {company_name} and was impressed by your expertise in {legal_focus}. Building a successful legal practice in {location} requires both exceptional legal skills and effective client acquisition.

{legal_compliment}

Many successful attorneys I work with initially struggled with:
• {legal_challenge_1}
• {legal_challenge_2}
• {legal_challenge_3}

{legal_value_proposition}

{seasonal_relevance}

I'd appreciate the opportunity to discuss how we can help {company_name}:
• {legal_benefit_1}
• {legal_benefit_2}
• {legal_benefit_3}

Would you be available for a brief 15-minute call this week?

Best regards,
{sender_name}

P.S. {legal_ps}''',
                    'tone': 'professional_formal',
                    'seasonal_hooks': {
                        'tax_season': 'Tax Season Legal Needs',
                        'year_end': 'Estate Planning Season',
                        'post_holiday': 'New Year Legal Matters',
                        'general': 'Legal Services Growth'
                    }
                },
                'follow_up': {
                    'subject': 'Following up - {company_name} growth opportunity',
                    'body': '''Dear {attorney_title} {contact_name},

I wanted to follow up on my previous email regarding client acquisition strategies for {company_name}.

{legal_follow_up_reason}

I understand the demands of legal practice, and that's precisely why the attorneys I work with value having a reliable system for attracting qualified clients.

{specific_legal_opportunity}

{legal_urgency}

Would you have time for a brief call this {preferred_day}?

Best regards,
{sender_name}''',
                    'tone': 'respectful_persistent'
                },
                'value_proposition': {
                    'subject': 'Increase Legal Client Acquisition - {practice_area}',
                    'body': '''Dear {attorney_title} {contact_name},

Successful legal practices don't just happen - they're built with intentional client acquisition strategies.

Here's what I've observed with law firms in {location}:

{legal_market_insight}

The law firms that implement strategic marketing see:
• {legal_metric_1}
• {legal_metric_2}
• {legal_metric_3}

{legal_case_study}

I'd be happy to discuss how this approach could work specifically for {company_name}'s {practice_area} practice.

{legal_cta}

Best regards,
{sender_name}''',
                    'tone': 'strategic_professional'
                }
            }
        }
    
    def _get_template(self, industry: str, template_type: str) -> Optional[Dict]:
        """Get specific template by industry and type"""
        return self.templates.get(industry, {}).get(template_type)
    
    def _personalize_template(self, template: Dict, lead: Lead, ai_insights: Dict = None) -> Dict:
        """Personalize template with lead data and AI insights"""
        try:
            # Extract lead information
            company_name = lead.company_name
            contact_name = lead.contact_name or 'there'
            location = lead.location
            industry = lead.industry
            
            # Get seasonal context
            seasonal_context = self._get_seasonal_context(industry)
            
            # Get AI-driven insights for personalization
            personalization_data = self._get_personalization_data(lead, ai_insights)
            
            # Personalize subject line
            subject = template['subject'].format(
                company_name=company_name,
                contact_name=contact_name,
                seasonal_hook=seasonal_context['hook'],
                **personalization_data
            )
            
            # Personalize body
            body = template['body'].format(
                company_name=company_name,
                contact_name=contact_name,
                location=location,
                industry=industry,
                current_season=seasonal_context['season'],
                seasonal_demand=seasonal_context['demand'],
                seasonal_relevance=seasonal_context['relevance'],
                **personalization_data
            )
            
            return {
                'subject': subject,
                'body': body,
                'tone': template['tone'],
                'personalization_score': self._calculate_personalization_score(ai_insights),
                'seasonal_relevance': seasonal_context['relevance_score']
            }
            
        except Exception as e:
            self.logger.error(f"Template personalization error: {e}")
            # Return basic template if personalization fails
            return {
                'subject': template['subject'],
                'body': template['body'],
                'tone': template['tone'],
                'personalization_score': 0.3,
                'error': 'Limited personalization available'
            }
    
    def _get_seasonal_context(self, industry: str) -> Dict:
        """Get seasonal context for industry"""
        current_month = datetime.now().month
        
        seasonal_data = {
            'HVAC': {
                (6, 7, 8): {
                    'season': 'summer',
                    'hook': 'Peak Cooling Season',
                    'demand': 'at its highest',
                    'relevance': 'With temperatures soaring, efficient cooling systems are critical for customer satisfaction.',
                    'relevance_score': 0.9
                },
                (12, 1, 2): {
                    'season': 'winter',
                    'hook': 'Heating System Peak',
                    'demand': 'critical',
                    'relevance': 'Winter heating demands require reliable HVAC systems to keep customers comfortable.',
                    'relevance_score': 0.9
                },
                (3, 4, 5): {
                    'season': 'spring',
                    'hook': 'Maintenance Season',
                    'demand': 'shifting to maintenance',
                    'relevance': 'Spring is the perfect time for preventive maintenance before summer cooling season.',
                    'relevance_score': 0.7
                }
            },
            'Dental': {
                (1, 2): {
                    'season': 'new year',
                    'hook': 'New Year Benefits',
                    'demand': 'high with fresh insurance benefits',
                    'relevance': 'January brings renewed insurance benefits, making it prime time for dental procedures.',
                    'relevance_score': 0.8
                },
                (8, 9): {
                    'season': 'back-to-school',
                    'hook': 'School Health Requirements',
                    'demand': 'increasing for checkups',
                    'relevance': 'Back-to-school season drives family dental checkup appointments.',
                    'relevance_score': 0.8
                }
            },
            'Legal': {
                (1, 2, 3, 4): {
                    'season': 'tax season',
                    'hook': 'Tax and Business Planning',
                    'demand': 'high for business and tax matters',
                    'relevance': 'Tax season creates urgency for business formation and tax planning legal services.',
                    'relevance_score': 0.8
                },
                (11, 12): {
                    'season': 'year-end',
                    'hook': 'Estate Planning Season',
                    'demand': 'focused on planning',
                    'relevance': 'Year-end drives estate planning and business structure decisions.',
                    'relevance_score': 0.7
                }
            }
        }
        
        # Find matching seasonal context
        industry_seasons = seasonal_data.get(industry, {})
        
        for months, context in industry_seasons.items():
            if current_month in months:
                return context
        
        # Default context
        return {
            'season': 'current period',
            'hook': 'Business Growth',
            'demand': 'steady',
            'relevance': 'Business growth opportunities are always worth exploring.',
            'relevance_score': 0.5
        }
    
    def _get_personalization_data(self, lead: Lead, ai_insights: Dict = None) -> Dict:
        """Get personalization data from lead and AI insights"""
        data = {
            'sender_name': 'Your Marketing Partner',
            'company_strength': 'local market presence',
            'company_size': 'established',
            'preferred_day': 'Tuesday',
            'alternative_day': 'Thursday'
        }
        
        # Industry-specific personalizations
        if lead.industry == 'HVAC':
            data.update({
                'industry_pain_points': 'seasonal demand fluctuations and customer acquisition challenges',
                'value_proposition': 'We help HVAC companies build consistent lead generation systems that work year-round.',
                'benefit_1': 'Predictable lead flow during off-seasons',
                'benefit_2': 'Higher-quality service call bookings',
                'benefit_3': 'Improved customer lifetime value',
                'personalized_ps': 'I have specific strategies that work particularly well for HVAC companies in your market.'
            })
        
        elif lead.industry == 'Dental':
            data.update({
                'dental_focus': 'comprehensive patient care',
                'practice_compliment': 'Your dedication to patient health clearly shows in your practice approach.',
                'dental_challenge_1': 'Attracting new patients consistently',
                'dental_challenge_2': 'Managing appointment scheduling efficiently',
                'dental_challenge_3': 'Increasing case acceptance rates',
                'value_proposition': 'We help dental practices build sustainable patient acquisition systems.',
                'benefit_1': 'Steady stream of new patient appointments',
                'benefit_2': 'Higher case acceptance rates',
                'benefit_3': 'Improved practice revenue predictability',
                'dental_ps': 'I work exclusively with dental practices and understand your unique challenges.'
            })
        
        elif lead.industry == 'Legal':
            data.update({
                'attorney_title': 'Attorney',
                'legal_focus': 'client advocacy',
                'legal_compliment': 'Your commitment to client service is evident in your practice approach.',
                'legal_challenge_1': 'Generating qualified client inquiries',
                'legal_challenge_2': 'Standing out in a competitive legal market',
                'legal_challenge_3': 'Building lasting client relationships',
                'legal_value_proposition': 'We help law firms develop strategic client acquisition systems.',
                'legal_benefit_1': 'Consistent qualified client inquiries',
                'legal_benefit_2': 'Enhanced professional reputation',
                'legal_benefit_3': 'Improved practice profitability',
                'legal_ps': 'I specialize in marketing strategies specifically designed for legal practices.'
            })
        
        # Integrate AI insights if available
        if ai_insights:
            insights = ai_insights.get('insights', {})
            company_analysis = insights.get('company_analysis', {})
            
            if company_analysis.get('strengths'):
                data['company_strength'] = company_analysis['strengths'][0].lower()
            
            if company_analysis.get('pain_points'):
                pain_points = company_analysis['pain_points'][:3]
                for i, pain_point in enumerate(pain_points, 1):
                    data[f'pain_point_{i}'] = pain_point
        
        return data
    
    def _calculate_personalization_score(self, ai_insights: Dict = None) -> float:
        """Calculate personalization score based on available data"""
        base_score = 0.6  # Base template personalization
        
        if ai_insights:
            insights = ai_insights.get('insights', {})
            if insights.get('company_analysis'):
                base_score += 0.2
            if insights.get('engagement_strategy'):
                base_score += 0.1
            if insights.get('lead_scoring_breakdown'):
                base_score += 0.1
        
        return min(1.0, base_score)

# Global email template manager instance
email_template_manager = EmailTemplateManager()