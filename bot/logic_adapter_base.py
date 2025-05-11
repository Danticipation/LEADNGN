"""
This module contains the base class for all logic adapters
"""
from .conversation import Statement

class LogicAdapter:
    """
    Base class for all logic adapters 
    
    Logic adapters determine how the bot selects a response
    based on user input.
    """
    
    def __init__(self, chatbot, **kwargs):
        """
        Initialize the adapter with the chatbot instance.
        
        Args:
            chatbot: The ChatBot instance
            **kwargs: Additional keyword arguments
        """
        self.chatbot = chatbot
        self.language = kwargs.get('language', 'en')
        
    def can_process(self, statement):
        """
        Check if this adapter can process the input statement.
        
        Args:
            statement (Statement): The statement to be processed
            
        Returns:
            bool: True if the adapter can process the statement
        """
        return True
        
    def process(self, statement, additional_response_selection_parameters=None):
        """
        Process the input statement and determine a response.
        
        Args:
            statement (Statement): The statement to be processed
            additional_response_selection_parameters (dict): Additional parameters
                to help select a response
                
        Returns:
            Statement: The selected response statement
        """
        raise NotImplementedError(
            'Logic adapters must implement the `process` method'
        )
        
    def select_response(self, input_statement, response_list, additional_response_selection_parameters=None):
        """
        Select a response from a list of potential responses.
        
        Args:
            input_statement (Statement): The input statement
            response_list (list): A list of potential response statements
            additional_response_selection_parameters (dict): Additional parameters
                to help select a response
                
        Returns:
            Statement: The selected response statement
        """
        if not response_list:
            return None
            
        # Default to returning the first response
        return response_list[0]