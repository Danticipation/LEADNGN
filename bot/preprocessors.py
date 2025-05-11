"""
Preprocessors for handling and normalizing input text.
"""
import re

def clean_whitespace(statement):
    """
    Remove any consecutive whitespace characters from the statement text.
    
    Args:
        statement: The statement to be preprocessed.
    
    Returns:
        The preprocessed statement with normalized whitespace.
    """
    # Regular expression to match one or more whitespace characters
    whitespace_pattern = re.compile(r'\s+')
    
    # Replace consecutive whitespace with a single space
    statement.text = whitespace_pattern.sub(' ', statement.text.strip())
    
    return statement

def convert_to_lowercase(statement):
    """
    Convert the statement text to lowercase.
    
    Args:
        statement: The statement to be preprocessed.
    
    Returns:
        The preprocessed statement with all text converted to lowercase.
    """
    statement.text = statement.text.lower()
    
    return statement

def remove_punctuation(statement):
    """
    Remove punctuation characters from the statement text.
    
    Args:
        statement: The statement to be preprocessed.
    
    Returns:
        The preprocessed statement with punctuation removed.
    """
    # Regular expression to match punctuation
    punctuation_pattern = re.compile(r'[^\w\s]')
    
    # Remove punctuation
    statement.text = punctuation_pattern.sub('', statement.text)
    
    return statement