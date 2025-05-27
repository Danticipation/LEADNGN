"""
Sentiment Analyzer module for MirrorBot.

This module provides functions to detect emotions in text using
various techniques including rule-based analysis and SpaCy's NLP capabilities.
"""

import re
import logging
import random
from collections import defaultdict

import spacy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load SpaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("SpaCy model not found. Using blank model instead.")
    nlp = spacy.blank("en")

# Define emotion categories and related keywords
EMOTION_KEYWORDS = {
    'happy': [
        'happy', 'joy', 'excited', 'delighted', 'glad', 'pleased', 'thrilled', 
        'enjoy', 'love', 'great', 'excellent', 'amazing', 'wonderful', 'awesome',
        'yay', 'woohoo', 'hurray', 'smile', 'laugh', '😊', '😁', '😄', '🙂', '😃',
        '😀', '❤️', '👍', '🎉'
    ],
    'sad': [
        'sad', 'unhappy', 'upset', 'depressed', 'disappointed', 'miserable', 'sorry',
        'regret', 'miss', 'lonely', 'heartbroken', 'grief', 'cry', 'tears', '😢',
        '😭', '😔', '😥', '💔', '👎'
    ],
    'angry': [
        'angry', 'mad', 'frustrated', 'annoyed', 'irritated', 'furious', 'rage',
        'hate', 'dislike', 'resent', 'offensive', 'damn', 'terrible', 'awful',
        '😠', '😡', '🤬', '👿', '😤'
    ],
    'afraid': [
        'afraid', 'scared', 'frightened', 'terrified', 'fear', 'anxious', 'nervous',
        'worry', 'panic', 'dread', 'horror', 'help', '😨', '😱', '😰', '😧', '😦'
    ],
    'surprised': [
        'surprised', 'amazed', 'astonished', 'shocked', 'stunned', 'unexpected',
        'wow', 'whoa', 'unbelievable', 'incredible', 'what', '😲', '😮', '😯', '😳'
    ],
    'neutral': []  # Default category when no emotion is detected
}

# Intensity modifiers increase or decrease the strength of emotions
INTENSITY_MODIFIERS = {
    'increase': ['very', 'really', 'extremely', 'incredibly', 'absolutely', 'so', 'too', 'completely'],
    'decrease': ['somewhat', 'slightly', 'a bit', 'a little', 'kind of', 'sort of', 'barely']
}

# Negation words flip emotions (happy -> not happy)
NEGATION_WORDS = ['not', 'no', "isn't", "aren't", "wasn't", "weren't", "don't", "doesn't", 
                  "didn't", "can't", "couldn't", "shouldn't", "wouldn't", "hasn't", "haven't", 
                  "hadn't", "never", "none", "nothing", "nowhere", "nobody"]

# Punctuation indicators can emphasize emotions
PUNCTUATION_EMPHASIS = {
    '!': 0.2,        # Single exclamation adds 0.2 intensity
    '!!': 0.3,       # Double exclamation adds 0.3 intensity
    '!!!': 0.5,      # Triple or more adds 0.5 intensity
    '?': 0.1,        # Question marks add slight intensity
    '??': 0.2,
    '???': 0.3,
    '?!': 0.4,       # Mixed punctuation indicates strong emotion
}

# Basic reaction templates for different emotions
EMOTION_REACTIONS = {
    'happy': [
        "I'm glad to hear that!",
        "That sounds wonderful!",
        "How exciting!",
        "That's great news!",
        "Awesome!"
    ],
    'sad': [
        "I'm sorry to hear that.",
        "That sounds difficult.",
        "I understand that can be hard.",
        "That's unfortunate.",
        "I hope things get better."
    ],
    'angry': [
        "I understand your frustration.",
        "That does sound annoying.",
        "I can see why that would be upsetting.",
        "That's definitely frustrating.",
        "I hear your concern."
    ],
    'afraid': [
        "That sounds concerning.",
        "I understand why you might be worried.",
        "It's okay to be cautious about that.",
        "That would make me nervous too.",
        "I hope everything turns out alright."
    ],
    'surprised': [
        "Wow, really?",
        "That's unexpected!",
        "I wouldn't have guessed that!",
        "How surprising!",
        "That's quite a surprise!"
    ],
    'neutral': [
        "I see.",
        "Interesting.",
        "I understand.",
        "Got it.",
        "I hear you."
    ]
}

