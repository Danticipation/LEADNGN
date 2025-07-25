"""
Phone and Voice Lead Integration for LeadNgN
Supports Twilio, webhook integrations, and voice-first lead management
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

logger = logging.getLogger(__name__)

class PhoneLeadManager:
    """Manages phone-based lead interactions and voice campaigns"""
    
    def __init__(self):
        self.twilio_client = None
        self.setup_twilio()
        
    def setup_twilio(self):
        """Initialize Twilio client if credentials are available"""
        try:
            account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
            auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
            
            if account_sid and auth_token:
                self.twilio_client = Client(account_sid, auth_token)
                logger.info("Twilio client initialized successfully")
            else:
                logger.info("Twilio credentials not found - voice features disabled")
        except Exception as e:
            logger.error(f"Twilio initialization failed: {e}")
    
    def validate_phone_number(self, phone: str) -> Dict[str, Any]:
        """Validate and format phone number"""
        result = {
            "original": phone,
            "formatted": None,
            "is_valid": False,
            "is_mobile": False,
            "carrier": None,
            "location": None,
            "call_priority": "low"
        }
        
        if not phone:
            return result
        
        # Clean and format phone number
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Add US country code if missing
        if len(cleaned) == 10:
            cleaned = "+1" + cleaned
        elif len(cleaned) == 11 and cleaned.startswith("1"):
            cleaned = "+" + cleaned
        
        result["formatted"] = cleaned
        
        # Basic validation
        if re.match(r'^\+1[0-9]{10}$', cleaned):
            result["is_valid"] = True
        
        # Use Twilio lookup if available
        if self.twilio_client and result["is_valid"]:
            try:
                lookup = self.twilio_client.lookups.phone_numbers(cleaned).fetch(
                    type=['carrier', 'caller-name']
                )
                result["carrier"] = lookup.carrier.get('name') if lookup.carrier else None
                result["is_mobile"] = lookup.carrier.get('type') == 'mobile' if lookup.carrier else False
                result["location"] = lookup.country_code
                
                # Set call priority based on phone type
                if result["is_mobile"]:
                    result["call_priority"] = "high"
                elif result["carrier"]:
                    result["call_priority"] = "medium"
                    
            except TwilioException as e:
                logger.warning(f"Twilio lookup failed for {cleaned}: {e}")
        
        return result
    
    def identify_call_ready_leads(self, leads: List[Any]) -> Dict[str, Any]:
        """Identify leads that are best contacted by phone"""
        call_ready = {
            "high_priority": [],
            "medium_priority": [],
            "low_priority": [],
            "no_phone": [],
            "total_analyzed": len(leads)
        }
        
        for lead in leads:
            if not lead.phone:
                call_ready["no_phone"].append({
                    "lead_id": lead.id,
                    "company": lead.company_name,
                    "reason": "No phone number available"
                })
                continue
            
            phone_info = self.validate_phone_number(lead.phone)
            
            # Determine call priority
            priority_score = 0
            reasons = []
            
            # Industry factors (HVAC, plumbing, dental typically phone-first)
            phone_first_industries = ["HVAC", "Plumbing", "Dental", "Emergency Services", "Medical"]
            if any(industry.lower() in (lead.industry or "").lower() for industry in phone_first_industries):
                priority_score += 30
                reasons.append("Phone-first industry")
            
            # Phone quality
            if phone_info["is_mobile"]:
                priority_score += 25
                reasons.append("Mobile number (direct contact)")
            elif phone_info["is_valid"]:
                priority_score += 15
                reasons.append("Valid business line")
            
            # Email quality (inverse relationship)
            if not lead.email or "@" not in (lead.email or ""):
                priority_score += 20
                reasons.append("No valid email - phone preferred")
            
            # Business characteristics
            if lead.company_size in ["Small", "Local"]:
                priority_score += 15
                reasons.append("Small business (personal touch preferred)")
            
            # Quality score
            if lead.quality_score >= 80:
                priority_score += 10
                reasons.append("High-quality lead")
            
            lead_data = {
                "lead_id": lead.id,
                "company": lead.company_name,
                "contact": lead.contact_name,
                "phone": phone_info["formatted"],
                "industry": lead.industry,
                "priority_score": priority_score,
                "reasons": reasons,
                "best_call_times": self.suggest_call_times(lead.industry, lead.location),
                "phone_info": phone_info
            }
            
            if priority_score >= 60:
                call_ready["high_priority"].append(lead_data)
            elif priority_score >= 30:
                call_ready["medium_priority"].append(lead_data)
            else:
                call_ready["low_priority"].append(lead_data)
        
        return call_ready
    
    def suggest_call_times(self, industry: str, location: str) -> List[Dict[str, str]]:
        """Suggest optimal call times based on industry and location"""
        times = []
        
        industry_schedules = {
            "HVAC": [
                {"time": "8:00 AM - 10:00 AM", "reason": "Pre-job planning time"},
                {"time": "4:00 PM - 6:00 PM", "reason": "End of service day"}
            ],
            "Dental": [
                {"time": "10:00 AM - 12:00 PM", "reason": "Between morning appointments"},
                {"time": "2:00 PM - 4:00 PM", "reason": "Administrative time"}
            ],
            "Legal": [
                {"time": "9:00 AM - 11:00 AM", "reason": "Morning availability"},
                {"time": "2:00 PM - 5:00 PM", "reason": "Afternoon client time"}
            ],
            "Medical": [
                {"time": "12:00 PM - 1:00 PM", "reason": "Lunch break"},
                {"time": "5:00 PM - 6:00 PM", "reason": "End of patient hours"}
            ]
        }
        
        if industry in industry_schedules:
            times = industry_schedules[industry]
        else:
            times = [
                {"time": "9:00 AM - 11:00 AM", "reason": "Morning business hours"},
                {"time": "2:00 PM - 4:00 PM", "reason": "Afternoon availability"}
            ]
        
        return times
    
    def create_call_script(self, lead: Any, campaign_type: str = "introduction") -> Dict[str, Any]:
        """Generate call script based on lead information"""
        script = {
            "lead_id": lead.id,
            "company": lead.company_name,
            "contact": lead.contact_name or "decision maker",
            "campaign_type": campaign_type,
            "script_sections": {}
        }
        
        # Opening
        script["script_sections"]["opening"] = f"""
