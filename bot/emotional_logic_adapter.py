"""
EmotionalLogicAdapter adds sentiment analysis to bot responses.
"""

import logging
import random
from mirrorbot.logic import LogicAdapter
from mirrorbot.conversation import Statement

from bot.sentiment_analyzer import analyze_sentiment, add_emotional_style

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmotionalLogicAdapter(LogicAdapter):
    """
    A logic adapter that analyzes sentiment in user input and adjusts
    bot responses to reflect detected emotions.
    
    This adapter sits on top of other adapters to add emotional context.
    """
    
    def __init__(self, chatbot, **kwargs):
        super().__init__(chatbot, **kwargs)
        
        # Store reference to the chatbot
        self._chatbot = chatbot
        
        # Default confidence threshold
        self.confidence_threshold = kwargs.get('confidence_threshold', 0.5)
        
        # What percentage of the time to reflect user's emotions (0-1)
        self.emotion_reflection_rate = kwargs.get('emotion_reflection_rate', 0.8)
        
        # Store conversation id for tracking emotions across messages
        self.conversation_id = None
        
        # Remember recent emotions to create continuity
        self.recent_emotions = []
        self.max_recent_emotions = 5  # How many emotions to remember
        
    def process(self, statement, additional_response_selection_parameters=None):
        """
        Determine if the input statement has emotional content and
        modify the response accordingly.
        
        Args:
            statement: A statement to be processed.
            additional_response_selection_parameters: Parameters for response selection.
            
        Returns:
            Statement: A modified statement that reflects the detected emotion.
        """
        # Get conversation ID if provided
        if additional_response_selection_parameters:
            self.conversation_id = additional_response_selection_parameters.get('conversation_id')
            
        # Check for emotional content in the input
        emotion_data = analyze_sentiment(statement.text)
        
        # Update recent emotions list
        self.recent_emotions.append(emotion_data)
        if len(self.recent_emotions) > self.max_recent_emotions:
            self.recent_emotions.pop(0)
            
        # Get a normal response from the next adapter in chain
        response = self.get_response_from_other_adapters(statement, additional_response_selection_parameters)
        
        # If the response confidence is very low, don't modify
        if not response or response.confidence < 0.1:
            return response
            
        # Check if we should reflect the user's emotion (based on probability)
        if random.random() < self.emotion_reflection_rate:
            # Get the primary emotion from analysis
            primary_emotion = emotion_data['primary_emotion']
            intensity = emotion_data['intensity']
            
            # Only modify if emotion is strong enough and not neutral
            if primary_emotion != 'neutral' and intensity > 0.3:
                # Store the original response
                original_text = response.text
                
                # Apply emotional styling to the response
                response.text = add_emotional_style(original_text, primary_emotion, intensity)
                
                # Add emotions to response metadata
                if not hasattr(response, 'metadata'):
                    response.metadata = {}
                response.metadata['emotion'] = primary_emotion
                response.metadata['intensity'] = intensity
                
                logger.info(f"Modified response with {primary_emotion} emotion (intensity: {intensity:.2f})")
        
        return response
        
    def get_response_from_other_adapters(self, statement, additional_response_selection_parameters=None):
        """
        Get a response from the next adapter in the chain.
        
        Args:
            statement: The input statement.
            additional_response_selection_parameters: Any additional parameters.
            
        Returns:
            Statement: The response from the next adapter.
        """
        # Process statement with other adapters
        response_list = []
        
        if hasattr(self.chatbot, 'logic_adapters'):
            for adapter in self.chatbot.logic_adapters:
                # Skip the current adapter to avoid recursion
                if adapter == self:
                    continue
                
                # Get the response from the adapter
                adapter_response = adapter.process(statement, additional_response_selection_parameters)
                
                if adapter_response:
                    response_list.append(adapter_response)
        
        # Find the response with the highest confidence
        if response_list:
            best_response = max(response_list, key=lambda x: x.confidence)
            return best_response
            
        # If no valid responses, create a default
        default_response = Statement(text="I'm not sure how to respond to that.")
        default_response.confidence = 0.1
        return default_response
        
    def can_process(self, statement):
        """
        Determines whether the adapter can process the statement.
        This adapter can process any statement.
        """
        return True