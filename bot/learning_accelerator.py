"""
Learning Accelerator for MirrorBot.

This module provides functionality to accelerate the bot's learning progression
based on interaction frequency and engagement levels.
"""

import logging
from datetime import datetime, timedelta
from app import db
from models import Message, BotVocabulary, MemoryFact

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LearningAccelerator:
    """
    Manages accelerated learning progression for the bot.
    """
    
    # Learning stage thresholds (normally much higher, but accelerated for testing)
    STAGE_THRESHOLDS = {
        'infant': {
            'min_messages': 0,
            'min_vocabulary': 0,
            'min_facts': 0
        },
        'toddler': {
            'min_messages': 5,      # Normally 20
            'min_vocabulary': 10,   # Normally 50
            'min_facts': 2          # Normally 5
        },
        'child': {
            'min_messages': 15,     # Normally 100
            'min_vocabulary': 25,   # Normally 150
            'min_facts': 5          # Normally 15
        },
        'adolescent': {
            'min_messages': 30,     # Normally 300
            'min_vocabulary': 50,   # Normally 300
            'min_facts': 10         # Normally 30
        },
        'adult': {
            'min_messages': 50,     # Normally 500
            'min_vocabulary': 75,   # Normally 500
            'min_facts': 15         # Normally 50
        }
    }
    
    def __init__(self):
        """Initialize the learning accelerator."""
        pass
        
    def get_learning_stage(self, conversation_id):
        """
        Determine the current learning stage based on accumulated knowledge.
        
        Args:
            conversation_id (str): The conversation identifier
            
        Returns:
            str: The current learning stage
        """
        try:
            # Get conversation statistics
            stats = self._get_conversation_stats(conversation_id)
            
            # Determine stage based on thresholds
            for stage in ['adult', 'adolescent', 'child', 'toddler', 'infant']:
                thresholds = self.STAGE_THRESHOLDS[stage]
                
                if (stats['message_count'] >= thresholds['min_messages'] and
                    stats['vocabulary_count'] >= thresholds['min_vocabulary'] and
                    stats['facts_count'] >= thresholds['min_facts']):
                    
                    logger.info(f"Learning stage determined: {stage} "
                               f"(messages: {stats['message_count']}, "
                               f"vocab: {stats['vocabulary_count']}, "
                               f"facts: {stats['facts_count']})")
                    return stage
            
            return 'infant'  # Default fallback
            
        except Exception as e:
            logger.error(f"Error determining learning stage: {str(e)}")
            return 'infant'
    
    def _get_conversation_stats(self, conversation_id):
        """Get statistics for a conversation."""
        try:
            # Count user messages (bot learns from user input)
            message_count = Message.query.filter_by(
                conversation_id=conversation_id,
                sender='user'
            ).count()
            
            # Count unique vocabulary learned
            vocabulary_count = BotVocabulary.query.filter_by(
                conversation_id=conversation_id
            ).count()
            
            # Count memory facts learned
            facts_count = MemoryFact.query.filter_by(
                conversation_id=conversation_id
            ).count()
            
            return {
                'message_count': message_count,
                'vocabulary_count': vocabulary_count,
                'facts_count': facts_count
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation stats: {str(e)}")
            return {
                'message_count': 0,
                'vocabulary_count': 0,
                'facts_count': 0
            }
    
    def get_learning_progress(self, conversation_id):
        """
        Get detailed learning progress information.
        
        Args:
            conversation_id (str): The conversation identifier
            
        Returns:
            dict: Learning progress data
        """
        try:
            current_stage = self.get_learning_stage(conversation_id)
            stats = self._get_conversation_stats(conversation_id)
            
            # Calculate progress to next stage
            next_stage_progress = self._calculate_next_stage_progress(current_stage, stats)
            
            # Get stage capabilities
            capabilities = self._get_stage_capabilities(current_stage)
            
            return {
                'current_stage': current_stage,
                'stats': stats,
                'next_stage_progress': next_stage_progress,
                'capabilities': capabilities,
                'stage_description': self._get_stage_description(current_stage)
            }
            
        except Exception as e:
            logger.error(f"Error getting learning progress: {str(e)}")
            return {
                'current_stage': 'infant',
                'stats': {'message_count': 0, 'vocabulary_count': 0, 'facts_count': 0},
                'next_stage_progress': 0,
                'capabilities': [],
                'stage_description': 'Just starting to learn'
            }
    
    def _calculate_next_stage_progress(self, current_stage, stats):
        """Calculate progress percentage to the next learning stage."""
        stage_order = ['infant', 'toddler', 'child', 'adolescent', 'adult']
        
        if current_stage == 'adult':
            return 100  # Already at maximum stage
        
        current_index = stage_order.index(current_stage)
        next_stage = stage_order[current_index + 1]
        next_thresholds = self.STAGE_THRESHOLDS[next_stage]
        
        # Calculate progress for each metric
        message_progress = min(100, (stats['message_count'] / next_thresholds['min_messages']) * 100)
        vocab_progress = min(100, (stats['vocabulary_count'] / next_thresholds['min_vocabulary']) * 100)
        facts_progress = min(100, (stats['facts_count'] / next_thresholds['min_facts']) * 100)
        
        # Use the minimum progress (all requirements must be met)
        overall_progress = min(message_progress, vocab_progress, facts_progress)
        
        return round(overall_progress, 1)
    
    def _get_stage_capabilities(self, stage):
        """Get the capabilities available at each learning stage."""
        capabilities = {
            'infant': [
                'Basic repetition',
                'Simple word learning',
                'Emotion detection'
            ],
            'toddler': [
                'Short phrase mimicking',
                'Basic question recognition',
                'Simple fact storage',
                'Context awareness begins'
            ],
            'child': [
                'Question answering',
                'Topic tracking',
                'Memory recall',
                'Basic conversation flow'
            ],
            'adolescent': [
                'Complex question handling',
                'Conversation summarization',
                'Advanced context awareness',
                'Personality development'
            ],
            'adult': [
                'Sophisticated responses',
                'Deep conversation analysis',
                'Advanced memory integration',
                'Full personality expression'
            ]
        }
        
        return capabilities.get(stage, [])
    
    def _get_stage_description(self, stage):
        """Get a description of the current learning stage."""
        descriptions = {
            'infant': 'Just starting to learn - primarily repeats what you say',
            'toddler': 'Beginning to understand - can handle simple questions and remember basic facts',
            'child': 'Growing smarter - can answer questions and track conversation topics',
            'adolescent': 'Developing personality - sophisticated conversation and memory skills',
            'adult': 'Fully developed - advanced conversational AI with deep understanding'
        }
        
        return descriptions.get(stage, 'Learning and growing')
    
    def should_enable_feature(self, feature_name, conversation_id):
        """
        Check if a specific feature should be enabled based on learning stage.
        
        Args:
            feature_name (str): Name of the feature to check
            conversation_id (str): The conversation identifier
            
        Returns:
            bool: Whether the feature should be enabled
        """
        current_stage = self.get_learning_stage(conversation_id)
        
        feature_requirements = {
            'question_answering': ['toddler', 'child', 'adolescent', 'adult'],
            'context_awareness': ['child', 'adolescent', 'adult'],
            'conversation_summary': ['adolescent', 'adult'],
            'advanced_memory': ['adolescent', 'adult'],
            'personality_expression': ['child', 'adolescent', 'adult']
        }
        
        return current_stage in feature_requirements.get(feature_name, [])
    
    def get_response_style_for_stage(self, stage):
        """
        Get the appropriate response style for the current learning stage.
        
        Args:
            stage (str): The current learning stage
            
        Returns:
            dict: Response style configuration
        """
        styles = {
            'infant': {
                'repetition_chance': 0.8,
                'question_answering': False,
                'context_reference': False,
                'emotional_response': False,
                'complexity': 'minimal'
            },
            'toddler': {
                'repetition_chance': 0.6,
                'question_answering': True,
                'context_reference': False,
                'emotional_response': True,
                'complexity': 'simple'
            },
            'child': {
                'repetition_chance': 0.4,
                'question_answering': True,
                'context_reference': True,
                'emotional_response': True,
                'complexity': 'moderate'
            },
            'adolescent': {
                'repetition_chance': 0.2,
                'question_answering': True,
                'context_reference': True,
                'emotional_response': True,
                'complexity': 'advanced'
            },
            'adult': {
                'repetition_chance': 0.1,
                'question_answering': True,
                'context_reference': True,
                'emotional_response': True,
                'complexity': 'sophisticated'
            }
        }
        
        return styles.get(stage, styles['infant'])