Hi, this is [YOUR NAME] from [YOUR COMPANY]. 
I'm calling for {script['contact']} at {script['company']}.
Is this a good time for a quick conversation?
"""
        
        # Value proposition based on industry
        industry_value_props = {
            "HVAC": "help HVAC companies increase their service efficiency and customer satisfaction",
            "Dental": "help dental practices improve patient acquisition and retention",
            "Legal": "help law firms streamline their client management and case workflows",
            "Medical": "help medical practices optimize their patient experience and operations"
        }
        
        value_prop = industry_value_props.get(
            lead.industry, 
            "help businesses like yours improve efficiency and growth"
        )
        
        script["script_sections"]["value_proposition"] = f"""
The reason I'm calling is that we {value_prop}.
I noticed {script['company']} is {lead.industry or 'in your industry'} 
and thought there might be a good fit for what we do.
"""
        
        # Discovery questions
        industry_questions = {
            "HVAC": [
                "How are you currently managing your service scheduling?",
                "What's your biggest challenge during peak seasons?",
                "How do you handle emergency service calls?"
            ],
            "Dental": [
                "How do you currently attract new patients?",
                "What's your biggest challenge with patient retention?",
                "How do you manage appointment scheduling?"
            ],
            "Legal": [
                "How do you currently manage your case workflows?",
                "What's your biggest challenge with client communication?",
                "How do you handle new client intake?"
            ]
        }
        
        questions = industry_questions.get(lead.industry, [
            "What's your biggest operational challenge right now?",
            "How do you currently handle [relevant process]?",
            "What would ideal growth look like for your business?"
        ])
        
        script["script_sections"]["discovery"] = questions
        
        # Call to action
        script["script_sections"]["close"] = """
