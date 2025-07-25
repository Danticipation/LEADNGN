"""
AI Provider Manager for LeadNgN
Supports both OpenAI and Local LLM (Ollama) with automatic fallback
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIProviderManager:
    """Manages multiple AI providers with intelligent fallback"""
    
    def __init__(self):
        self.use_local_ai = os.environ.get("USE_LOCAL_AI", "false").lower() == "true"
        self.openai_client = None
        self.ollama_available = False
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "llama2:13b")
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        
        self.initialize_providers()
    
    def initialize_providers(self):
        """Initialize available AI providers"""
        # Initialize OpenAI if API key is available
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                self.openai_client = OpenAI(api_key=openai_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"OpenAI initialization failed: {e}")
        
        # Check Ollama availability
        if self.use_local_ai:
            self.ollama_available = self.check_ollama_connection()
    
    def check_ollama_connection(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]
                
                if any(self.ollama_model in name for name in model_names):
                    logger.info(f"Ollama model {self.ollama_model} is available")
                    return True
                else:
                    logger.warning(f"Ollama model {self.ollama_model} not found. Available: {model_names}")
                    return False
            else:
                logger.warning(f"Ollama API returned status {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.info("Ollama not available - connection refused")
            return False
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return False
    
    def get_available_providers(self) -> List[str]:
        """Get list of available AI providers"""
        providers = []
        if self.openai_client:
            providers.append("openai")
        if self.ollama_available:
            providers.append("ollama")
        return providers
    
    def generate_analysis(self, prompt: str, task_type: str = "analysis") -> Dict[str, Any]:
        """Generate AI analysis using the best available provider"""
        if self.use_local_ai and self.ollama_available:
            return self.call_ollama_api(prompt, task_type)
        elif self.openai_client:
            return self.call_openai_api(prompt, task_type)
        else:
            return self.create_error_response("No AI providers available")
    
    def call_ollama_api(self, prompt: str, task_type: str = "analysis") -> Dict[str, Any]:
        """Call local Ollama API for text generation"""
        try:
            # Configure parameters based on task type
            if task_type == "analysis":
                system_prompt = "You are an expert business analyst. Provide detailed insights in JSON format."
                temperature = 0.3
            elif task_type == "outreach":
                system_prompt = "You are a professional sales copywriter. Create compelling, personalized outreach content in JSON format."
                temperature = 0.7
            else:
                system_prompt = "You are a helpful business assistant. Respond in JSON format."
                temperature = 0.5
            
            # Prepare the request
            payload = {
                "model": self.ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 1500 if task_type == "analysis" else 800
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "")
                
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.warning("Ollama returned non-JSON response, parsing manually")
                    return self.parse_non_json_response(content, task_type)
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return self.create_error_response(f"Ollama API error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error("Ollama API timeout")
            return self.create_error_response("AI analysis timeout")
        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            return self.create_error_response(f"Local AI error: {str(e)}")
    
    def call_openai_api(self, prompt: str, task_type: str = "analysis") -> Dict[str, Any]:
        """Call OpenAI API for text generation"""
        try:
            if task_type == "analysis":
                model = "gpt-4o"
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
            if content:
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return self.parse_non_json_response(content, task_type)
            else:
                return self.create_error_response("Empty response from OpenAI")
                
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return self.create_error_response(f"OpenAI error: {str(e)}")
    
    def parse_non_json_response(self, content: str, task_type: str) -> Dict[str, Any]:
        """Parse non-JSON response into structured format"""
        if task_type == "analysis":
            return {
                "business_intelligence": {
                    "overview": content[:300] + "..." if len(content) > 300 else content,
                    "pain_points": ["Manual analysis required - AI response format issue"],
                    "opportunities": ["Review and refine AI prompt structure"],
                    "industry_position": "Analysis incomplete",
                    "decision_makers": ["Contact directly for best results"],
                    "budget_indicators": "Requires manual assessment"
                },
                "engagement_strategy": {
                    "approach": "Direct outreach recommended",
                    "timing": "Immediate follow-up",
                    "key_messages": ["Focus on core value proposition"],
                    "objection_handling": ["Prepare for common industry objections"],
                    "follow_up_strategy": "Multi-touch sequence"
                },
                "lead_scoring": {
                    "interest_level": "medium",
                    "buying_readiness": "researching",
                    "authority_level": "unknown",
                    "fit_score": "fair"
                },
                "next_steps": ["Manual review recommended", "Verify contact information"],
                "provider_used": "local_ai_parsed"
            }
        elif task_type == "outreach":
            return {
                "subject_line": "Partnership Opportunity",
                "email_content": content[:500] + "..." if len(content) > 500 else content,
                "key_points": ["Manual personalization recommended"],
                "tone": "Professional",
                "follow_up_strategy": "Review and customize before sending",
                "personalization_elements": ["Add specific business details"],
                "provider_used": "local_ai_parsed"
            }
        else:
            return {
                "status": "partial_success",
                "content": content,
                "message": "AI response received but format requires manual review",
                "provider_used": "local_ai_parsed"
            }
    
    def create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create structured error response"""
        return {
            "error": True,
            "message": error_message,
            "business_intelligence": {
                "overview": "AI analysis temporarily unavailable",
                "pain_points": ["System connectivity issue"],
                "opportunities": ["Manual research recommended"],
                "industry_position": "Assessment pending",
                "decision_makers": ["Contact directly"],
                "budget_indicators": "Unknown"
            },
            "engagement_strategy": {
                "approach": "Direct contact",
                "timing": "Immediate",
                "key_messages": ["Focus on proven value"],
                "objection_handling": ["Prepare standard responses"],
                "follow_up_strategy": "Standard sequence"
            },
            "lead_scoring": {
                "interest_level": "unknown",
                "buying_readiness": "unknown",
                "authority_level": "unknown",
                "fit_score": "unknown"
            },
            "next_steps": ["Verify AI system status", "Manual analysis recommended"],
            "provider_used": "error_fallback"
        }
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all AI providers"""
        return {
            "use_local_ai": self.use_local_ai,
            "ollama_available": self.ollama_available,
            "ollama_model": self.ollama_model,
            "openai_available": self.openai_client is not None,
            "active_provider": "ollama" if (self.use_local_ai and self.ollama_available) else "openai",
            "available_providers": self.get_available_providers()
        }
    
    def switch_provider(self, provider: str) -> bool:
        """Switch between AI providers"""
        if provider == "ollama":
            if self.check_ollama_connection():
                self.use_local_ai = True
                self.ollama_available = True
                logger.info("Switched to Ollama provider")
                return True
            else:
                logger.error("Cannot switch to Ollama - not available")
                return False
        elif provider == "openai":
            if self.openai_client:
                self.use_local_ai = False
                logger.info("Switched to OpenAI provider")
                return True
            else:
                logger.error("Cannot switch to OpenAI - not configured")
                return False
        else:
            logger.error(f"Unknown provider: {provider}")
            return False
    
    def test_provider(self, provider: str) -> Dict[str, Any]:
        """Test specific AI provider"""
        test_prompt = """
        Analyze this test business: "TechCorp Solutions, a software consulting company in San Francisco."
        Respond with JSON containing: {"test": "success", "provider": "provider_name"}
        """
        
        if provider == "ollama":
            if not self.ollama_available:
                return {"test": "failed", "error": "Ollama not available"}
            return self.call_ollama_api(test_prompt, "test")
        elif provider == "openai":
            if not self.openai_client:
                return {"test": "failed", "error": "OpenAI not configured"}
            return self.call_openai_api(test_prompt, "test")
        else:
            return {"test": "failed", "error": "Unknown provider"}


# Global instance for use throughout the application
ai_provider = AIProviderManager()