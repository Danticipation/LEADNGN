"""
Emotion Manager for MirrorBot.

This module provides functionality for tracking, storing, and analyzing
user emotions over time.
"""

import logging
from datetime import datetime, timedelta
import json

from app import db
from models import EmotionTracker, Message
from bot.sentiment_analyzer import analyze_sentiment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmotionManager:
    """
    Manages the tracking and analysis of user emotions during conversations.
    """
    
    def __init__(self):
        """Initialize the emotion manager."""
        pass
        
    def track_emotion(self, message_text, conversation_id, message_id=None, mode="imitation"):
        """
        Analyze a message for emotional content and store the results.
        
        Args:
            message_text (str): The text of the message to analyze
            conversation_id (str): The conversation identifier
            message_id (int, optional): The ID of the message in the database
            mode (str, optional): The bot mode being used
            
        Returns:
            dict: The analyzed emotion data
        """
        if not message_text or not conversation_id:
            return None
            
        # Analyze the sentiment of the message
        emotion_data = analyze_sentiment(message_text)
        
        try:
            # Create new emotion tracker entry
            emotion = EmotionTracker()
            emotion.conversation_id = conversation_id
            emotion.message_id = message_id
            emotion.primary_emotion = emotion_data['primary_emotion']
            emotion.confidence = emotion_data['confidence']
            emotion.intensity = emotion_data['intensity']
            emotion.set_emotion_data(emotion_data['emotion_scores'])
            emotion.text_sample = message_text[:255]  # Store a sample of the text
            emotion.mode = mode
            
            # Save to database
            db.session.add(emotion)
            db.session.commit()
            
            logger.info(f"Tracked emotion: {emotion.primary_emotion} "
                       f"(confidence: {emotion.confidence:.2f}, intensity: {emotion.intensity:.2f})")
            
            return emotion_data
            
        except Exception as e:
            logger.error(f"Error tracking emotion: {str(e)}")
            db.session.rollback()
            return emotion_data
            
    def get_recent_emotions(self, conversation_id, limit=5):
        """
        Get the most recent emotions tracked for a conversation.
        
        Args:
            conversation_id (str): The conversation identifier
            limit (int, optional): Maximum number of emotions to return
            
        Returns:
            list: Recent emotion tracking data
        """
        try:
            emotions = EmotionTracker.query.filter_by(
                conversation_id=conversation_id
            ).order_by(
                EmotionTracker.created_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    'primary_emotion': e.primary_emotion,
                    'confidence': e.confidence,
                    'intensity': e.intensity,
                    'created_at': e.created_at.isoformat() if e.created_at else None,
                    'text_sample': e.text_sample,
                    'emotion_scores': e.get_emotion_data()
                }
                for e in emotions
            ]
        except Exception as e:
            logger.error(f"Error retrieving recent emotions: {str(e)}")
            return []
            
    def get_dominant_emotion(self, conversation_id, time_window_minutes=30):
        """
        Get the dominant emotion over a time period.
        
        Args:
            conversation_id (str): The conversation identifier
            time_window_minutes (int, optional): Time window in minutes for analysis
            
        Returns:
            dict: The dominant emotion data or None if no data
        """
        try:
            # Calculate the time window
            time_threshold = datetime.utcnow() - timedelta(minutes=time_window_minutes)
            
            # Get emotions in the time window
            emotions = EmotionTracker.query.filter(
                EmotionTracker.conversation_id == conversation_id,
                EmotionTracker.created_at >= time_threshold
            ).order_by(
                EmotionTracker.created_at.desc()
            ).all()
            
            if not emotions:
                return None
                
            # Count emotions by type
            emotion_counts = {}
            for e in emotions:
                if e.primary_emotion not in emotion_counts:
                    emotion_counts[e.primary_emotion] = {
                        'count': 0,
                        'total_confidence': 0,
                        'total_intensity': 0
                    }
                emotion_counts[e.primary_emotion]['count'] += 1
                emotion_counts[e.primary_emotion]['total_confidence'] += e.confidence
                emotion_counts[e.primary_emotion]['total_intensity'] += e.intensity
            
            # Find the most common emotion
            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1]['count'])
            emotion_name = dominant_emotion[0]
            emotion_data = dominant_emotion[1]
            
            # Calculate averages
            avg_confidence = emotion_data['total_confidence'] / emotion_data['count']
            avg_intensity = emotion_data['total_intensity'] / emotion_data['count']
            
            return {
                'primary_emotion': emotion_name,
                'count': emotion_data['count'],
                'total_count': len(emotions),
                'percentage': emotion_data['count'] / len(emotions) * 100,
                'avg_confidence': avg_confidence,
                'avg_intensity': avg_intensity
            }
            
        except Exception as e:
            logger.error(f"Error retrieving dominant emotion: {str(e)}")
            return None
            
    def get_emotion_timeline(self, conversation_id, days=7):
        """
        Get emotion data over time for visualization.
        
        Args:
            conversation_id (str): The conversation identifier
            days (int, optional): Number of days to analyze
            
        Returns:
            dict: Emotion timeline data
        """
        try:
            # Calculate the time window
            time_threshold = datetime.utcnow() - timedelta(days=days)
            
            # Get emotions in the time window
            emotions = EmotionTracker.query.filter(
                EmotionTracker.conversation_id == conversation_id,
                EmotionTracker.created_at >= time_threshold
            ).order_by(
                EmotionTracker.created_at.asc()
            ).all()
            
            # Initialize timeline data
            timeline = {
                'timestamps': [],
                'emotions': {
                    'happy': [],
                    'sad': [],
                    'angry': [],
                    'afraid': [],
                    'surprised': [],
                    'neutral': []
                }
            }
            
            # Process emotions
            for e in emotions:
                # Add timestamp
                timestamp = e.created_at.isoformat() if e.created_at else None
                timeline['timestamps'].append(timestamp)
                
                # Get emotion scores
                scores = e.get_emotion_data()
                
                # Add each emotion score to timeline
                for emotion in timeline['emotions'].keys():
                    score = scores.get(emotion, 0) * e.intensity
                    timeline['emotions'][emotion].append(score)
            
            return timeline
            
        except Exception as e:
            logger.error(f"Error retrieving emotion timeline: {str(e)}")
            return {
                'timestamps': [],
                'emotions': {
                    'happy': [],
                    'sad': [],
                    'angry': [],
                    'afraid': [],
                    'surprised': [],
                    'neutral': []
                }
            }
            
    def analyze_emotional_patterns(self, conversation_id):
        """
        Analyze emotional patterns for a conversation.
        
        Args:
            conversation_id (str): The conversation identifier
            
        Returns:
            dict: Analysis of emotional patterns
        """
        try:
            # Get all emotions for this conversation
            emotions = EmotionTracker.query.filter_by(
                conversation_id=conversation_id
            ).order_by(
                EmotionTracker.created_at.asc()
            ).all()
            
            if not emotions:
                return {
                    'dominant_emotion': 'neutral',
                    'emotional_stability': 1.0,  # Higher is more stable
                    'emotional_range': 0.0,      # Higher is wider range
                    'emotion_counts': {},
                    'emotion_transitions': {}
                }
                
            # Count emotions by type
            emotion_counts = {}
            for e in emotions:
                if e.primary_emotion not in emotion_counts:
                    emotion_counts[e.primary_emotion] = 0
                emotion_counts[e.primary_emotion] += 1
            
            # Find the most common emotion
            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])
            
            # Calculate emotional stability (fewer transitions = more stable)
            transitions = 0
            prev_emotion = None
            emotion_transitions = {}
            
            for e in emotions:
                current_emotion = e.primary_emotion
                
                if prev_emotion and prev_emotion != current_emotion:
                    transitions += 1
                    
                    # Track transition patterns
                    transition_key = f"{prev_emotion}_to_{current_emotion}"
                    if transition_key not in emotion_transitions:
                        emotion_transitions[transition_key] = 0
                    emotion_transitions[transition_key] += 1
                    
                prev_emotion = current_emotion
            
            # Calculate stability (1 = stable, 0 = unstable)
            if len(emotions) > 1:
                emotional_stability = 1.0 - (transitions / (len(emotions) - 1))
            else:
                emotional_stability = 1.0
                
            # Calculate emotional range (number of different emotions expressed)
            emotional_range = len(emotion_counts) / 6.0  # 6 is max number of emotions
            
            return {
                'dominant_emotion': dominant_emotion[0],
                'emotional_stability': emotional_stability,
                'emotional_range': emotional_range,
                'emotion_counts': emotion_counts,
                'emotion_transitions': emotion_transitions
            }
            
        except Exception as e:
            logger.error(f"Error analyzing emotional patterns: {str(e)}")
            return {
                'dominant_emotion': 'neutral',
                'emotional_stability': 1.0,
                'emotional_range': 0.0,
                'emotion_counts': {},
                'emotion_transitions': {}
            }