from datetime import datetime
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
    
    __table_args__ = (
        db.UniqueConstraint('conversation_id', 'word', 'mode', name='uix_vocab_conv_word_mode'),
    )
    
    def __repr__(self):
        return f'<BotVocabulary {self.word}: {self.frequency}>'