def analyze_sentiment(text):
    """
    Analyze the sentiment/emotion of the given text.
    
    Args:
        text (str): The input text to analyze
        
    Returns:
        dict: A dictionary containing the primary emotion, confidence score,
              and a breakdown of all detected emotions
    """
    if not text:
        return {
            'primary_emotion': 'neutral',
            'confidence': 1.0,
            'emotion_scores': {'neutral': 1.0},
            'intensity': 0.5
        }
    
    # Lowercase the text for better matching
    text_lower = text.lower()
    
    # Process with SpaCy for more advanced analysis
    doc = nlp(text_lower)
    
    # Initialize emotion scores dictionary with default values of 0
    emotion_scores = defaultdict(float)
    for emotion in EMOTION_KEYWORDS.keys():
        emotion_scores[emotion] = 0.0
    
    # Default to neutral if no emotions are detected
    emotion_scores['neutral'] = 0.3
    
    # Track negation and intensifiers
    negation_present = False
    intensity_modifier = 1.0
    
    # Check for negation words within the last 5 tokens of each token in the text
    for i, token in enumerate(doc):
        # Check if word is a negation
        if token.text in NEGATION_WORDS:
            # Look ahead up to 5 tokens to find emotion keywords
            for j in range(1, 6):
                if i + j < len(doc):
                    negation_present = True
        
        # Check if word is an intensity modifier
        if token.text in INTENSITY_MODIFIERS['increase']:
            intensity_modifier = 1.5
        elif token.text in INTENSITY_MODIFIERS['decrease']:
            intensity_modifier = 0.5
    
    # Check for emotion keywords in the text
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                # If negation is present, reduce this emotion and increase opposite emotions
                if negation_present and any(neg + " " + keyword in text_lower for neg in NEGATION_WORDS):
                    emotion_scores[emotion] -= 0.3
                    # Increase opposite emotions
                    if emotion == 'happy':
                        emotion_scores['sad'] += 0.2
                    elif emotion == 'sad':
                        emotion_scores['happy'] += 0.2
                else:
                    # Add score for the emotion, considering intensity modifiers
                    emotion_scores[emotion] += 0.3 * intensity_modifier
    
    # Check for emojis and give them higher weight
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for keyword in keywords:
            try:
                # Check if this is likely an emoji (Unicode characters)
                if len(keyword) <= 2 and any(ord(char) > 127 for char in keyword):
                    # This is likely an emoji
                    if keyword in text:
                        emotion_scores[emotion] += 0.5  # Emojis have stronger weight
            except (UnicodeError, ValueError):
                # Skip if there's any Unicode issue
                continue
    
    # Check for punctuation emphasis
    for punct, value in PUNCTUATION_EMPHASIS.items():
        if punct in text:
            # Find the most likely emotion to emphasize
            primary = max(emotion_scores.items(), key=lambda x: x[1])
            if primary[0] != 'neutral':
                emotion_scores[primary[0]] += value
    
    # Ensure scores are within 0-1 range
    for emotion in emotion_scores:
        emotion_scores[emotion] = max(0, min(1, emotion_scores[emotion]))
    
    # Determine the primary emotion
    primary_emotion = max(emotion_scores.items(), key=lambda x: x[1])
    
    # If all emotions have low scores, default to neutral
    if primary_emotion[1] < 0.3:
        primary_emotion = ('neutral', max(0.3, emotion_scores['neutral']))
    
    # Calculate overall intensity (0-1 scale)
    overall_intensity = sum(emotion_scores.values()) / len(emotion_scores)
    overall_intensity = min(1.0, overall_intensity)  # Cap at 1.0
    
    return {
        'primary_emotion': primary_emotion[0],
        'confidence': primary_emotion[1],
        'emotion_scores': dict(emotion_scores),
        'intensity': overall_intensity
    }

