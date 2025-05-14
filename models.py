from datetime import datetime
import json
from app import db

class Message(db.Model):
    """Model to store chat messages"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(36), nullable=False, index=True)
    sender = db.Column(db.String(20), nullable=False)  # 'user' or 'bot'
    content = db.Column(db.Text, nullable=False)
    mode = db.Column(db.String(20), nullable=False)  # Bot mode used
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.id}: {self.sender}>'

class BotVocabulary(db.Model):
    """Model to track words the bot has learned"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(36), nullable=False, index=True)
    word = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.Integer, default=1)
    mode = db.Column(db.String(20), nullable=False)  # Bot mode used
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add parts of speech for advanced learning
    pos_tag = db.Column(db.String(10), nullable=True)  # Part of speech tag (NOUN, VERB, etc.)
    
    __table_args__ = (
        db.UniqueConstraint('conversation_id', 'word', 'mode', name='uix_vocab_conv_word_mode'),
    )
    
    def __repr__(self):
        return f'<BotVocabulary {self.word}: {self.frequency}>'

class SpeechPattern(db.Model):
    """Model to track speech patterns for advanced learning"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(36), nullable=False, index=True)
    pattern_type = db.Column(db.String(20), nullable=False)  # 'ngram', 'pos_sequence', 'phrase'
    pattern = db.Column(db.Text, nullable=False)  # Changed from String(255) to Text for long patterns
    frequency = db.Column(db.Integer, default=1)
    mode = db.Column(db.String(20), nullable=False)  # Bot mode used
    example = db.Column(db.Text, nullable=True)  # Example text containing this pattern
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('conversation_id', 'pattern', 'mode', name='uix_pattern_conv_pattern_mode'),
    )
    
    def __repr__(self):
        return f'<SpeechPattern {self.pattern_type}: {self.pattern}>'

class PhraseTemplate(db.Model):
    """Model to store sentence templates for mimicking speech patterns"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(36), nullable=False, index=True)
    template = db.Column(db.Text, nullable=False)  # Template with POS placeholders
    pos_structure = db.Column(db.Text, nullable=False)  # POS sequence as JSON
    frequency = db.Column(db.Integer, default=1)
    mode = db.Column(db.String(20), nullable=False)  # Bot mode used
    example = db.Column(db.Text, nullable=True)  # Original sentence this template was derived from
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<PhraseTemplate {self.id}: {self.template[:30]}...>'

class MemoryFact(db.Model):
    """Model to store specific facts about the user learned from conversations"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(36), nullable=False, index=True)
    subject = db.Column(db.String(100), nullable=False)  # What the fact is about (e.g., "name", "occupation", "birthday")
    fact = db.Column(db.Text, nullable=False)  # The actual fact content
    confidence = db.Column(db.Float, default=1.0)  # How confident the bot is about this fact (0-1)
    source_message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)  # Message where fact was learned
    source_text = db.Column(db.Text, nullable=True)  # Portion of the text containing the fact
    fact_metadata = db.Column(db.Text, nullable=True)  # JSON string for additional metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    mentioned_count = db.Column(db.Integer, default=1)  # How many times this fact has been mentioned
    priority = db.Column(db.Integer, default=5)  # Importance (1-10, with 10 being highest)
    
    # The context in which to use this fact (greeting, personal, preferences, etc.)
    context_tags = db.Column(db.Text, default='["general"]')  # JSON list of contexts
    
    __table_args__ = (
        db.UniqueConstraint('conversation_id', 'subject', name='uix_memory_fact_conv_subject'),
    )
    
    def __repr__(self):
        return f'<MemoryFact {self.subject}: {self.fact[:30]}...>'
    
    def get_context_tags(self):
        """Return context tags as a list"""
        if not self.context_tags:
            return ['general']
        try:
            return json.loads(self.context_tags)
        except:
            return ['general']
    
    def set_context_tags(self, tags_list):
        """Set context tags from a list"""
        if not tags_list:
            self.context_tags = json.dumps(['general'])
        else:
            self.context_tags = json.dumps(tags_list)
    
    def get_metadata(self):
        """Return metadata as a dictionary"""
        if not self.fact_metadata:
            return {}
        try:
            return json.loads(self.fact_metadata)
        except:
            return {}
    
    def set_metadata(self, metadata_dict):
        """Set metadata from a dictionary"""
        if not metadata_dict:
            self.fact_metadata = None
        else:
            self.fact_metadata = json.dumps(metadata_dict)
