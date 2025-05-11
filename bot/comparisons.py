"""
Text comparison utilities for the MirrorBot
"""
import re

class LevenshteinDistance:
    """
    Compare two statements based on the Levenshtein distance
    of each statement's text.
    """
    
    def __init__(self, language='en'):
        """
        Initialize the comparator.
        """
        self.language = language
        
    def compare(self, statement_a, statement_b):
        """
        Compare the two statements based on text similarity.
        
        Args:
            statement_a: The first statement object
            statement_b: The second statement object
            
        Returns:
            float: The percentage similarity between statements
        """
        return self.compare_text(statement_a.text, statement_b.text)
        
    def compare_text(self, text_a, text_b):
        """
        Calculate the Levenshtein distance between two strings.
        
        Args:
            text_a: The first string
            text_b: The second string
            
        Returns:
            float: The percentage similarity between texts
        """
        # Normalize whitespace and lowercase
        text_a = ' '.join(text_a.lower().split())
        text_b = ' '.join(text_b.lower().split())
        
        # Check for exact match
        if text_a == text_b:
            return 1.0
            
        # Check for empty string
        if not text_a or not text_b:
            return 0.0
            
        # Calculate Levenshtein distance
        distance = self._levenshtein_distance(text_a, text_b)
        
        # Calculate similarity as a ratio
        max_len = max(len(text_a), len(text_b))
        similarity = 1.0 - (distance / max_len)
        
        return similarity
    
    def _levenshtein_distance(self, text_a, text_b):
        """
        Calculate the Levenshtein distance between two strings.
        
        Args:
            text_a: The first string
            text_b: The second string
            
        Returns:
            int: The Levenshtein distance between the strings
        """
        if len(text_a) < len(text_b):
            return self._levenshtein_distance(text_b, text_a)
            
        if not text_b:
            return len(text_a)
            
        previous_row = range(len(text_b) + 1)
        for i, c1 in enumerate(text_a):
            current_row = [i + 1]
            for j, c2 in enumerate(text_b):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
            
        return previous_row[-1]