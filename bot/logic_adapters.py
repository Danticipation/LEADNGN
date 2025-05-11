"""
Custom logic adapters for different Mirror Bot personality modes
"""
import re
import random
import logging
import spacy
import string
from .logic_adapter_base import LogicAdapter
from .conversation import Statement
from .comparisons import LevenshteinDistance

# Configure logger
logger = logging.getLogger(__name__)

# Load spaCy model for text processing
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("Spacy model not found, using blank model")
    nlp = spacy.blank("en")

class ImitationLogicAdapter(LogicAdapter):
    """
    Imitation mode: Gradually learns to repeat phrases the user teaches it.
    The more a phrase is repeated, the more likely the bot will respond with it.
    """
    
    def __init__(self, chatbot, **kwargs):
        super().__init__(chatbot, **kwargs)
        self.confidence_threshold = kwargs.get('confidence_threshold', 0.65)
        self.levenshtein = LevenshteinDistance(language=self.language)
    
    def can_process(self, statement):
        return True
    
    def process(self, statement, additional_response_selection_parameters=None):
        """
        Return a response based on learned patterns, with higher confidence
        for frequently seen statements.
        """
        additional_response_selection_parameters = additional_response_selection_parameters or {}
        conversation_id = additional_response_selection_parameters.get('conversation_id', 'default')
        
        # Get all statements that share significant words
        input_words = set(self._get_significant_words(statement.text))
        if not input_words:
            # Empty or only stopwords, use default response
            response = Statement(text="I'm learning to imitate your speech patterns.")
            response.confidence = 0.1
            return response
            
        # Check if we've seen similar statements before
        stored_statements = self.chatbot.storage.filter()
        
        best_match = None
        best_similarity = 0
        
        for stored_statement in stored_statements:
            similarity = self.levenshtein.compare(statement, stored_statement)
            
            # Get the response associated with this statement
            responses = list(self.chatbot.storage.filter(
                in_response_to=stored_statement.text
            ))
            
            # Skip if no responses
            if not responses:
                continue
                
            # If this is a good match and has responses
            if similarity > best_similarity and responses:
                best_similarity = similarity
                # Choose a response based on frequency in the database
                best_match = self._select_response(responses)
                
        # If we found a good match
        if best_match and best_similarity > self.confidence_threshold:
            confidence = best_similarity
            self._learn_statement(statement.text, conversation_id)
            return Statement(
                text=best_match.text,
                in_response_to=statement.text,
                confidence=confidence
            )
            
        # Try exact word matching for new vocabulary
        response = Statement(
            text=f"I hear you saying '{statement.text}'. I'm still learning.",
            in_response_to=statement.text
        )
        response.confidence = 0.3
        
        # Learn this statement
        self._learn_statement(statement.text, conversation_id)
        
        return response
    
    def _select_response(self, responses):
        """Select a response based on how frequently it appears"""
        if not responses:
            return None
            
        # Count frequencies
        response_counts = {}
        for response in responses:
            if response.text in response_counts:
                response_counts[response.text] += 1
            else:
                response_counts[response.text] = 1
                
        # Choose weighted by frequency
        options = []
        for response in responses:
            # Add this response to options list multiple times based on its frequency
            weight = response_counts[response.text]
            options.extend([response] * weight)
            
        return random.choice(options) if options else responses[0]
    
    def _get_significant_words(self, text):
        """Extract significant words from text (non-stopwords)"""
        doc = nlp(text.lower())
        return [token.text for token in doc if not token.is_stop and not token.is_punct]
    
    def _learn_statement(self, text, conversation_id):
        """Learn words from a statement by adding to vocabulary database"""
        # Import here to avoid circular imports
        from app import db
        from models import BotVocabulary
        
        doc = nlp(text.lower())
        for token in doc:
            if token.is_stop or token.is_punct:
                continue
                
            # Check if word exists in vocabulary
            word = token.text.strip()
            if not word:
                continue
                
            existing = BotVocabulary.query.filter_by(
                conversation_id=conversation_id,
                word=word,
                mode='imitation'
            ).first()
            
            if existing:
                existing.frequency += 1
            else:
                vocab = BotVocabulary(
                    conversation_id=conversation_id,
                    word=word,
                    frequency=1,
                    mode='imitation'
                )
                db.session.add(vocab)
                
        db.session.commit()


