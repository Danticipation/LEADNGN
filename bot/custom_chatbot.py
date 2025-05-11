"""
Custom ChatBot implementation based on MirrorBot concept
"""
import logging
import importlib
import datetime
import uuid

# Configure logger
logger = logging.getLogger(__name__)

class CustomChatBot:
    """
    A chatbot implementation specialized for the MirrorBot personality modes
    """
    
    def __init__(self, name, storage_adapter=None, logic_adapters=None,
                 preprocessors=None, response_selection_method=None, **kwargs):
        """
        Initialize the ChatBot.
        
        Args:
            name (str): The name of the chatbot
            storage_adapter (str): Path to the storage adapter class
            logic_adapters (list): List of paths to logic adapter classes
            preprocessors (list): List of preprocessor functions to use
            response_selection_method (str): Path to response selection method
            **kwargs: Additional arguments
        """
        self.name = name
        self.read_only = kwargs.get('read_only', False)
        
        self.storage = self._initialize_class(storage_adapter)
        
        # Initialize preprocessors
        self.preprocessors = []
        preprocessors = preprocessors or []
        for preprocessor in preprocessors:
            self.preprocessors.append(self._initialize_function(preprocessor))
        
        # Initialize logic adapters
        self.logic_adapters = []
        logic_adapters = logic_adapters or []
        for adapter in logic_adapters:
            self.logic_adapters.append(self._initialize_class(adapter))
    
    def _initialize_class(self, path):
        """
        Dynamically import a class from its dotted path.
        
        Args:
            path (str): Dotted path to the class
            
        Returns:
            object: Instance of the specified class
        """
        try:
            if not path:
                raise ImportError(f"No path provided")
                
            module_path, class_name = path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            Cls = getattr(module, class_name)
            
            return Cls(self)
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Error initializing class {path}: {str(e)}")
            raise
    
    def _initialize_function(self, path):
        """
        Dynamically import a function from its dotted path.
        
        Args:
            path (str): Dotted path to the function
            
        Returns:
            function: The imported function
        """
        try:
            if not path:
                raise ImportError(f"No path provided")
                
            module_path, function_name = path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            function = getattr(module, function_name)
            
            return function
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Error initializing function {path}: {str(e)}")
            raise
    
    def get_response(self, input_text, additional_response_selection_parameters=None):
        """
        Return a response for the given input text.
        
        Args:
            input_text (str): The text input
            additional_response_selection_parameters (dict): Parameters to 
                help select a response
                
        Returns:
            Statement: The response Statement
        """
        from .conversation import Statement
        
        additional_response_selection_parameters = additional_response_selection_parameters or {}
        
        conversation = additional_response_selection_parameters.get('conversation_id', str(uuid.uuid4()))
        
        # Create input statement
        input_statement = Statement(
            text=input_text,
            conversation=conversation,
            persona='user'
        )
        
        # Preprocess the input statement
        for preprocessor in self.preprocessors:
            input_statement = preprocessor(input_statement)
        
        # Get all responses from logic adapters
        results = []
        for adapter in self.logic_adapters:
            if adapter.can_process(input_statement):
                try:
                    result = adapter.process(input_statement, additional_response_selection_parameters)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error getting response from {adapter.__class__.__name__}: {str(e)}")
        
        # Select best response based on confidence
        best_response = None
        best_confidence = -1
        
        for result in results:
            if result.confidence > best_confidence:
                best_response = result
                best_confidence = result.confidence
        
        # If no response, create default
        if not best_response:
            best_response = Statement(
                text="I'm sorry, I don't have a response for that."
            )
            best_response.confidence = 0.0
        
        # Add response to database
        if not self.read_only:
            try:
                self.storage.create(
                    text=best_response.text,
                    in_response_to=input_statement.text,
                    conversation=conversation,
                    persona=self.name
                )
            except Exception as e:
                logger.error(f"Error saving response to database: {str(e)}")
        
        return best_response