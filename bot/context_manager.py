"""
Context Manager for MirrorBot.

This module provides functionality for tracking conversation context,
remembering topics, and enabling intelligent question answering.
"""

import logging
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter

import spacy
from app import db
from models import Message, MemoryFact

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load SpaCy model for NLP processing
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("SpaCy model not found. Using blank model instead.")
    nlp = spacy.blank("en")

class ContextManager:
    """
    Manages conversation context, topic tracking, and question answering.
    """
    
    def __init__(self):
        """Initialize the context manager."""
        self.current_topics = []
        self.conversation_summary = {}
        
    def extract_topics_from_text(self, text):
        """
        Extract topics and key entities from text using NLP.
        
        Args:
            text (str): The text to analyze
            
        Returns:
            dict: Contains topics, entities, and keywords
        """
        if not text:
            return {'topics': [], 'entities': [], 'keywords': []}
            
        # Process with SpaCy
        doc = nlp(text.lower())
        
        # Extract named entities
        entities = []
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'EVENT', 'WORK_OF_ART', 'PRODUCT']:
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char
                })
        
        # Extract noun phrases as potential topics
        noun_phrases = []
        for chunk in doc.noun_chunks:
            # Filter out common pronouns and short phrases
            if len(chunk.text) > 2 and chunk.root.pos_ in ['NOUN', 'PROPN']:
                noun_phrases.append(chunk.text.strip())
        
        # Extract important keywords (nouns and proper nouns)
        keywords = []
        for token in doc:
            if (token.pos_ in ['NOUN', 'PROPN'] and 
                not token.is_stop and 
                not token.is_punct and 
                len(token.text) > 2):
                keywords.append(token.lemma_)
        
        # Combine and deduplicate topics
        all_topics = list(set(noun_phrases + [ent['text'] for ent in entities]))
        
        return {
            'topics': all_topics[:10],  # Limit to top 10 topics
            'entities': entities,
            'keywords': list(set(keywords))
        }
    
    def update_conversation_context(self, user_message, bot_response, conversation_id, mode):
        """
        Update the conversation context with new messages.
        
        Args:
            user_message (str): The user's message
            bot_response (str): The bot's response
            conversation_id (str): The conversation identifier
            mode (str): The current bot mode
        """
        try:
            # Extract context from user message
            user_context = self.extract_topics_from_text(user_message)
            
            # Store conversation context in the database as a memory fact
            if user_context['topics'] or user_context['entities']:
                context_data = {
                    'topics': user_context['topics'],
                    'entities': user_context['entities'],
                    'keywords': user_context['keywords'],
                    'message_text': user_message[:500],  # Store sample
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Create or update conversation context fact
                existing_context = MemoryFact.query.filter_by(
                    conversation_id=conversation_id,
                    subject='conversation_context'
                ).first()
                
                if existing_context:
                    # Merge new context with existing
                    existing_data = existing_context.get_metadata()
                    if 'contexts' not in existing_data:
                        existing_data['contexts'] = []
                    
                    existing_data['contexts'].append(context_data)
                    
                    # Keep only the last 20 contexts to prevent bloat
                    if len(existing_data['contexts']) > 20:
                        existing_data['contexts'] = existing_data['contexts'][-20:]
                    
                    existing_context.set_metadata(existing_data)
                    existing_context.updated_at = datetime.utcnow()
                    existing_context.mentioned_count += 1
                else:
                    # Create new context fact
                    context_fact = MemoryFact()
                    context_fact.conversation_id = conversation_id
                    context_fact.subject = 'conversation_context'
                    context_fact.fact = f"Conversation topics and context data"
                    context_fact.confidence = 0.8
                    context_fact.priority = 7
                    context_fact.set_context_tags(['context', 'topics', 'conversation'])
                    context_fact.set_metadata({'contexts': [context_data]})
                    
                    db.session.add(context_fact)
                
                db.session.commit()
                logger.info(f"Updated conversation context with {len(user_context['topics'])} topics")
                
        except Exception as e:
            logger.error(f"Error updating conversation context: {str(e)}")
            db.session.rollback()
    
    def get_conversation_context(self, conversation_id, recent_messages=10):
        """
        Get recent conversation context.
        
        Args:
            conversation_id (str): The conversation identifier
            recent_messages (int): Number of recent messages to analyze
            
        Returns:
            dict: Recent conversation context and topics
        """
        try:
            # Get conversation context from memory facts
            context_fact = MemoryFact.query.filter_by(
                conversation_id=conversation_id,
                subject='conversation_context'
            ).first()
            
            if context_fact:
                context_data = context_fact.get_metadata()
                recent_contexts = context_data.get('contexts', [])[-recent_messages:]
                
                # Aggregate topics and keywords
                all_topics = []
                all_keywords = []
                all_entities = []
                
                for context in recent_contexts:
                    all_topics.extend(context.get('topics', []))
                    all_keywords.extend(context.get('keywords', []))
                    all_entities.extend(context.get('entities', []))
                
                # Count frequency and get most common
                topic_counts = Counter(all_topics)
                keyword_counts = Counter(all_keywords)
                
                return {
                    'recent_topics': list(topic_counts.most_common(5)),
                    'recent_keywords': list(keyword_counts.most_common(10)),
                    'recent_entities': all_entities[-10:],  # Last 10 entities
                    'context_count': len(recent_contexts)
                }
            
            return {
                'recent_topics': [],
                'recent_keywords': [],
                'recent_entities': [],
                'context_count': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            return {
                'recent_topics': [],
                'recent_keywords': [],
                'recent_entities': [],
                'context_count': 0
            }
    
    def answer_question_from_context(self, question, conversation_id):
        """
        Try to answer a question using learned context and facts.
        
        Args:
            question (str): The question to answer
            conversation_id (str): The conversation identifier
            
        Returns:
            str: Answer to the question or None if can't answer
        """
        if not question:
            return None
            
        # Simple question patterns
        question_lower = question.lower().strip()
        
        # Check if it's a question about the user
        if any(word in question_lower for word in ['my', 'me', 'i', 'am i', 'do i']):
            return self._answer_personal_question(question_lower, conversation_id)
        
        # Check if it's a question about previous conversations
        if any(word in question_lower for word in ['said', 'talked', 'mentioned', 'discussed']):
            return self._answer_conversation_question(question_lower, conversation_id)
        
        # Check if it's a general fact question
        return self._answer_fact_question(question_lower, conversation_id)
    
    def _answer_personal_question(self, question, conversation_id):
        """Answer questions about the user's personal information."""
        try:
            # Get personal facts about the user
            personal_facts = MemoryFact.query.filter_by(
                conversation_id=conversation_id
            ).filter(
                MemoryFact.subject.in_(['name', 'location', 'occupation', 'hobby', 'age'])
            ).all()
            
            # Match question to facts
            if 'name' in question:
                name_fact = next((f for f in personal_facts if f.subject == 'name'), None)
                if name_fact:
                    return f"Your name is {name_fact.fact}."
            
            elif 'live' in question or 'from' in question:
                location_fact = next((f for f in personal_facts if f.subject == 'location'), None)
                if location_fact:
                    return f"You're from {location_fact.fact}."
            
            elif 'work' in question or 'job' in question:
                job_fact = next((f for f in personal_facts if f.subject == 'occupation'), None)
                if job_fact:
                    return f"You work as {job_fact.fact}."
            
            elif 'like' in question or 'enjoy' in question:
                hobby_facts = [f for f in personal_facts if f.subject == 'hobby']
                if hobby_facts:
                    hobbies = [f.fact for f in hobby_facts]
                    return f"You enjoy {', '.join(hobbies)}."
            
            return None
            
        except Exception as e:
            logger.error(f"Error answering personal question: {str(e)}")
            return None
    
    def _answer_conversation_question(self, question, conversation_id):
        """Answer questions about previous conversations."""
        try:
            # Get conversation context
            context = self.get_conversation_context(conversation_id, recent_messages=20)
            
            if 'topic' in question or 'about' in question:
                if context['recent_topics']:
                    topics = [topic[0] for topic in context['recent_topics'][:3]]
                    return f"We've been talking about {', '.join(topics)}."
            
            elif 'said' in question or 'mentioned' in question:
                if context['recent_keywords']:
                    keywords = [keyword[0] for keyword in context['recent_keywords'][:5]]
                    return f"You've mentioned things like {', '.join(keywords)}."
            
            return None
            
        except Exception as e:
            logger.error(f"Error answering conversation question: {str(e)}")
            return None
    
    def _answer_fact_question(self, question, conversation_id):
        """Answer general fact questions from stored memory."""
        try:
            # Get all memory facts
            facts = MemoryFact.query.filter_by(
                conversation_id=conversation_id
            ).filter(
                MemoryFact.confidence > 0.5
            ).order_by(
                MemoryFact.priority.desc()
            ).limit(20).all()
            
            # Simple keyword matching against facts
            question_keywords = set(re.findall(r'\w+', question.lower()))
            
            best_match = None
            best_score = 0
            
            for fact in facts:
                fact_keywords = set(re.findall(r'\w+', fact.fact.lower()))
                # Calculate overlap
                overlap = len(question_keywords.intersection(fact_keywords))
                if overlap > best_score:
                    best_score = overlap
                    best_match = fact
            
            if best_match and best_score > 0:
                return f"I remember that {best_match.fact}."
            
            return None
            
        except Exception as e:
            logger.error(f"Error answering fact question: {str(e)}")
            return None
    
    def summarize_conversation(self, conversation_id, messages_limit=50):
        """
        Generate a summary of the conversation.
        
        Args:
            conversation_id (str): The conversation identifier
            messages_limit (int): Number of recent messages to summarize
            
        Returns:
            dict: Conversation summary with key topics and insights
        """
        try:
            # Get recent messages
            messages = Message.query.filter_by(
                conversation_id=conversation_id
            ).order_by(
                Message.timestamp.desc()
            ).limit(messages_limit).all()
            
            if not messages:
                return {
                    'summary': 'No conversation history available.',
                    'key_topics': [],
                    'user_interests': [],
                    'conversation_length': 0
                }
            
            # Reverse to get chronological order
            messages = list(reversed(messages))
            
            # Extract topics from all messages
            all_text = ' '.join([msg.content for msg in messages if msg.sender == 'user'])
            context_data = self.extract_topics_from_text(all_text)
            
            # Get personal facts for user interests
            personal_facts = MemoryFact.query.filter_by(
                conversation_id=conversation_id
            ).filter(
                MemoryFact.subject.in_(['hobby', 'interest', 'preference_music', 'preference_food'])
            ).all()
            
            user_interests = [fact.fact for fact in personal_facts]
            
            # Count topics
            topic_counts = Counter(context_data['topics'])
            key_topics = [topic for topic, count in topic_counts.most_common(5)]
            
            # Generate summary text
            summary_parts = []
            
            if key_topics:
                summary_parts.append(f"Main topics discussed: {', '.join(key_topics[:3])}")
            
            if user_interests:
                summary_parts.append(f"User interests: {', '.join(user_interests[:3])}")
            
            user_message_count = len([m for m in messages if m.sender == 'user'])
            bot_message_count = len([m for m in messages if m.sender == 'bot'])
            
            summary_parts.append(f"Conversation included {user_message_count} user messages and {bot_message_count} bot responses")
            
            if not summary_parts:
                summary_text = "This was a brief conversation with limited topics discussed."
            else:
                summary_text = '. '.join(summary_parts) + '.'
            
            return {
                'summary': summary_text,
                'key_topics': key_topics,
                'user_interests': user_interests,
                'conversation_length': len(messages),
                'message_breakdown': {
                    'user_messages': user_message_count,
                    'bot_messages': bot_message_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error summarizing conversation: {str(e)}")
            return {
                'summary': 'Error generating conversation summary.',
                'key_topics': [],
                'user_interests': [],
                'conversation_length': 0
            }