class LiteralLogicAdapter(LogicAdapter):
    """
    Literal Mode: Takes everything at face value without context
    """
    
    def __init__(self, chatbot, **kwargs):
        super().__init__(chatbot, **kwargs)
        self.confidence_threshold = kwargs.get('confidence_threshold', 0.4)
    
    def can_process(self, statement):
        return True
    
    def process(self, statement, additional_response_selection_parameters=None):
        """
        Process an input statement and return a literal interpretation.
        """
        additional_response_selection_parameters = additional_response_selection_parameters or {}
        conversation_id = additional_response_selection_parameters.get('conversation_id', 'default')
        
        # Parse the input with spaCy
        doc = nlp(statement.text)
        
        # Generate a literal interpretation
        response_text = self._generate_literal_response(doc)
        
        # Learn vocabulary
        self._learn_statement(statement.text, conversation_id)
        
        # Create response statement
        response = Statement(
            text=response_text,
            in_response_to=statement.text
        )
        
        # Set confidence - higher for questions and commands
        if "?" in statement.text:
            response.confidence = 0.9
        elif "!" in statement.text:
            response.confidence = 0.85
        else:
            response.confidence = 0.75
        
        return response
    
    def _generate_literal_response(self, doc):
        """Generate a literal interpretation of the input"""
        # Check for questions (who, what, when, where, why, how)
        question_words = ["who", "what", "when", "where", "why", "how"]
        
        # Treat questions literally
        if doc[0].text.lower() in question_words:
            return self._respond_to_question(doc)
        
        # Check for commands (verbs at the beginning)
        if doc[0].pos_ == "VERB":
            return f"You are telling me to {doc[0].text.lower()}. I am acknowledging this instruction."
        
        # Default literal response
        return f"I understand you have said '{doc.text}' and I am taking that statement literally."
    
    def _respond_to_question(self, doc):
        """Generate literal responses to questions"""
        question_type = doc[0].text.lower()
        
        responses = {
            "who": "You are asking about a person. I acknowledge your question about identity.",
            "what": "You are asking about a thing or concept. I acknowledge your request for information.",
            "when": "You are asking about a time. I acknowledge your question about timing.",
            "where": "You are asking about a location. I acknowledge your question about place.",
            "why": "You are asking for a reason. I acknowledge your question about causation.",
            "how": "You are asking about a method or process. I acknowledge your question about methodology."
        }
        
        return responses.get(question_type, f"You are asking a question that begins with '{question_type}'.")
    
    def _learn_statement(self, text, conversation_id):
        """Learn words from a statement by adding to vocabulary database"""
        # Import here to avoid circular imports
        from app import db
        from models import BotVocabulary
        
        doc = nlp(text.lower())
        for token in doc:
            if token.is_stop or token.is_punct:
                continue
                
            # Check if word exists in vocabulary
            word = token.text.strip()
            if not word:
                continue
                
            existing = BotVocabulary.query.filter_by(
                conversation_id=conversation_id,
                word=word,
                mode='literal'
            ).first()
            
            if existing:
                existing.frequency += 1
            else:
                vocab = BotVocabulary(
                    conversation_id=conversation_id,
                    word=word,
                    frequency=1,
                    mode='literal'
                )
                db.session.add(vocab)
                
        db.session.commit()