Based on what you've shared, I think there could be real value in exploring this further.
Would you be open to a brief 15-minute call next week where I can show you 
specifically how this could work for [COMPANY NAME]?
"""
        
        # Objection handling
        script["script_sections"]["objections"] = {
            "not_interested": "I understand. Can I ask what you're currently doing to address [pain point]?",
            "too_busy": "I completely understand you're busy. That's exactly why this could be valuable - it's designed to save you time.",
            "already_have_solution": "That's great that you have something in place. How well is it working for [specific challenge]?",
            "call_back_later": "Of course. When would be a better time? I can call you back at exactly [TIME]."
        }
        
        return script
    
    def initiate_voice_campaign(self, leads: List[Any], campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate automated voice campaign"""
        if not self.twilio_client:
            return {"error": "Twilio not configured for voice campaigns"}
        
        campaign = {
            "campaign_id": f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "total_leads": len(leads),
            "calls_initiated": 0,
            "calls_successful": 0,
            "calls_failed": 0,
            "results": []
        }
        
        twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
        if not twilio_phone:
            return {"error": "Twilio phone number not configured"}
        
        for lead in leads:
            if not lead.phone:
                continue
                
            try:
                # Create call with TwiML
                call = self.twilio_client.calls.create(
                    twiml=self.generate_voice_twiml(lead, campaign_config),
                    to=lead.phone,
                    from_=twilio_phone
                )
                
                campaign["calls_initiated"] += 1
                campaign["results"].append({
                    "lead_id": lead.id,
                    "call_sid": call.sid,
                    "status": "initiated",
                    "phone": lead.phone
                })
                
            except TwilioException as e:
                campaign["calls_failed"] += 1
                campaign["results"].append({
                    "lead_id": lead.id,
                    "error": str(e),
                    "status": "failed",
                    "phone": lead.phone
                })
        
        return campaign
    
    def generate_voice_twiml(self, lead: Any, config: Dict[str, Any]) -> str:
        """Generate TwiML for voice calls"""
        message = config.get("message", f"""
Hello, this is a message for {lead.contact_name or 'the business owner'} at {lead.company_name}.
We help {lead.industry or 'businesses like yours'} improve their operations and growth.
Please call us back at {config.get('callback_number', 'the number that just called')} 
to learn more about how we can help.
Thank you.
""")
        
        twiml = f"""
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">{message}</Say>
    <Record timeout="30" transcribe="true" transcribeCallback="{config.get('webhook_url', '')}" />
</Response>
"""
        return twiml
    
    def process_call_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming call webhook data"""
        return {
            "call_sid": webhook_data.get("CallSid"),
            "call_status": webhook_data.get("CallStatus"),
            "call_duration": webhook_data.get("CallDuration"),
            "recording_url": webhook_data.get("RecordingUrl"),
            "transcription": webhook_data.get("TranscriptionText"),
            "from_number": webhook_data.get("From"),
            "to_number": webhook_data.get("To"),
            "processed_at": datetime.now().isoformat()
        }
    
    def analyze_call_transcription(self, transcription: str) -> Dict[str, Any]:
        """Analyze call transcription for lead qualification"""
        analysis = {
            "transcription": transcription,
            "sentiment": "neutral",
            "interest_level": "unknown",
            "next_action": "follow_up",
            "key_phrases": [],
            "objections": [],
            "opportunities": []
        }
        
        if not transcription:
            return analysis
        
        text_lower = transcription.lower()
        
        # Interest indicators
        positive_phrases = ["interested", "tell me more", "sounds good", "when can", "how much"]
        negative_phrases = ["not interested", "don't need", "already have", "too busy", "call back"]
        
        for phrase in positive_phrases:
            if phrase in text_lower:
                analysis["key_phrases"].append(phrase)
                analysis["interest_level"] = "high"
                analysis["sentiment"] = "positive"
        
        for phrase in negative_phrases:
            if phrase in text_lower:
                analysis["objections"].append(phrase)
                if analysis["interest_level"] == "unknown":
                    analysis["interest_level"] = "low"
                    analysis["sentiment"] = "negative"
        
        # Determine next action
        if analysis["interest_level"] == "high":
            analysis["next_action"] = "schedule_demo"
        elif analysis["interest_level"] == "low":
            analysis["next_action"] = "nurture_sequence"
        else:
            analysis["next_action"] = "follow_up_call"
        
        return analysis
    
    def generate_sms_followup(self, lead: Any, call_result: Dict[str, Any]) -> Dict[str, str]:
        """Generate SMS follow-up message based on call result"""
        if not self.twilio_client:
            return {"error": "SMS not available - Twilio not configured"}
        
        contact_name = lead.contact_name or "there"
        company = lead.company_name
        
        # Customize message based on call outcome
        if call_result.get("interest_level") == "high":
            message = f"Hi {contact_name}, thanks for your interest during our call about {company}. I'll send over the information we discussed. When works best for a follow-up this week?"
        elif call_result.get("interest_level") == "low":
            message = f"Hi {contact_name}, I understand the timing might not be right for {company}. I'll check back in a few months. Feel free to reach out if anything changes."
        else:
            message = f"Hi {contact_name}, I tried calling {company} today about ways to improve your {lead.industry or 'business'} operations. When's a good time to connect briefly?"
        
        return {
            "message": message,
            "to_number": lead.phone,
            "lead_id": lead.id
        }
    
    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send SMS message via Twilio"""
        if not self.twilio_client:
            return {"success": False, "error": "Twilio not configured"}
        
        try:
            twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
            if not twilio_phone:
                return {"success": False, "error": "Twilio phone number not configured"}
            
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=twilio_phone,
                to=to_number
            )
            
            return {
                "success": True,
                "message_sid": message_obj.sid,
                "status": message_obj.status
            }
            
        except TwilioException as e:
            return {"success": False, "error": str(e)}
    
    def get_call_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get call campaign analytics"""
        if not self.twilio_client:
            return {"error": "Analytics not available - Twilio not configured"}
        
        try:
            calls = self.twilio_client.calls.list(
                start_time_after=start_date,
                start_time_before=end_date
            )
            
            analytics = {
                "total_calls": len(calls),
                "completed_calls": 0,
                "answered_calls": 0,
                "voicemail_calls": 0,
                "failed_calls": 0,
                "average_duration": 0,
                "total_duration": 0
            }
            
            durations = []
            for call in calls:
                if call.status == "completed":
                    analytics["completed_calls"] += 1
                    if call.duration and int(call.duration) > 30:
                        analytics["answered_calls"] += 1
                        durations.append(int(call.duration))
                    else:
                        analytics["voicemail_calls"] += 1
                elif call.status in ["failed", "busy", "no-answer"]:
                    analytics["failed_calls"] += 1
            
            if durations:
                analytics["average_duration"] = sum(durations) / len(durations)
                analytics["total_duration"] = sum(durations)
            
            return analytics
            
        except TwilioException as e:
            return {"error": str(e)}


# Global instance
phone_manager = PhoneLeadManager()