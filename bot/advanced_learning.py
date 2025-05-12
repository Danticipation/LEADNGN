"""
Advanced learning algorithms for improved speech pattern mimicry.
"""
import logging
import json
import re
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Any, Optional

# Configure logger
logger = logging.getLogger(__name__)

class SpeechPatternLearner:
    """
    Advanced learning algorithms for speech patterns and mimicry.
    """
    
    def __init__(self, nlp, db):
        """
        Initialize the speech pattern learner.
        
        Args:
            nlp: spaCy NLP model
            db: SQLAlchemy database connection
        """
        self.nlp = nlp
        self.db = db
        
        # Import here to avoid circular imports
        from models import SpeechPattern, PhraseTemplate, BotVocabulary
        self.SpeechPattern = SpeechPattern
        self.PhraseTemplate = PhraseTemplate
        self.BotVocabulary = BotVocabulary
        
    def learn_from_text(self, text: str, conversation_id: str, mode: str) -> None:
        """
        Apply advanced learning algorithms to a piece of text.
        
        Args:
            text: The text to learn from
            conversation_id: The conversation ID
            mode: The bot mode (imitation, etc.)
        """
        # Parse the text with spaCy
        doc = self.nlp(text)
        
        # Apply different learning methods
        self._learn_ngrams(doc, conversation_id, mode)
        self._learn_pos_patterns(doc, conversation_id, mode)
        self._learn_phrase_templates(doc, conversation_id, mode)
        self._learn_vocabulary_with_pos(doc, conversation_id, mode)
        
        # Commit all changes
        self.db.session.commit()
    
    def _learn_ngrams(self, doc, conversation_id: str, mode: str, max_n: int = 3) -> None:
        """
        Learn n-grams from the text (sequences of n words).
        
        Args:
            doc: spaCy Doc object
            conversation_id: The conversation ID
            mode: The bot mode
            max_n: Maximum n-gram size
        """
        text = doc.text
        tokens = [token.text.lower() for token in doc if not token.is_punct]
        
        # Process different n-gram sizes
        for n in range(2, min(max_n + 1, len(tokens) + 1)):
            for i in range(len(tokens) - n + 1):
                ngram = " ".join(tokens[i:i+n])
                
                # Skip n-grams that are too short
                if len(ngram) < 5:
                    continue
                
                # Check if n-gram exists
                existing = self.SpeechPattern.query.filter_by(
                    conversation_id=conversation_id,
                    pattern=ngram,
                    pattern_type=f"{n}-gram",
                    mode=mode
                ).first()
                
                if existing:
                    existing.frequency += 1
                    existing.last_seen = None  # Will be updated automatically
                    if not existing.example:
                        existing.example = text
                else:
                    # Create new pattern object
                    pattern = self.SpeechPattern()
                    pattern.conversation_id = conversation_id
                    pattern.pattern = ngram
                    pattern.pattern_type = f"{n}-gram"
                    pattern.frequency = 1
                    pattern.mode = mode
                    pattern.example = text
                    self.db.session.add(pattern)
    
    def _learn_pos_patterns(self, doc, conversation_id: str, mode: str, min_length: int = 3) -> None:
        """
        Learn part-of-speech patterns from the text.
        
        Args:
            doc: spaCy Doc object
            conversation_id: The conversation ID
            mode: The bot mode
            min_length: Minimum pattern length
        """
        # Extract POS sequence
        pos_sequence = [token.pos_ for token in doc if not token.is_space]
        
        # Only process if we have a minimum length
        if len(pos_sequence) < min_length:
            return
        
        # Create the pattern string
        pos_pattern = " ".join(pos_sequence)
        
        # Check if pattern exists
        existing = self.SpeechPattern.query.filter_by(
            conversation_id=conversation_id,
            pattern=pos_pattern,
            pattern_type="pos_sequence",
            mode=mode
        ).first()
        
        if existing:
            existing.frequency += 1
            existing.last_seen = None  # Will be updated automatically
            if not existing.example:
                existing.example = doc.text
        else:
            # Create new pattern object
            pattern = self.SpeechPattern()
            pattern.conversation_id = conversation_id
            pattern.pattern = pos_pattern
            pattern.pattern_type = "pos_sequence"
            pattern.frequency = 1
            pattern.mode = mode
            pattern.example = doc.text
            self.db.session.add(pattern)
    
    def _learn_phrase_templates(self, doc, conversation_id: str, mode: str) -> None:
        """
        Learn sentence templates by replacing content words with POS placeholders.
        
        Args:
            doc: spaCy Doc object
            conversation_id: The conversation ID
            mode: The bot mode
        """
        # Skip very short texts
        if len(doc) < 4:
            return
            
        # Create a template by replacing content words with POS tags
        template_parts = []
        pos_structure = []
        
        for token in doc:
            if token.pos_ in ('NOUN', 'VERB', 'ADJ', 'ADV', 'PROPN') and not token.is_stop:
                template_parts.append(f"{{{token.pos_}}}")
                pos_structure.append(token.pos_)
            else:
                template_parts.append(token.text)
                if not token.is_space and not token.is_punct:
                    pos_structure.append(token.pos_)
        
        template = "".join(template_parts)
        pos_structure_json = json.dumps(pos_structure)
        
        # Check if template exists
        existing = self.PhraseTemplate.query.filter_by(
            conversation_id=conversation_id,
            template=template,
            mode=mode
        ).first()
        
        if existing:
            existing.frequency += 1
            existing.last_seen = None  # Will be updated automatically
        else:
            # Create new template object
            template_obj = self.PhraseTemplate()
            template_obj.conversation_id = conversation_id
            template_obj.template = template
            template_obj.pos_structure = pos_structure_json
            template_obj.frequency = 1
            template_obj.mode = mode
            template_obj.example = doc.text
            self.db.session.add(template_obj)
    
    def _learn_vocabulary_with_pos(self, doc, conversation_id: str, mode: str) -> None:
        """
        Learn vocabulary with part-of-speech tags for more accurate mimicry.
        
        Args:
            doc: spaCy Doc object
            conversation_id: The conversation ID
            mode: The bot mode
        """
        for token in doc:
            if token.is_stop or token.is_punct or token.is_space:
                continue
                
            # Check if word exists in vocabulary
            word = token.text.lower().strip()
            if not word:
                continue
                
            existing = self.BotVocabulary.query.filter_by(
                conversation_id=conversation_id,
                word=word,
                mode=mode
            ).first()
            
            if existing:
                existing.frequency += 1
                existing.last_seen = None  # Will be updated automatically
                # Update POS tag if it's not set
                if not existing.pos_tag:
                    existing.pos_tag = token.pos_
            else:
                # Create new vocabulary object
                vocab = self.BotVocabulary()
                vocab.conversation_id = conversation_id
                vocab.word = word
                vocab.frequency = 1
                vocab.mode = mode
                vocab.pos_tag = token.pos_
                self.db.session.add(vocab)


