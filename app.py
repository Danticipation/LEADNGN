import os
import logging
from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///mirrorbot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import bot logic after app is created to avoid circular imports
from bot import create_bot, get_bot_modes, get_bot_stats

# Import models after db is initialized
with app.app_context():
    from models import Message, BotVocabulary
    db.create_all()

# Routes
@app.route('/')
def index():
    """Render the main chat interface"""
    # Generate a session ID if one doesn't exist
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session['bot_mode'] = 'imitation'
    
    return render_template('index.html', 
                           bot_modes=get_bot_modes(),
                           current_mode=session.get('bot_mode', 'imitation'))

@app.route('/api/message', methods=['POST'])
def message():
    """Handle incoming user messages and return bot responses"""
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
    
    user_message = data['message']
    conversation_id = session.get('session_id')
    bot_mode = session.get('bot_mode', 'imitation')
    
    try:
        # Process emotions in the user message
        from bot.emotion_manager import EmotionManager
        from bot.sentiment_analyzer import analyze_sentiment, add_emotional_style
        from bot.context_manager import ContextManager
        
        # Analyze emotion in the user message
        emotion_manager = EmotionManager()
        emotion_data = analyze_sentiment(user_message)
        
        # Initialize context manager
        context_manager = ContextManager()
        
        # Check if this is a question that can be answered from context
        question_answer = None
        if any(word in user_message.lower() for word in ['what', 'who', 'when', 'where', 'why', 'how', 'do you remember', 'did i', 'have i']):
            question_answer = context_manager.answer_question_from_context(user_message, conversation_id)
        
        # Get bot response using the appropriate bot mode
        bot = create_bot(mode=bot_mode)
        
        # If we have a direct answer to the question, use it, otherwise get normal response
        if question_answer:
            bot_response_text = question_answer
            # Create a mock response object for consistency
            class MockResponse:
                def __init__(self, text):
                    self.text = text
                    self.confidence = 0.9
                def __str__(self):
                    return self.text
            bot_response = MockResponse(bot_response_text)
        else:
            bot_response = bot.get_response(
                user_message,
                additional_response_selection_parameters={
                    'conversation_id': conversation_id,
                    'emotion_data': emotion_data  # Pass emotion data to the bot
                }
            )
        
        # Save messages to database
        with app.app_context():
            # Save user message
            user_msg = Message()
            user_msg.conversation_id = conversation_id
            user_msg.sender = 'user'
            user_msg.content = user_message
            user_msg.mode = bot_mode
            
            db.session.add(user_msg)
            db.session.flush()  # Flush to get the ID without committing
            
            # Track emotion for the user message
            emotion_manager.track_emotion(
                user_message, 
                conversation_id, 
                user_msg.id, 
                bot_mode
            )
            
            # Save bot response
            bot_msg = Message()
            bot_msg.conversation_id = conversation_id
            bot_msg.sender = 'bot'
            bot_msg.content = str(bot_response)
            bot_msg.mode = bot_mode
            
            db.session.add(bot_msg)
            db.session.commit()
        
        # Update conversation context with the new messages
        context_manager.update_conversation_context(
            user_message, 
            str(bot_response), 
            conversation_id, 
            bot_mode
        )
        
        # Add emotion styling to response in certain cases
        response_text = str(bot_response)
        
        # Determine if we should reflect the user's emotion (50% chance)
        import random
        if random.random() < 0.5 and emotion_data['primary_emotion'] != 'neutral':
            # Apply emotional styling to response text
            styled_response = add_emotional_style(
                response_text, 
                emotion_data['primary_emotion'], 
                emotion_data['intensity']
            )
            
            # Only use the styled response if it's different
            if styled_response != response_text:
                response_text = styled_response
        
        return jsonify({
            'response': response_text,
            'confidence': bot_response.confidence if hasattr(bot_response, 'confidence') else 0,
            'emotion': {
                'detected': emotion_data['primary_emotion'],
                'confidence': emotion_data['confidence'],
                'intensity': emotion_data['intensity']
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({'error': 'An error occurred processing your message'}), 500

@app.route('/api/change-mode', methods=['POST'])
def change_mode():
    """Change the bot's personality mode"""
    data = request.get_json()
    
    if not data or 'mode' not in data:
        return jsonify({'error': 'No mode provided'}), 400
    
    mode = data['mode']
    
    # Validate the mode
    if mode not in get_bot_modes():
        return jsonify({'error': 'Invalid mode'}), 400
    
    # Set the new mode in the session
    session['bot_mode'] = mode
    
    return jsonify({'success': True, 'mode': mode})

@app.route('/api/chat-history', methods=['GET'])
def chat_history():
    """Get the chat history for the current session"""
    conversation_id = session.get('session_id')
    
    if not conversation_id:
        return jsonify({'history': []})
    
    try:
        with app.app_context():
            messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
            history = [{'sender': msg.sender, 'content': msg.content, 'timestamp': msg.timestamp.isoformat()} 
                      for msg in messages]
            return jsonify({'history': history})
    
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        return jsonify({'error': 'An error occurred retrieving chat history'}), 500

@app.route('/memory')
def memory_page():
    """Render the memory view page"""
    # Initialize session if not already done
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session['bot_mode'] = 'imitation'
    
    return render_template('memory.html', 
                           bot_modes=get_bot_modes(),
                           current_mode=session.get('bot_mode', 'imitation'))

@app.route('/api/learning-stats', methods=['GET'])
def learning_stats():
    """Get learning statistics for the bot"""
    conversation_id = session.get('session_id')
    
    if not conversation_id:
        return jsonify({'vocabulary': [], 'total': 0})
    
    try:
        # Get basic stats from bot
        stats = get_bot_stats(conversation_id)
        
        # Add advanced learning pattern stats
        from models import SpeechPattern, PhraseTemplate, MemoryFact
        
        # Count patterns by type
        pattern_counts = {}
        patterns = db.session.query(
            SpeechPattern.pattern_type, 
            db.func.count(SpeechPattern.id)
        ).filter_by(
            conversation_id=conversation_id
        ).group_by(SpeechPattern.pattern_type).all()
        
        for pattern_type, count in patterns:
            pattern_counts[pattern_type] = count
            
        # Count phrase templates
        template_count = PhraseTemplate.query.filter_by(
            conversation_id=conversation_id
        ).count()
        
        # Get a few examples of each pattern type
        pattern_examples = {}
        for pattern_type in pattern_counts.keys():
            examples = SpeechPattern.query.filter_by(
                conversation_id=conversation_id,
                pattern_type=pattern_type
            ).order_by(SpeechPattern.frequency.desc()).limit(3).all()
            
            pattern_examples[pattern_type] = [
                {
                    "pattern": example.pattern,
                    "frequency": example.frequency
                }
                for example in examples
            ]
            
        # Add to stats
        stats['advanced_patterns'] = {
            'counts': pattern_counts,
            'examples': pattern_examples,
            'template_count': template_count
        }
        
        # Add memory facts
        facts = MemoryFact.query.filter_by(
            conversation_id=conversation_id
        ).order_by(MemoryFact.priority.desc(), MemoryFact.mentioned_count.desc()).limit(10).all()
        
        memory_facts = []
        for fact in facts:
            memory_facts.append({
                'subject': fact.subject,
                'fact': fact.fact,
                'confidence': fact.confidence,
                'mentioned_count': fact.mentioned_count,
                'updated_at': fact.updated_at.isoformat() if fact.updated_at else None
            })
        
        stats['memory_facts'] = memory_facts
        
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Error retrieving learning stats: {str(e)}")
        return jsonify({'error': 'An error occurred retrieving learning stats'}), 500

@app.route('/api/emotion-stats', methods=['GET'])
def emotion_stats():
    """Get emotion statistics and data for the bot"""
    conversation_id = session.get('session_id')
    
    if not conversation_id:
        return jsonify({'recent_emotions': [], 'emotion_distribution': {}})
    
    try:
        from models import EmotionTracker
        from bot.emotion_manager import EmotionManager
        
        emotion_manager = EmotionManager()
        
        # Get recent emotions
        recent_emotions = EmotionTracker.query.filter_by(
            conversation_id=conversation_id
        ).order_by(EmotionTracker.created_at.desc()).limit(10).all()
        
        recent_emotions_data = []
        for emotion in recent_emotions:
            recent_emotions_data.append({
                'primary_emotion': emotion.primary_emotion,
                'confidence': emotion.confidence,
                'intensity': emotion.intensity,
                'text_sample': emotion.text_sample,
                'created_at': emotion.created_at.isoformat() if emotion.created_at else None
            })
        
        # Count emotions by type for distribution
        emotion_distribution = {}
        emotion_counts = db.session.query(
            EmotionTracker.primary_emotion, 
            db.func.count(EmotionTracker.id)
        ).filter_by(
            conversation_id=conversation_id
        ).group_by(EmotionTracker.primary_emotion).all()
        
        for emotion, count in emotion_counts:
            emotion_distribution[emotion] = count
        
        # Get emotion timeline
        emotion_timeline = emotion_manager.get_emotion_timeline(conversation_id)
        
        # Get emotional patterns
        emotional_patterns = emotion_manager.analyze_emotional_patterns(conversation_id)
        
        # Combine all emotion stats
        stats = {
            'recent_emotions': recent_emotions_data,
            'emotion_distribution': emotion_distribution,
            'emotion_timeline': emotion_timeline,
            'emotional_patterns': emotional_patterns
        }
        
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Error retrieving emotion stats: {str(e)}")
        return jsonify({'error': 'An error occurred retrieving emotion stats'}), 500

@app.route('/api/conversation-summary', methods=['GET'])
def conversation_summary():
    """Get a summary of the current conversation"""
    conversation_id = session.get('session_id')
    
    if not conversation_id:
        return jsonify({'summary': 'No conversation available to summarize.'})
    
    try:
        from bot.context_manager import ContextManager
        
        context_manager = ContextManager()
        summary_data = context_manager.summarize_conversation(conversation_id)
        
        return jsonify(summary_data)
    
    except Exception as e:
        logger.error(f"Error generating conversation summary: {str(e)}")
        return jsonify({'error': 'An error occurred generating the summary'}), 500

@app.route('/api/conversation-context', methods=['GET'])
def conversation_context():
    """Get recent conversation context and topics"""
    conversation_id = session.get('session_id')
    
    if not conversation_id:
        return jsonify({'recent_topics': [], 'recent_keywords': []})
    
    try:
        from bot.context_manager import ContextManager
        
        context_manager = ContextManager()
        context_data = context_manager.get_conversation_context(conversation_id)
        
        return jsonify(context_data)
    
    except Exception as e:
        logger.error(f"Error retrieving conversation context: {str(e)}")
        return jsonify({'error': 'An error occurred retrieving context'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
