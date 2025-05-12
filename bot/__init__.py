"""
Bot initialization and factory methods
"""
import logging
import os
from pathlib import Path
from .custom_chatbot import CustomChatBot
from .conversation import Statement
from .logic_adapters import (
    ImitationLogicAdapter, 
    LiteralLogicAdapter, 
    EchoLogicAdapter, 
    OverUnderstandingLogicAdapter,
    NonsenseLogicAdapter
)
from .advanced_logic_adapters import AdvancedImitationLogicAdapter

# Configure logger
logger = logging.getLogger(__name__)

# Ensure data directory exists for SQLite database
data_dir = Path(__file__).parent.parent / 'data'
data_dir.mkdir(exist_ok=True)

# Define available bot modes and their friendly names
BOT_MODES = {
    'imitation': 'Imitation Mode',
    'advanced_imitation': 'Advanced Imitation Mode',
    'literal': 'Literal Mode',
    'echo': 'Echo Mode',
    'overunderstanding': 'Over-Understanding Mode',
    'nonsense': 'Nonsense Mode'
}

def create_bot(mode='advanced_imitation'):
    """
    Factory function to create a chatbot with the specified mode
    
    Args:
        mode (str): The bot personality mode to use
    
    Returns:
        CustomChatBot: Configured ChatBot instance
    """
    # Map modes to logic adapters
    logic_adapter_map = {
        'imitation': 'bot.logic_adapters.ImitationLogicAdapter',
        'advanced_imitation': 'bot.advanced_logic_adapters.AdvancedImitationLogicAdapter',
        'literal': 'bot.logic_adapters.LiteralLogicAdapter',
        'echo': 'bot.logic_adapters.EchoLogicAdapter',
        'overunderstanding': 'bot.logic_adapters.OverUnderstandingLogicAdapter',
        'nonsense': 'bot.logic_adapters.NonsenseLogicAdapter'
    }
    
    # Use default if an invalid mode is provided
    if mode not in logic_adapter_map:
        mode = 'advanced_imitation'
        logger.warning(f"Invalid mode '{mode}' specified, using 'advanced_imitation' instead")
    
    # Create a new CustomChatBot instance
    bot = CustomChatBot(
        name=f"MirrorBot-{mode.replace('advanced_', '')}",  # Keep original name but use advanced adapter
        storage_adapter="bot.storage_adapters.SQLStorageAdapter",
        logic_adapters=[
            logic_adapter_map[mode]
        ],
        preprocessors=[
            'bot.preprocessors.clean_whitespace',
        ],
        read_only=False
    )
    
    return bot

def get_bot_modes():
    """
    Get a dictionary of available bot modes
    
    Returns:
        dict: Dictionary of bot modes and their display names
    """
    return BOT_MODES

def get_bot_stats(conversation_id):
    """
    Get vocabulary statistics for a conversation
    
    Args:
        conversation_id (str): The conversation ID to get stats for
    
    Returns:
        dict: Dictionary containing vocabulary stats
    """
    # Import here to avoid circular imports
    from app import db
    from models import BotVocabulary
    
    # Get vocabulary words sorted by frequency
    words = BotVocabulary.query.filter_by(conversation_id=conversation_id).order_by(
        BotVocabulary.frequency.desc()).limit(50).all()
    
    # Calculate total vocabulary size
    total_vocab = BotVocabulary.query.filter_by(conversation_id=conversation_id).count()
    
    # Format response
    vocab_data = [{'word': word.word, 'frequency': word.frequency, 'mode': word.mode} for word in words]
    
    # Get stats by mode
    mode_stats = {}
    for mode in BOT_MODES.keys():
        mode_count = BotVocabulary.query.filter_by(conversation_id=conversation_id, mode=mode).count()
        mode_stats[mode] = mode_count
    
    return {
        'vocabulary': vocab_data, 
        'total': total_vocab,
        'by_mode': mode_stats
    }
