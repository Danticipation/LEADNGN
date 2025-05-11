"""
Utility functions for the Mirror Bot
"""
import re
import random
import logging

logger = logging.getLogger(__name__)

def clean_text(text):
    """
    Clean text by removing extra whitespace and standardizing formatting
    """
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    # Remove leading and trailing whitespace
    text = text.strip()
    return text

def get_learning_stage(vocabulary_size):
    """
    Determine learning stage based on vocabulary size
    
    Args:
        vocabulary_size (int): Size of bot's vocabulary
        
    Returns:
        tuple: (stage_name, percentage)
    """
    # Define vocabulary thresholds for learning stages
    stages = [
        (10, "Infant"),
        (25, "Toddler"),
        (50, "Child"),
        (100, "Teen"),
        (200, "Young Adult"),
        (500, "Adult"),
        (float('inf'), "Wise Elder")
    ]
    
    # Find current stage
    current_stage = "Newborn"
    next_threshold = 1
    
    for threshold, stage_name in stages:
        if vocabulary_size < threshold:
            current_stage = stage_name
            next_threshold = threshold
            break
        current_stage = stage_name
    
    # Calculate percentage to next stage
    if current_stage == "Wise Elder":
        percentage = 100
    else:
        # Find previous threshold
        prev_threshold = 0
        for i, (threshold, stage_name) in enumerate(stages):
            if stage_name == current_stage:
                if i > 0:
                    prev_threshold = stages[i-1][0]
                break
        
        # Calculate percentage within current stage
        range_size = next_threshold - prev_threshold
        progress = vocabulary_size - prev_threshold
        percentage = min(100, max(0, int((progress / range_size) * 100)))
    
    return (current_stage, percentage)

def substitute_word(word, vocabulary, chance=0.3):
    """
    Randomly substitute a word with another from vocabulary
    
    Args:
        word (str): Original word
        vocabulary (list): List of possible substitutions
        chance (float): Probability of substitution
        
    Returns:
        str: Original or substituted word
    """
    if random.random() < chance and vocabulary:
        substitute = random.choice(vocabulary)
        
        # Maintain capitalization
        if word and word[0].isupper():
            substitute = substitute.capitalize()
            
        return substitute
    
    return word
