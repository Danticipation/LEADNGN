"""
Memory management for the MirrorBot - handles storing and retrieving facts about the user.
"""
import logging
import re
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any, Union
import spacy

# Get the same spaCy model that the logic adapters use
from .logic_adapters import nlp

# Configure logger
logger = logging.getLogger(__name__)

# Common subjects for facts that we want to extract
COMMON_FACT_SUBJECTS = {
    'name': ['name', 'call me', 'i am', 'my name'],
    'age': ['age', 'years old', 'birthday', 'born'],
    'location': ['live in', 'living in', 'located in', 'from', 'city', 'state', 'country'],
    'occupation': ['work as', 'job', 'profession', 'occupation', 'career', 'employed', 'working as'],
    'hobby': ['hobby', 'hobbies', 'like to', 'enjoy', 'leisure', 'free time', 'passion'],
    'family': ['family', 'married', 'children', 'parents', 'siblings', 'spouse', 'daughter', 'son'],
    'pet': ['pet', 'dog', 'cat', 'animal', 'companion'],
    'education': ['school', 'college', 'university', 'study', 'studied', 'degree', 'education'],
    'preference': ['favorite', 'prefer', 'like', 'love', 'hate', 'dislike', 'enjoy'],
}

# Personal pronouns typically used when discussing oneself
PERSONAL_PRONOUNS = ['i', 'me', 'my', 'mine', 'myself']

