"""
Storage adapters for the MirrorBot
"""
import json
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create a base class for declarative models
Base = declarative_base()

class Statement(Base):
    """
    A statement represents a single spoken entity, sentence or phrase.
    """
    __tablename__ = 'statements'

    id = Column(Integer, primary_key=True)
    text = Column(String(255), nullable=False)
    search_text = Column(String(255), nullable=False)
    conversation = Column(String(32), nullable=False)
    persona = Column(String(50), nullable=True)
    tags = Column(Text, default='[]')  # Stored as JSON string
    in_response_to = Column(String(255), nullable=True)
    search_in_response_to = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    
    def get_tags(self):
        """Return the list of tags."""
        return json.loads(self.tags)
    
    def add_tags(self, *tags):
        """Add a list of tags to the statement."""
        current_tags = self.get_tags()
        for tag in tags:
            if tag not in current_tags:
                current_tags.append(tag)
        self.tags = json.dumps(current_tags)


class SQLStorageAdapter:
    """
    SQLAlchemy storage adapter for the MirrorBot.
    """
    
    def __init__(self, chatbot=None, **kwargs):
        """
        Initialize the adapter with the given database URI.
        
        Args:
            chatbot: The chatbot instance
            **kwargs: Additional arguments including database_uri
        """
        self.chatbot = chatbot
        self.database_uri = kwargs.get('database_uri', 'sqlite:///db.sqlite3')
        self.engine = create_engine(self.database_uri)
        self.Session = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
    
    def get_statement_model(self):
        """
        Return the statement model used by this adapter.
        """
        return Statement
    
    def count(self):
        """
        Return the number of entries in the database.
        """
        session = self.Session()
        statement_count = session.query(Statement).count()
        session.close()
        return statement_count
        
    def find(self, text=None, conversation=None, in_response_to=None):
        """
        Find statements that match the given criteria.
        """
        from .conversation import Statement as MBStatement
        
        session = self.Session()
        query = session.query(Statement)
        
        if text:
            query = query.filter(Statement.text == text)
        
        if conversation:
            query = query.filter(Statement.conversation == conversation)
            
        if in_response_to:
            query = query.filter(Statement.in_response_to == in_response_to)
            
        results = query.all()
        
        # Convert to MirrorBot Statement objects
        statement_objects = []
        for statement in results:
            statement_obj = MBStatement(
                text=statement.text,
                in_response_to=statement.in_response_to
            )
            statement_obj.id = statement.id
            statement_obj.search_text = statement.search_text
            statement_obj.conversation = statement.conversation
            statement_obj.persona = statement.persona
            statement_obj.created_at = statement.created_at
            
            # Add tags
            for tag in statement.get_tags():
                statement_obj.add_tags(tag)
                
            statement_objects.append(statement_obj)
            
        session.close()
        return statement_objects
        
    def create(self, **kwargs):
        """
        Create a new statement in the database.
        """
        session = self.Session()
        
        statement = Statement(
            text=kwargs.get('text'),
            search_text=kwargs.get('search_text', kwargs.get('text', '')),
            conversation=kwargs.get('conversation', ''),
            persona=kwargs.get('persona', ''),
            in_response_to=kwargs.get('in_response_to'),
            search_in_response_to=kwargs.get('search_in_response_to', 
                                            kwargs.get('in_response_to', '')),
            tags=json.dumps(kwargs.get('tags', []))
        )
        
        session.add(statement)
        session.commit()
        
        statement_id = statement.id
        
        session.close()
        
        return self.get_statement_by_id(statement_id)
        
    def get_statement_by_id(self, statement_id):
        """
        Get a statement by its ID.
        """
        from .conversation import Statement as MBStatement
        
        session = self.Session()
        statement = session.query(Statement).get(statement_id)
        
        if statement:
            statement_obj = MBStatement(
                text=statement.text,
                in_response_to=statement.in_response_to
            )
            statement_obj.id = statement.id
            statement_obj.search_text = statement.search_text
            statement_obj.conversation = statement.conversation
            statement_obj.persona = statement.persona
            statement_obj.created_at = statement.created_at
            
            # Add tags
            for tag in statement.get_tags():
                statement_obj.add_tags(tag)
                
            session.close()
            return statement_obj
            
        session.close()
        return None
        
    def update(self, statement):
        """
        Update a statement in the database.
        """
        session = self.Session()
        record = session.query(Statement).get(statement.id)
        
        if record:
            record.text = statement.text
            record.search_text = statement.search_text
            record.conversation = statement.conversation
            record.persona = statement.persona
            record.in_response_to = statement.in_response_to
            record.search_in_response_to = statement.search_in_response_to
            
            # Update tags
            if hasattr(statement, 'get_tags'):
                record.tags = json.dumps(statement.get_tags())
            
            session.commit()
            
        session.close()
        
    def remove(self, statement_id):
        """
        Remove a statement from the database.
        """
        session = self.Session()
        statement = session.query(Statement).get(statement_id)
        
        if statement:
            session.delete(statement)
            session.commit()
            
        session.close()