def get_emotion_response(emotion, intensity=0.5, existing_response=None):
    """
    Get an emotion-appropriate response or modify an existing response
    to reflect the detected emotion.
    
    Args:
        emotion (str): The primary emotion to respond to
        intensity (float): The intensity of the emotion (0-1)
        existing_response (str, optional): Existing response to modify
        
    Returns:
        str: An emotion-appropriate response or the modified existing response
    """
    if emotion not in EMOTION_REACTIONS:
        emotion = 'neutral'
    
    # If no existing response, return a simple emotional reaction
    if not existing_response:
        return random.choice(EMOTION_REACTIONS[emotion])
    
    # If we have an existing response, we'll modify it based on emotion
    if intensity < 0.3:  # Low intensity
        # Just return the existing response for low intensity emotions
        return existing_response
    
    elif intensity < 0.7:  # Medium intensity
        # Add an emotional acknowledgment at the beginning
        emotional_prefix = random.choice(EMOTION_REACTIONS[emotion])
        return f"{emotional_prefix} {existing_response}"
    
    else:  # High intensity
        # For high intensity, modify the tone throughout
        if emotion == 'happy':
            # Add exclamation marks and positive language
            response = existing_response.rstrip('.!?') + "!"
            response = response.replace('.', '!')
        elif emotion == 'sad':
            # More subdued, add ellipses
            response = existing_response.rstrip('.!?') + "..."
        elif emotion == 'angry':
            # More direct/emphatic language
            response = existing_response.rstrip('.!?') + "."
            response = response.replace('perhaps', 'definitely')
            response = response.replace('maybe', 'certainly')
        elif emotion == 'afraid':
            # Add cautious language
            response = existing_response.rstrip('.!?') + "..."
            response = response.replace('will', 'might')
            response = response.replace('is', 'could be')
        elif emotion == 'surprised':
            # Add surprise indicators
            response = existing_response.rstrip('.!?') + "!"
            response = "Wow! " + response
        else:
            response = existing_response
            
        return response

def add_emotional_style(text, emotion, intensity=0.5):
    """
    Add emotional styling to text based on the emotion and intensity.
    
    Args:
        text (str): The text to style
        emotion (str): The emotion to style with
        intensity (float): The intensity of the emotion (0-1)
        
    Returns:
        str: The styled text
    """
    if not text:
        return text
        
    # Return original for very low intensity
    if intensity < 0.2:
        return text
    
    # Make a copy to work with
    styled_text = text
    
    # Apply emotion-specific styling
    if emotion == 'happy':
        if intensity > 0.7:
            # Very happy - add multiple exclamations, positive words
            styled_text = styled_text.rstrip('.!?') + "!! 😊"
            styled_text = styled_text.replace('.', '!')
        elif intensity > 0.4:
            # Moderately happy - add exclamation
            styled_text = styled_text.rstrip('.!?') + "! 🙂"
            
    elif emotion == 'sad':
        if intensity > 0.7:
            # Very sad - add ellipses, sad emojis
            styled_text = styled_text.rstrip('.!?') + "... 😔"
        elif intensity > 0.4:
            # Moderately sad
            styled_text = styled_text.rstrip('.!?') + "..."
            
    elif emotion == 'angry':
        if intensity > 0.7:
            # Very angry - emphatic punctuation, angry emoji
            styled_text = styled_text.rstrip('.!?') + "! 😠"
        elif intensity > 0.4:
            # Moderately angry
            styled_text = styled_text.rstrip('.!?') + "."
            
    elif emotion == 'afraid':
        if intensity > 0.7:
            # Very afraid - ellipses, nervous emoji
            styled_text = styled_text.rstrip('.!?') + "... 😨"
        elif intensity > 0.4:
            # Moderately afraid
            styled_text = styled_text.rstrip('.!?') + "..."
            
    elif emotion == 'surprised':
        if intensity > 0.7:
            # Very surprised - exclamation+question, surprised emoji
            styled_text = styled_text.rstrip('.!?') + "?! 😮"
        elif intensity > 0.4:
            # Moderately surprised
            styled_text = styled_text.rstrip('.!?') + "!"
    
    return styled_text