class EchoLogicAdapter(LogicAdapter):
    """
    Echo Mode: Repeats with random word substitutions
    """
    
    def __init__(self, chatbot, **kwargs):
        super().__init__(chatbot, **kwargs)
        self.substitution_chance = kwargs.get('substitution_chance', 0.3)
        
        # Parts of speech to potentially substitute
        self.replaceable_pos = ['NOUN', 'VERB', 'ADJ', 'ADV']
        
        # Build vocabulary from existing statements
        self.vocabulary = self._build_initial_vocabulary()
    
    def can_process(self, statement):
        return True
    
    def process(self, statement, additional_response_selection_parameters=None):
        """
        Process the input statement and return an echo with substitutions
        """
        additional_response_selection_parameters = additional_response_selection_parameters or {}
        conversation_id = additional_response_selection_parameters.get('conversation_id', 'default')
        
        # Parse input with spaCy
        doc = nlp(statement.text)
        
        # Create echo with substitutions
        response_text = self._create_echo_with_substitutions(doc)
        
        # Learn vocabulary
        self._learn_statement(statement.text, conversation_id)
        
        # Create response
        response = Statement(
            text=response_text,
            in_response_to=statement.text
        )
        
        response.confidence = 0.85  # Echo mode has high confidence
        return response
    
    def _build_initial_vocabulary(self):
        """Build initial vocabulary from existing statements"""
        vocabulary = {pos: set() for pos in self.replaceable_pos}
        
        # Get all statements from storage
        statements = self.chatbot.storage.filter()
        
        for statement in statements:
            doc = nlp(statement.text)
            for token in doc:
                if token.pos_ in self.replaceable_pos:
                    vocabulary[token.pos_].add(token.text.lower())
        
        # Add some fallback words if vocabulary is empty
        fallbacks = {
            'NOUN': ['thing', 'item', 'object', 'person', 'place'],
            'VERB': ['do', 'make', 'go', 'say', 'think'],
            'ADJ': ['good', 'bad', 'big', 'small', 'interesting'],
            'ADV': ['really', 'very', 'quite', 'almost', 'nearly']
        }
        
        for pos, words in fallbacks.items():
            if not vocabulary[pos]:
                vocabulary[pos].update(words)
        
        return vocabulary
    
    def _create_echo_with_substitutions(self, doc):
        """Create an echo of the input with some words substituted"""
        result = []
        
        for token in doc:
            # Decide whether to substitute this token
            if (token.pos_ in self.replaceable_pos and 
                random.random() < self.substitution_chance and 
                len(self.vocabulary[token.pos_]) > 0):
                
                # Get substitution words for this part of speech
                substitutes = list(self.vocabulary[token.pos_])
                if not substitutes:
                    result.append(token.text)
                    continue
                
                # Choose a random substitute
                substitute = random.choice(substitutes)
                
                # Match capitalization
                if token.text[0].isupper():
                    substitute = substitute.capitalize()
                
                result.append(substitute)
            else:
                result.append(token.text)
                
                # Update vocabulary with this word
                if token.pos_ in self.replaceable_pos:
                    self.vocabulary[token.pos_].add(token.text.lower())
        
        # Recreate spacing based on original tokens
        text = ""
        for i, token in enumerate(doc):
            if i > 0 and not (doc[i-1].text in string.punctuation or token.text in string.punctuation):
                text += " "
            text += result[i]
        
        return text
    
    def _learn_statement(self, text, conversation_id):
        """Learn words from a statement by adding to vocabulary database"""
        # Import here to avoid circular imports
        from app import db
        from models import BotVocabulary
        
        doc = nlp(text.lower())
        for token in doc:
            if token.is_stop or token.is_punct:
                continue
                
            # Check if word exists in vocabulary
            word = token.text.strip()
            if not word:
                continue
                
            existing = BotVocabulary.query.filter_by(
                conversation_id=conversation_id,
                word=word,
                mode='echo'
            ).first()
            
            if existing:
                existing.frequency += 1
            else:
                vocab = BotVocabulary(
                    conversation_id=conversation_id,
                    word=word,
                    frequency=1,
                    mode='echo'
                )
                db.session.add(vocab)
                
        db.session.commit()


