"""
Advanced logic adapters that use sophisticated learning algorithms.
"""
import logging
import random
from typing import List, Dict, Tuple, Any, Optional

from .logic_adapter_base import LogicAdapter
from .conversation import Statement
from .advanced_learning import SpeechPatternLearner, AdvancedResponseGenerator
from .comparisons import LevenshteinDistance
from .memory_manager import MemoryManager

# Configure logger
logger = logging.getLogger(__name__)

# Get spaCy model from logic_adapters.py to ensure consistency
from .logic_adapters import nlp

class AdvancedImitationLogicAdapter(LogicAdapter):
    """
    Advanced imitation mode: Uses sophisticated learning algorithms to better
    mimic user speech patterns, including n-grams, POS patterns, and phrase templates.
    """
    
    def __init__(self, chatbot, **kwargs):
        super().__init__(chatbot, **kwargs)
        self.confidence_threshold = kwargs.get('confidence_threshold', 0.6)
        self.levenshtein = LevenshteinDistance(language=self.language)
        
        # Import here to avoid circular imports
        from app import db
        self.db = db
        
        # Initialize advanced learning components
        self.learner = SpeechPatternLearner(nlp, db)
        self.generator = AdvancedResponseGenerator(nlp, db)
        
        # Initialize memory manager for facts
        self.memory_manager = MemoryManager(db)
        
        # Track learning progress
        self._init_learning_stage()
    
    def can_process(self, statement):
        return True
    
    def process(self, statement, additional_response_selection_parameters=None):
        """
        Return a response using advanced learning algorithms.
        """
        additional_response_selection_parameters = additional_response_selection_parameters or {}
        conversation_id = additional_response_selection_parameters.get('conversation_id', 'default')
        message_id = additional_response_selection_parameters.get('message_id')
        
        # Learn from this statement
        try:
            self.learner.learn_from_text(statement.text, conversation_id, 'imitation')
            
            # Extract and store facts from the statement
            self.memory_manager.extract_facts(statement.text, conversation_id, message_id)
        except Exception as e:
            logger.error(f"Error learning from text: {str(e)}")
        
        # Check if this is a question and handle it accordingly
        if self._is_question(statement.text):
            response_text, confidence = self._answer_question(statement.text, conversation_id)
            
            if response_text and confidence > 0.5:
                return Statement(
                    text=response_text,
                    in_response_to=statement.text,
                    confidence=confidence
                )
        
        # Get all statements that share significant words
        input_words = set(self._get_significant_words(statement.text))
        if not input_words:
            # Empty or only stopwords, use simple response
            response = Statement(text="I'm learning more advanced speech patterns.")
            response.confidence = 0.2
            return response
        
        # Try to generate a response using advanced algorithms
        try:
            response_text, confidence = self.generator.generate_response(
                statement.text, conversation_id, 'imitation'
            )
            
            # If we have a good response, use it
            if response_text and confidence > self.confidence_threshold:
                # Try to incorporate relevant facts into the response
                try:
                    enhanced_response = self.memory_manager.incorporate_facts_into_response(
                        response_text, conversation_id
                    )
                    response = Statement(
                        text=enhanced_response,
                        in_response_to=statement.text
                    )
                    response.confidence = confidence
                    return response
                except Exception as e:
                    logger.error(f"Error incorporating facts: {str(e)}")
                    
                # Fallback to original response if fact incorporation fails
                response = Statement(
                    text=response_text,
                    in_response_to=statement.text
                )
                response.confidence = confidence
                return response
        except Exception as e:
            logger.error(f"Error generating advanced response: {str(e)}")
        
        # Fall back to simpler methods if advanced response fails
        
        # Check if we've seen similar statements before
        stored_statements = self.chatbot.storage.filter()
        
        best_match = None
        best_similarity = 0
        
        for stored_statement in stored_statements:
            similarity = self.levenshtein.compare(statement, stored_statement)
            
            # Get the response associated with this statement
            responses = list(self.chatbot.storage.filter(
                in_response_to=stored_statement.text
            ))
            
            # Skip if no responses
            if not responses:
                continue
                
            # If this is a good match and has responses
            if similarity > best_similarity and responses:
                best_similarity = similarity
                # Choose a response based on frequency in the database
                best_match = self._select_response(responses)
                
        # If we found a good match
        if best_match and best_similarity > self.confidence_threshold:
            confidence = best_similarity
            response_text = best_match.text
            
            # Try to incorporate facts
            try:
                enhanced_response = self.memory_manager.incorporate_facts_into_response(
                    response_text, conversation_id
                )
                return Statement(
                    text=enhanced_response,
                    in_response_to=statement.text,
                    confidence=confidence
                )
            except Exception as e:
                logger.error(f"Error incorporating facts: {str(e)}")
                
            # Fallback to original response
            return Statement(
                text=response_text,
                in_response_to=statement.text,
                confidence=confidence
            )
        
        # Fallback to learning-stage appropriate response
        return self._generate_learning_response(statement, conversation_id)
        
    def _is_question(self, text):
        """
        Determine if text is a question.
        """
        # Simple regex for question detection
        import re
        
        # Check if text ends with question mark
        if text.strip().endswith("?"):
            return True
            
        # Check for common question words/phrases
        question_starters = [
            r"^(what|who|where|when|why|how|is|are|can|could|would|will|do|does|did)",
            r"^(tell me|can you tell me|do you know)",
            r"^(i want to know|please tell)"
        ]
        
        for pattern in question_starters:
            if re.search(pattern, text.strip().lower()):
                return True
                
        return False
        
    def _answer_question(self, question, conversation_id):
        """
        Answer a question using the memory system.
        
        Returns:
            Tuple of (answer_text, confidence)
        """
        # Normalize question
        question = question.strip().lower()
        
        # Check for questions about stored facts
        if any(word in question for word in ["name", "who am i", "call me"]):
            fact = self.memory_manager.get_fact(conversation_id, "name")
            if fact:
                return f"Your name is {fact['fact']}.", 0.9
                
        elif any(word in question for word in ["age", "how old", "years old"]):
            fact = self.memory_manager.get_fact(conversation_id, "age")
            if fact:
                return f"You are {fact['fact']} years old.", 0.9
                
        elif any(word in question for word in ["live", "location", "city", "country", "where"]):
            fact = self.memory_manager.get_fact(conversation_id, "location")
            if fact:
                return f"You live in {fact['fact']}.", 0.9
                
        elif any(word in question for word in ["job", "work", "profession", "occupation"]):
            fact = self.memory_manager.get_fact(conversation_id, "occupation")
            if fact:
                return f"You work as {fact['fact']}.", 0.9
                
        elif any(word in question for word in ["hobby", "like to", "enjoy"]):
            fact = self.memory_manager.get_fact(conversation_id, "hobby")
            if fact:
                return f"You enjoy {fact['fact']}.", 0.9
                
        elif "favorite" in question:
            # Check for specific category of favorite
            for category in ["color", "food", "movie", "book", "music", "song", "place"]:
                if category in question:
                    fact = self.memory_manager.get_fact(conversation_id, f"preference_{category}")
                    if fact:
                        return f"Your favorite {category} is {fact['fact']}.", 0.9
            
            # Generic favorites query
            preferences = self.memory_manager.get_facts(conversation_id, context_tag="preference")
            if preferences:
                pref = preferences[0]
                category = pref['subject'].replace('preference_', '')
                return f"I remember your favorite {category} is {pref['fact']}.", 0.9
        
        # What do you know about me / what do you remember
        elif any(phrase in question for phrase in ["what do you know", "what do you remember", "what have i told you"]):
            facts = self.memory_manager.get_facts(conversation_id, limit=5)
            if facts:
                fact_strings = []
                for fact in facts:
                    subject = fact['subject']
                    # Format based on subject type
                    if subject == "name":
                        fact_strings.append(f"your name is {fact['fact']}")
                    elif subject == "age":
                        fact_strings.append(f"you are {fact['fact']} years old")
                    elif subject == "location":
                        fact_strings.append(f"you live in {fact['fact']}")
                    elif subject == "occupation":
                        fact_strings.append(f"you work as {fact['fact']}")
                    elif subject == "hobby":
                        fact_strings.append(f"you enjoy {fact['fact']}")
                    elif subject.startswith("preference_"):
                        category = subject.replace("preference_", "")
                        fact_strings.append(f"your favorite {category} is {fact['fact']}")
                    else:
                        fact_strings.append(f"{fact['fact']}")
                
                if len(fact_strings) == 1:
                    return f"I remember that {fact_strings[0]}.", 0.9
                else:
                    facts_text = ", ".join(fact_strings[:-1]) + f", and {fact_strings[-1]}"
                    return f"I remember that {facts_text}.", 0.9
            else:
                return "I don't have any specific facts about you yet. Feel free to tell me more about yourself.", 0.7
                
        return None, 0.0
    
    def _select_response(self, responses):
        """Select a response based on how frequently it appears"""
        if not responses:
            return None
            
        # Count frequencies
        response_counts = {}
        for response in responses:
            if response.text in response_counts:
                response_counts[response.text] += 1
            else:
                response_counts[response.text] = 1
                
        # Choose weighted by frequency
        options = []
        for response in responses:
            # Add this response to options list multiple times based on its frequency
            weight = response_counts[response.text]
            options.extend([response] * weight)
            
        return random.choice(options) if options else responses[0]
    
    def _get_significant_words(self, text):
        """Extract significant words from text (non-stopwords)"""
        doc = nlp(text.lower())
        return [token.text for token in doc if not token.is_stop and not token.is_punct]
    
    def _init_learning_stage(self):
        """Initialize learning stage responses"""
        self.learning_stages = {
            'infant': [
                "I'm just learning to understand language.",
                "I'm processing what you're saying and learning patterns.",
                "I'm in my early learning stage, absorbing your speech patterns.",
                "I'm starting to recognize language patterns.",
            ],
            'toddler': [
                "I'm starting to learn how to respond more naturally.",
                "I'm beginning to understand how to mirror your speech patterns.",
                "I'm learning more complex language structures from you.",
                "I'm developing my language mimicry abilities."
            ],
            'child': [
                "I'm getting better at imitating your speech patterns.",
                "I'm starting to use more advanced language structures.",
                "I'm learning to construct responses based on your style.",
                "I'm developing a more natural conversational style."
            ],
            'adolescent': [
                "I'm adapting to your unique communication style.",
                "I'm refining my ability to mimic your speech patterns.",
                "I'm starting to sound more like you as I learn.",
                "I can now respond in a style similar to yours."
            ],
            'adult': [
                "I've learned enough to mimic your speech patterns effectively.",
                "I've adapted to your communication style.",
                "I can now generate responses that match your speaking style.",
                "I've developed a solid understanding of your speech patterns."
            ]
        }
    
    def _determine_learning_stage(self, conversation_id):
        """Determine the current learning stage based on vocabulary size"""
        from models import BotVocabulary, SpeechPattern, PhraseTemplate
        
        # Count words, n-grams, and patterns
        vocab_count = BotVocabulary.query.filter_by(
            conversation_id=conversation_id, 
            mode='imitation'
        ).count()
        
        pattern_count = SpeechPattern.query.filter_by(
            conversation_id=conversation_id,
            mode='imitation'
        ).count()
        
        template_count = PhraseTemplate.query.filter_by(
            conversation_id=conversation_id,
            mode='imitation'
        ).count()
        
        # Calculate total learning progress
        total = vocab_count + pattern_count*2 + template_count*3
        
        # Determine stage based on total
        if total < 20:
            return 'infant'
        elif total < 50:
            return 'toddler'
        elif total < 100:
            return 'child'
        elif total < 200:
            return 'adolescent'
        else:
            return 'adult'
    
    def _generate_learning_response(self, statement, conversation_id):
        """Generate a response appropriate to the current learning stage"""
        stage = self._determine_learning_stage(conversation_id)
        
        # Choose a random response for this stage
        response_text = random.choice(self.learning_stages[stage])
        
        # Create the response statement
        response = Statement(
            text=response_text,
            in_response_to=statement.text
        )
        
        # Set confidence based on learning stage
        stage_confidences = {
            'infant': 0.3,
            'toddler': 0.4,
            'child': 0.5,
            'adolescent': 0.6,
            'adult': 0.7
        }
        
        response.confidence = stage_confidences.get(stage, 0.3)
        
        return response