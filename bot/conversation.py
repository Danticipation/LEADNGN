"""
Classes for representing conversation statements and responses
"""
import json

class Statement:
    """
    A statement represents a single spoken entity, sentence or phrase.
    """
    
    def __init__(self, text, in_response_to=None, **kwargs):
        """
        Initialize a statement object.
        
        Args:
            text: The text content of the statement
            in_response_to: Statement or string this statement is responding to
            **kwargs: Additional keyword arguments
        """
        self.text = text
        self.in_response_to = in_response_to
        
        self.id = kwargs.get('id')
        self.conversation = kwargs.get('conversation')
        self.persona = kwargs.get('persona')
        self.tags = kwargs.get('tags', [])
        self.search_text = kwargs.get('search_text', '')
        self.search_in_response_to = kwargs.get('search_in_response_to', '')
        self.created_at = kwargs.get('created_at')
        
        # Add confidence attribute that we can modify
        self.confidence = 0.0
        
    def __str__(self):
        return self.text
        
    def __repr__(self):
        return f"<Statement text={self.text}>"
        
    def get_tags(self):
        """Return the list of tags."""
        return self.tags
        
    def add_tags(self, *tags):
        """Add a list of tags to the statement."""
        for tag in tags:
            if tag not in self.tags:
                self.tags.append(tag)
                
    def serialize(self):
        """
        Returns a dictionary representation of the statement.
        """
        data = {
            'text': self.text,
            'in_response_to': self.in_response_to,
            'conversation': self.conversation,
            'persona': self.persona,
            'tags': self.tags,
            'confidence': self.confidence
        }
        
        if self.id:
            data['id'] = self.id
            
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
            
        return data