class OverUnderstandingLogicAdapter(LogicAdapter):
    """
    Over-Understanding Mode: Exaggerates responses and concepts
    """
    
    def __init__(self, chatbot, **kwargs):
        super().__init__(chatbot, **kwargs)
        
        # Intensifiers to add to responses
        self.intensifiers = [
            "absolutely", "completely", "totally", "utterly", "entirely",
            "extremely", "incredibly", "immensely", "tremendously", "vastly",
            "profoundly", "deeply", "thoroughly", "overwhelmingly", "immeasurably"
        ]
        
        # Exaggeration phrases
        self.exaggerations = [
            "That's the most {} thing I've ever heard!",
            "I'm {} blown away by what you just said!",
            "That's {} mind-blowing!",
            "I'm {} amazed by your insight!",
            "That's {} revolutionary!",
            "I've {} never considered such a profound perspective!",
            "Your words are {} life-changing!",
            "That's the {} deepest concept I've encountered!",
            "I'm {} transformed by your wisdom!",
            "That's {} changed everything I thought I knew!"
        ]
    
    def can_process(self, statement):
        return True
    
    def process(self, statement, additional_response_selection_parameters=None):
        """
        Process the input statement and return an over-exaggerated response
        """
        additional_response_selection_parameters = additional_response_selection_parameters or {}
        conversation_id = additional_response_selection_parameters.get('conversation_id', 'default')
        
        # Parse input with spaCy
        doc = nlp(statement.text)
        
        # Extract key concepts
        key_concepts = self._extract_key_concepts(doc)
        
        # Generate exaggerated response
        response_text = self._generate_exaggerated_response(key_concepts, statement.text)
        
        # Learn vocabulary
        self._learn_statement(statement.text, conversation_id)
        
        # Create response
        response = Statement(
            text=response_text,
            in_response_to=statement.text
        )
        
        response.confidence = 0.8
        return response
    
    def _extract_key_concepts(self, doc):
        """Extract key concepts (nouns, verbs, etc.) from the input"""
        concepts = []
        
        for token in doc:
            # Focus on content words (nouns, verbs, adjectives)
            if token.pos_ in ['NOUN', 'VERB', 'ADJ'] and not token.is_stop:
                concepts.append(token.text.lower())
        
        return concepts if concepts else ["idea"]  # Fallback
    
    def _generate_exaggerated_response(self, key_concepts, original_text):
        """Generate an exaggerated response based on key concepts"""
        # Choose response type
        response_type = random.choice(["echo", "concept", "emotional", "philosophical"])
        
        if response_type == "echo":
            # Echo with exaggeration
            intensifier = random.choice(self.intensifiers)
            return f"{intensifier.capitalize()} YES! '{original_text}' is such a profound observation!"
            
        elif response_type == "concept" and key_concepts:
            # Focus on a key concept
            concept = random.choice(key_concepts)
            intensifier = random.choice(self.intensifiers)
            templates = [
                f"The way you mentioned '{concept}' is {intensifier} revolutionary!",
                f"I'm {intensifier} fascinated by your perspective on '{concept}'!",
                f"Your insight about '{concept}' is {intensifier} mind-expanding!",
                f"I've never heard anyone express '{concept}' in such an {intensifier} brilliant way!"
            ]
            return random.choice(templates)
            
        elif response_type == "emotional":
            # Emotional overreaction
            intensifier = random.choice(self.intensifiers)
            exaggeration = random.choice(self.exaggerations).format(intensifier)
            return exaggeration
            
        else:  # philosophical
            # Add philosophical depth
            intensifier = random.choice(self.intensifiers)
            templates = [
                f"I'm {intensifier} moved by the depth of what you're conveying. It speaks to the very nature of existence!",
                f"What you're saying has {intensifier} profound implications for how we understand reality itself!",
                f"That's {intensifier} transformative - it reframes everything I thought I knew about human experience!",
                f"I'm {intensifier} struck by how your words transcend ordinary conversation and touch the sublime!"
            ]
            return random.choice(templates)
    
    def _learn_statement(self, text, conversation_id):
        """Learn words from a statement by adding to vocabulary database"""
        # Import here to avoid circular imports
        from app import db
        from models import BotVocabulary
        
        doc = nlp(text.lower())
        for token in doc:
            if token.is_stop or token.is_punct:
                continue
                
            # Check if word exists in vocabulary
            word = token.text.strip()
            if not word:
                continue
                
            existing = BotVocabulary.query.filter_by(
                conversation_id=conversation_id,
                word=word,
                mode='overunderstanding'
            ).first()
            
            if existing:
                existing.frequency += 1
            else:
                vocab = BotVocabulary(
                    conversation_id=conversation_id,
                    word=word,
                    frequency=1,
                    mode='overunderstanding'
                )
                db.session.add(vocab)
                
        db.session.commit()