class MemoryManager:
    """
    Manages memory and fact extraction for the bot.
    """
    
    def __init__(self, db):
        """
        Initialize the memory manager.
        
        Args:
            db: SQLAlchemy database connection
        """
        self.db = db
        
        # Import here to avoid circular imports
        from models import MemoryFact, Message
        self.MemoryFact = MemoryFact
        self.Message = Message
        
    def extract_facts(self, text: str, conversation_id: str, message_id: Optional[int] = None) -> List[Dict]:
        """
        Extract facts from a message.
        
        Args:
            text: The text to extract facts from
            conversation_id: The conversation ID
            message_id: The ID of the message (if available)
            
        Returns:
            List of extracted facts as dictionaries
        """
        extracted_facts = []
        
        # Skip very short texts
        if len(text.strip()) < 10:
            return extracted_facts
            
        # Parse the text with spaCy
        doc = nlp(text)
        
        # Try different extraction methods
        extracted_facts.extend(self._extract_direct_facts(doc, text))
        extracted_facts.extend(self._extract_self_disclosures(doc, text))
        
        # Store facts in database if any were extracted
        for fact in extracted_facts:
            self.store_fact(
                conversation_id=conversation_id,
                subject=fact['subject'],
                fact=fact['fact'],
                confidence=fact['confidence'],
                source_message_id=message_id,
                source_text=fact.get('source_text'),
                context_tags=fact.get('context_tags', ['general']),
                priority=fact.get('priority', 5),
            )
            
        return extracted_facts
    
    def _extract_direct_facts(self, doc, text: str) -> List[Dict]:
        """
        Extract facts that are directly stated.
        
        Args:
            doc: spaCy Doc object
            text: Original text
            
        Returns:
            List of extracted facts
        """
        facts = []
        
        # Look for common patterns like "I am X" or "My name is X" etc.
        common_patterns = [
            (r"(?:my name is|i am|i'm|call me) ([a-zA-Z]+)", "name"),
            (r"(?:i am|i'm) (\d+)(?: years old)?", "age"),
            (r"(?:i live in|i'm from|i am from|i live at) ([a-zA-Z\s,]+)", "location"),
            (r"(?:i work as|my job is|i'm a|i am a) ([a-zA-Z\s]+)", "occupation"),
            (r"(?:i enjoy|i like|my hobby is) ([a-zA-Z\s,]+)", "hobby"),
            (r"(?:my favorite|i love) ([a-zA-Z\s]+) (?:is|are) ([a-zA-Z\s]+)", "preference"),
        ]
        
        for pattern, subject in common_patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                if subject == "preference" and len(match.groups()) >= 2:
                    # Handle preference with category
                    category = match.group(1).strip()
                    preference = match.group(2).strip()
                    subject = f"preference_{category}"
                    fact_text = preference
                else:
                    fact_text = match.group(1).strip()
                
                facts.append({
                    'subject': subject,
                    'fact': fact_text,
                    'confidence': 0.8,
                    'source_text': match.group(0),
                    'context_tags': ['general', subject]
                })
        
        return facts
    
    def _extract_self_disclosures(self, doc, text: str) -> List[Dict]:
        """
        Extract facts based on self-disclosure statements.
        
        Args:
            doc: spaCy Doc object
            text: Original text
            
        Returns:
            List of extracted facts
        """
        facts = []
        
        # Look for sentences with personal pronouns
        personal_disclosure = False
        for token in doc:
            if token.text.lower() in PERSONAL_PRONOUNS:
                personal_disclosure = True
                break
        
        if not personal_disclosure:
            return facts
        
        # For each type of common fact, check if it's mentioned
        for subject, keywords in COMMON_FACT_SUBJECTS.items():
            for keyword in keywords:
                if keyword in text.lower():
                    # Find the sentence containing this keyword
                    for sent in doc.sents:
                        sent_text = sent.text.lower()
                        if keyword in sent_text and any(pronoun in sent_text for pronoun in PERSONAL_PRONOUNS):
                            # Extract the relevant part (very simplistic)
                            if subject == 'name':
                                # Try to extract name - look for proper nouns
                                names = [token.text for token in sent if token.pos_ == 'PROPN']
                                if names:
                                    facts.append({
                                        'subject': subject,
                                        'fact': ' '.join(names),
                                        'confidence': 0.7,
                                        'source_text': sent.text,
                                        'context_tags': ['general', 'personal', subject]
                                    })
                            else:
                                # For other subjects, just store the full sentence for now
                                # In a production system, this would use more sophisticated extraction
                                facts.append({
                                    'subject': subject,
                                    'fact': sent.text,
                                    'confidence': 0.6,
                                    'source_text': sent.text,
                                    'context_tags': ['general', subject]
                                })
                            break
        
        return facts
    
    def store_fact(self, conversation_id: str, subject: str, fact: str, confidence: float = 1.0,
                 source_message_id: Optional[int] = None, source_text: Optional[str] = None,
                 context_tags: Optional[List[str]] = None, priority: int = 5) -> bool:
        """
        Store a fact in the database.
        
        Args:
            conversation_id: The conversation ID
            subject: What the fact is about (e.g., "name", "occupation", "birthday")
            fact: The actual fact content
            confidence: How confident the bot is about this fact (0-1)
            source_message_id: Message ID where fact was learned
            source_text: Portion of the text containing the fact
            context_tags: List of contexts where this fact is relevant
            priority: Importance (1-10, with 10 being highest)
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Check if fact already exists
            existing = self.MemoryFact.query.filter_by(
                conversation_id=conversation_id,
                subject=subject
            ).first()
            
            if existing:
                # Update existing fact if new one has higher confidence or priority
                if confidence > existing.confidence or priority > existing.priority:
                    existing.fact = fact
                    existing.confidence = confidence
                    existing.priority = max(existing.priority, priority)
                    if source_message_id:
                        existing.source_message_id = source_message_id
                    if source_text:
                        existing.source_text = source_text
                
                # Always increment mention count
                existing.mentioned_count += 1
                existing.updated_at = datetime.utcnow()
                
                # Merge context tags
                existing_tags = existing.get_context_tags()
                if context_tags:
                    for tag in context_tags:
                        if tag not in existing_tags:
                            existing_tags.append(tag)
                    existing.set_context_tags(existing_tags)
            else:
                # Create new fact
                new_fact = self.MemoryFact()
                new_fact.conversation_id = conversation_id
                new_fact.subject = subject
                new_fact.fact = fact
                new_fact.confidence = confidence
                new_fact.source_message_id = source_message_id
                new_fact.source_text = source_text
                new_fact.priority = priority
                new_fact.set_context_tags(context_tags or ['general'])
                
                self.db.session.add(new_fact)
            
            self.db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error storing fact: {str(e)}")
            self.db.session.rollback()
            return False
    
    def get_facts(self, conversation_id: str, subject: Optional[str] = None,
                context_tag: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """
        Get facts from the database.
        
        Args:
            conversation_id: The conversation ID
            subject: Optional subject to filter by
            context_tag: Optional context tag to filter by
            limit: Maximum number of facts to return
            
        Returns:
            List of facts as dictionaries
        """
        try:
            query = self.MemoryFact.query.filter_by(conversation_id=conversation_id)
            
            if subject:
                query = query.filter_by(subject=subject)
                
            # Order by priority and mention count
            query = query.order_by(self.MemoryFact.priority.desc(), 
                                  self.MemoryFact.mentioned_count.desc())
            
            facts = query.limit(limit).all()
            
            # Filter by context tag if specified
            if context_tag:
                filtered_facts = []
                for fact in facts:
                    if context_tag in fact.get_context_tags():
                        filtered_facts.append(fact)
                facts = filtered_facts
            
            # Convert to dictionaries
            return [{
                'id': fact.id,
                'subject': fact.subject,
                'fact': fact.fact,
                'confidence': fact.confidence,
                'created_at': fact.created_at.isoformat() if fact.created_at else None,
                'updated_at': fact.updated_at.isoformat() if fact.updated_at else None,
                'mentioned_count': fact.mentioned_count,
                'priority': fact.priority,
                'context_tags': fact.get_context_tags()
            } for fact in facts]
            
        except Exception as e:
            logger.error(f"Error retrieving facts: {str(e)}")
            return []
    
    def get_fact(self, conversation_id: str, subject: str) -> Optional[Dict]:
        """
        Get a specific fact from the database.
        
        Args:
            conversation_id: The conversation ID
            subject: The subject to get
            
        Returns:
            Fact as dictionary or None if not found
        """
        facts = self.get_facts(conversation_id, subject=subject, limit=1)
        return facts[0] if facts else None
    
    def get_relevant_facts(self, text: str, conversation_id: str, limit: int = 3) -> List[Dict]:
        """
        Get facts that are relevant to the current message.
        
        Args:
            text: The text to find relevant facts for
            conversation_id: The conversation ID
            limit: Maximum number of facts to return
            
        Returns:
            List of relevant facts as dictionaries
        """
        # Get all facts for this conversation
        all_facts = self.get_facts(conversation_id, limit=50)
        
        if not all_facts:
            return []
            
        # Score facts by relevance to the current text
        scored_facts = []
        text_lower = text.lower()
        
        for fact in all_facts:
            score = 0
            
            # Check if the subject is mentioned
            if fact['subject'] in text_lower:
                score += 3
                
            # Check if any words from the fact are in the text
            fact_words = set(fact['fact'].lower().split())
            text_words = set(text_lower.split())
            common_words = fact_words.intersection(text_words)
            score += len(common_words)
            
            # Add points for high priority and frequently mentioned facts
            score += fact['priority'] * 0.5
            score += fact['mentioned_count'] * 0.2
            
            # Always assign at least a small score to ensure facts can be used
            if score == 0:
                score = 0.1 + (fact['priority'] / 10)
                
            scored_facts.append((score, fact))
        
        # Sort by score in descending order (highest scores first)
        scored_facts.sort(key=lambda x: x[0], reverse=True)
        
        # Return the facts (without scores)
        return [fact for score, fact in scored_facts[:limit]]
    
    def incorporate_facts_into_response(self, response_text: str, conversation_id: str) -> str:
        """
        Modify a response to incorporate relevant facts.
        
        Args:
            response_text: Original response text
            conversation_id: The conversation ID
            
        Returns:
            Modified response with incorporated facts
        """
        try:
            # Get relevant facts
            relevant_facts = self.get_relevant_facts(response_text, conversation_id, limit=2)
            
            if not relevant_facts:
                return response_text
                
            # Simple fact incorporation - just append a sentence
            # In a more sophisticated system, this would use more natural incorporation
            fact = relevant_facts[0]
            
            # Skip fact incorporation if confidence is missing or too low
            if 'confidence' not in fact or fact['confidence'] < 0.7:
                return response_text
                
            # Don't add facts if response is already long
            if len(response_text) > 100:
                return response_text
                
            # Don't repeat facts that are already in the response
            if fact['fact'].lower() in response_text.lower():
                return response_text
                
            if fact['subject'] == 'name':
                modified = f"{response_text} I remember your name is {fact['fact']}."
            elif fact['subject'] == 'location':
                modified = f"{response_text} You mentioned you're from {fact['fact']}."
            elif fact['subject'] == 'hobby':
                modified = f"{response_text} I recall you enjoy {fact['fact']}."
            elif fact['subject'] == 'occupation':
                modified = f"{response_text} You work as {fact['fact']}, right?"
            elif fact['subject'].startswith('preference_'):
                category = fact['subject'].replace('preference_', '')
                modified = f"{response_text} I remember your favorite {category} is {fact['fact']}."
            else:
                # Default case - generic incorporation
                modified = f"{response_text} I remember that {fact['fact']}."
                
            return modified
                
        except Exception as e:
            logger.error(f"Error in incorporate_facts_into_response: {str(e)}")
            # If anything goes wrong, just return the original response
            return response_text