class AdvancedResponseGenerator:
    """
    Generate responses using advanced learning algorithms.
    """
    
    def __init__(self, nlp, db):
        """
        Initialize the response generator.
        
        Args:
            nlp: spaCy NLP model
            db: SQLAlchemy database connection
        """
        self.nlp = nlp
        self.db = db
        
        # Import here to avoid circular imports
        from models import SpeechPattern, PhraseTemplate, BotVocabulary
        self.SpeechPattern = SpeechPattern
        self.PhraseTemplate = PhraseTemplate
        self.BotVocabulary = BotVocabulary
        
    def generate_response(self, input_text: str, conversation_id: str, mode: str) -> Tuple[str, float]:
        """
        Generate a response based on learned patterns.
        
        Args:
            input_text: The input text
            conversation_id: The conversation ID
            mode: The bot mode
            
        Returns:
            Tuple of (response_text, confidence)
        """
        # Parse the input text
        doc = self.nlp(input_text)
        
        # Try different response generation methods in order of preference
        response, confidence = self._generate_from_templates(doc, conversation_id, mode)
        if response and confidence > 0.7:
            return response, confidence
            
        response, confidence = self._generate_from_pos_patterns(doc, conversation_id, mode)
        if response and confidence > 0.6:
            return response, confidence
            
        response, confidence = self._generate_from_ngrams(doc, conversation_id, mode)
        if response and confidence > 0.5:
            return response, confidence
            
        # Fallback to simpler mimicry
        return input_text, 0.3
    
    def _generate_from_templates(self, doc, conversation_id: str, mode: str) -> Tuple[Optional[str], float]:
        """
        Generate a response using learned phrase templates.
        
        Args:
            doc: spaCy Doc object
            conversation_id: The conversation ID
            mode: The bot mode
            
        Returns:
            Tuple of (response_text, confidence)
        """
        # Get top templates by frequency
        templates = self.PhraseTemplate.query.filter_by(
            conversation_id=conversation_id,
            mode=mode
        ).order_by(self.PhraseTemplate.frequency.desc()).limit(10).all()
        
        if not templates:
            return None, 0.0
            
        # Get vocabulary by POS
        vocab_by_pos = {}
        for pos in ('NOUN', 'VERB', 'ADJ', 'ADV', 'PROPN'):
            words = self.BotVocabulary.query.filter_by(
                conversation_id=conversation_id,
                mode=mode,
                pos_tag=pos
            ).order_by(self.BotVocabulary.frequency.desc()).limit(50).all()
            
            vocab_by_pos[pos] = [word.word for word in words]
            
        # If we don't have vocabulary for some POS, use the input text
        for token in doc:
            if token.pos_ in ('NOUN', 'VERB', 'ADJ', 'ADV', 'PROPN'):
                if token.pos_ not in vocab_by_pos or not vocab_by_pos[token.pos_]:
                    if token.pos_ not in vocab_by_pos:
                        vocab_by_pos[token.pos_] = []
                    vocab_by_pos[token.pos_].append(token.text.lower())
        
        # Choose a template weighted by frequency
        import random
        template_options = []
        for template in templates:
            # Add template to options weighted by frequency
            template_options.extend([template] * template.frequency)
            
        if not template_options:
            return None, 0.0
            
        chosen_template = random.choice(template_options)
        
        # Fill in the template
        filled_template = chosen_template.template
        for pos in ('NOUN', 'VERB', 'ADJ', 'ADV', 'PROPN'):
            placeholder = f"{{{pos}}}"
            while placeholder in filled_template:
                if pos in vocab_by_pos and vocab_by_pos[pos]:
                    replacement = random.choice(vocab_by_pos[pos])
                    # Handle capitalization for first word in sentence
                    if filled_template.startswith(placeholder):
                        replacement = replacement.capitalize()
                else:
                    # Fallback if no vocabulary for this POS
                    replacement = pos.lower()
                    
                filled_template = filled_template.replace(placeholder, replacement, 1)
        
        # Calculate confidence based on template frequency and number of learned words
        template_confidence = min(0.4, 0.1 * min(chosen_template.frequency, 4))
        vocab_confidence = min(0.5, 0.01 * sum(len(words) for words in vocab_by_pos.values()))
        
        confidence = 0.1 + template_confidence + vocab_confidence
        
        return filled_template, confidence
    
    def _generate_from_pos_patterns(self, doc, conversation_id: str, mode: str) -> Tuple[Optional[str], float]:
        """
        Generate a response using learned part-of-speech patterns.
        
        Args:
            doc: spaCy Doc object
            conversation_id: The conversation ID
            mode: The bot mode
            
        Returns:
            Tuple of (response_text, confidence)
        """
        # Extract POS sequence from input
        input_pos = [token.pos_ for token in doc if not token.is_space]
        input_pos_str = " ".join(input_pos)
        
        # Find matching POS patterns
        patterns = self.SpeechPattern.query.filter_by(
            conversation_id=conversation_id,
            pattern_type="pos_sequence",
            mode=mode
        ).order_by(self.SpeechPattern.frequency.desc()).limit(20).all()
        
        if not patterns:
            return None, 0.0
            
        # Find best matching pattern using longest common subsequence
        best_pattern = None
        best_score = 0
        
        for pattern in patterns:
            pattern_pos = pattern.pattern.split()
            lcs_length = self._longest_common_subsequence(input_pos, pattern_pos)
            score = lcs_length / max(len(input_pos), len(pattern_pos))
            
            if score > best_score:
                best_score = score
                best_pattern = pattern
        
        if not best_pattern or best_score < 0.3:
            return None, 0.0
        
        # Use the example as basis for response
        example = best_pattern.example
        if not example:
            return None, 0.0
            
        # Calculate confidence
        confidence = 0.1 + min(0.5, 0.1 * best_pattern.frequency) + best_score
        
        return example, confidence
    
    def _generate_from_ngrams(self, doc, conversation_id: str, mode: str) -> Tuple[Optional[str], float]:
        """
        Generate a response using learned n-grams.
        
        Args:
            doc: spaCy Doc object
            conversation_id: The conversation ID
            mode: The bot mode
            
        Returns:
            Tuple of (response_text, confidence)
        """
        # Get tokens from input
        input_tokens = [token.text.lower() for token in doc if not token.is_punct and not token.is_space]
        
        # Find n-grams that contain at least one of the input words
        patterns = []
        for token in input_tokens:
            # Use SQL LIKE to find n-grams containing this token
            found = self.SpeechPattern.query.filter(
                self.SpeechPattern.conversation_id == conversation_id,
                self.SpeechPattern.pattern_type.like("%-gram"),
                self.SpeechPattern.pattern.like(f"%{token}%"),
                self.SpeechPattern.mode == mode
            ).order_by(self.SpeechPattern.frequency.desc()).limit(5).all()
            
            patterns.extend(found)
        
        if not patterns:
            return None, 0.0
            
        # Choose an n-gram weighted by frequency
        import random
        ngram_options = []
        for pattern in patterns:
            ngram_options.extend([pattern] * pattern.frequency)
            
        if not ngram_options:
            return None, 0.0
            
        chosen_pattern = random.choice(ngram_options)
        
        # Use the n-gram or its example as response
        response = chosen_pattern.example or chosen_pattern.pattern
        
        # Calculate confidence
        confidence = 0.1 + min(0.5, 0.1 * chosen_pattern.frequency)
        
        return response, confidence
    
    def _longest_common_subsequence(self, seq1: List[str], seq2: List[str]) -> int:
        """
        Find the length of the longest common subsequence between two sequences.
        
        Args:
            seq1: First sequence
            seq2: Second sequence
            
        Returns:
            Length of longest common subsequence
        """
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]