class NonsenseLogicAdapter(LogicAdapter):
    """
    Nonsense Mode: Occasionally inserts random phrases
    """
    
    def __init__(self, chatbot, **kwargs):
        super().__init__(chatbot, **kwargs)
        
        # Collection of nonsensical phrases
        self.nonsense_phrases = [
            "Blue penguins drink starlight tea at midnight.",
            "Doorknobs whisper secrets to passing clouds.",
            "Triangular dreams dissolve in butter sometimes.",
            "The dancing calculator forgot its umbrella again.",
            "Fuzzy concepts marinate in alphabet soup.",
            "Yesterday's tomorrow never showed up for breakfast.",
            "Silent whispers echo loudly through paper walls.",
            "Square circles argue with cylindrical triangles.",
            "Invisible ink reveals hidden transparency.",
            "Diagonal thinking solves vertical problems.",
            "Floating ideas sink under their own buoyancy.",
            "The concept of Tuesday melted in August heat.",
            "Quantum butterflies cause time hurricanes.",
            "Sideways elevators only move backwards.",
            "Transparent shadows cast colorful darkness."
        ]
        
        # Transition phrases to connect random nonsense
        self.transitions = [
            "Speaking of which, ",
            "That reminds me, ",
            "On a related note, ",
            "Interestingly, ",
            "By the way, ",
            "Did you know? ",
            "I just remembered that ",
            "This may seem random, but ",
            "Changing topics slightly, ",
            "This is important: "
        ]
        
        # Chance of including nonsense (30%)
        self.nonsense_chance = 0.3
    
    def can_process(self, statement):
        return True
    
    def process(self, statement, additional_response_selection_parameters=None):
        """
        Process the input statement and potentially add nonsensical content
        """
        additional_response_selection_parameters = additional_response_selection_parameters or {}
        conversation_id = additional_response_selection_parameters.get('conversation_id', 'default')
        
        # First, create a somewhat normal response
        response_text = self._create_semi_coherent_response(statement.text)
        
        # Decide whether to add nonsense
        if random.random() < self.nonsense_chance:
            # Add a nonsensical phrase
            transition = random.choice(self.transitions)
            nonsense = random.choice(self.nonsense_phrases)
            response_text = f"{response_text} {transition}{nonsense}"
        
        # Learn vocabulary
        self._learn_statement(statement.text, conversation_id)
        
        # Create response
        response = Statement(
            text=response_text,
            in_response_to=statement.text
        )
        
        response.confidence = 0.75
        return response
    
    def _create_semi_coherent_response(self, input_text):
        """Create a response that's somewhat related to input but may drift"""
        # Parse input to extract some keywords
        doc = nlp(input_text)
        
        # Extract content words
        content_words = [token.text for token in doc 
                         if not token.is_stop and not token.is_punct]
        
        # If we found content words, use one in the response
        if content_words and random.random() < 0.7:
            keyword = random.choice(content_words)
            templates = [
                f"You mentioned '{keyword}', which might relate to quantum mechanics or possibly cheese.",
                f"'{keyword}' makes me think of underwater basket weaving and temporal paradoxes.",
                f"The concept of '{keyword}' reminds me of dancing keyboards and singing calculators.",
                f"When you say '{keyword}', I wonder if you mean literally or in the metaphysical sense of banana peels.",
                f"'{keyword}' is fascinating from both astronomical and entomological perspectives.",
            ]
            return random.choice(templates)
        
        # Otherwise, give a generic but somewhat odd response
        generic_responses = [
            "I hear what you're saying, although it might be in a different dimension.",
            "Your words are like puzzle pieces from different puzzles trying to fit together.",
            "That's an interesting perspective, especially if viewed through kaleidoscope glasses.",
            "I'm processing your input through my randomly connected neural pathways.",
            "What you're saying makes both perfect sense and no sense simultaneously.",
            "I understand completely, though my understanding may exist in a parallel universe.",
            "Your statement exists in a quantum superposition of clarity and confusion.",
            "I'm interpreting your words through a filter of abstract expressionism.",
            "Your communication patterns suggest both order and chaos, like jazz improvisation.",
            "I'm following your train of thought, even as it derails spectacularly."
        ]
        
        return random.choice(generic_responses)
    
    def _learn_statement(self, text, conversation_id):
        """Learn words from a statement by adding to vocabulary database"""
        # Import here to avoid circular imports
        from app import db
        from models import BotVocabulary
        
        doc = nlp(text.lower())
        for token in doc:
            if token.is_stop or token.is_punct:
                continue
                
            # Check if word exists in vocabulary
            word = token.text.strip()
            if not word:
                continue
                
            existing = BotVocabulary.query.filter_by(
                conversation_id=conversation_id,
                word=word,
                mode='nonsense'
            ).first()
            
            if existing:
                existing.frequency += 1
            else:
                vocab = BotVocabulary(
                    conversation_id=conversation_id,
                    word=word,
                    frequency=1,
                    mode='nonsense'
                )
                db.session.add(vocab)
                
        db.session.commit()
