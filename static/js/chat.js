/**
 * Main chat functionality for MirrorBot interface
 */

// DOM elements
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const modeSelect = document.getElementById('mode-select');
const typingIndicator = document.createElement('div');

// Set up typing indicator
typingIndicator.className = 'typing-indicator';
typingIndicator.innerHTML = 'MirrorBot is thinking <span></span><span></span><span></span>';
typingIndicator.style.display = 'none';

// Bot mode icons
const modeIcons = {
    'advanced_imitation': 'fas fa-graduation-cap',
    'imitation': 'fas fa-clone',
    'literal': 'fas fa-book',
    'echo': 'fas fa-bullhorn',
    'overunderstanding': 'fas fa-brain',
    'nonsense': 'fas fa-random'
};

// Emotion icons for visualization
const emotionIcons = {
    'happy': 'fa-smile',
    'sad': 'fa-sad-tear',
    'angry': 'fa-angry',
    'afraid': 'fa-grimace',
    'surprised': 'fa-surprise',
    'neutral': 'fa-meh'
};

// Emotion colors for styling
const emotionColors = {
    'happy': '#4BBF73',     // Green
    'sad': '#5091CD',       // Blue
    'angry': '#D9534F',     // Red
    'afraid': '#EFAD4D',    // Yellow/Gold
    'surprised': '#9B59B6', // Purple
    'neutral': '#6C757D'    // Gray
};

// Initialize chat
document.addEventListener('DOMContentLoaded', () => {
    loadChatHistory();
    
    // Set up event listeners
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    sendButton.addEventListener('click', sendMessage);
    
    modeSelect.addEventListener('change', changeMode);
});

/**
 * Send user message to the bot and get response
 */
function sendMessage() {
    const message = userInput.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat('user', message);
    
    // Clear input
    userInput.value = '';
    
    // Show typing indicator
    chatContainer.appendChild(typingIndicator);
    typingIndicator.style.display = 'inline-flex';
    
    // Scroll to bottom
    scrollToBottom();
    
    // Send to server
    fetch('/api/message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Remove typing indicator
        if (typingIndicator.parentNode === chatContainer) {
            chatContainer.removeChild(typingIndicator);
        }
        
        // Add bot response
        if (data.error) {
            addMessageToChat('bot', 'Sorry, I encountered an error processing your message.');
        } else {
            addMessageToChat('bot', data.response);
            
            // Update learning stats
            updateLearningStats();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        
        // Remove typing indicator
        if (typingIndicator.parentNode === chatContainer) {
            chatContainer.removeChild(typingIndicator);
        }
        
        addMessageToChat('bot', 'Sorry, there was an error communicating with the server.');
    });
}

/**
 * Add a message to the chat display
 * @param {string} sender - 'user' or 'bot'
 * @param {string} content - Message content
 */
function addMessageToChat(sender, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message fade-in`;
    
    // Add current mode class for styling
    const currentMode = modeSelect.value;
    messageDiv.classList.add(`mode-${currentMode}`);
    
    // For bot messages: add icon and speak text if voice output is enabled
    if (sender === 'bot') {
        const modeIcon = modeIcons[currentMode] || 'fas fa-robot';
        
        // Add voice button for bot messages
        const speakButton = document.createElement('button');
        speakButton.className = 'speak-button';
        speakButton.innerHTML = '<i class="fas fa-volume-up"></i>';
        speakButton.title = 'Speak this message';
        speakButton.onclick = function() {
            if (window.speakText) {
                window.speakText(content);
            }
        };
        
        messageDiv.innerHTML = `<i class="${modeIcon}"></i> ${content}`;
        messageDiv.appendChild(speakButton);
        
        // Auto-speak if voice output is enabled
        if (window.speakText && document.getElementById('voice-output-toggle')?.checked) {
            window.speakText(content);
        }
    } else {
        messageDiv.textContent = content;
    }
    
    chatContainer.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Scroll chat container to the bottom
 */
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Change the bot's personality mode
 */
function changeMode() {
    const newMode = modeSelect.value;
    
    // Notify server of mode change
    fetch('/api/change-mode', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ mode: newMode })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Add system message about mode change
            const messageDiv = document.createElement('div');
            messageDiv.className = 'text-center my-3 fade-in';
            messageDiv.innerHTML = `<small class="text-muted"><i class="${modeIcons[newMode]}"></i> Switched to ${getModeDisplayName(newMode)}</small>`;
            chatContainer.appendChild(messageDiv);
            scrollToBottom();
            
            // Update mode indicator in UI
            updateModeIndicator(newMode);
        }
    })
    .catch(error => {
        console.error('Error changing mode:', error);
    });
}

/**
 * Update the mode indicator in the UI
 * @param {string} mode - The bot mode
 */
function updateModeIndicator(mode) {
    const modeIndicator = document.getElementById('mode-indicator');
    if (modeIndicator) {
        const icon = modeIcons[mode] || 'fas fa-robot';
        modeIndicator.innerHTML = `<i class="${icon}"></i> ${getModeDisplayName(mode)}`;
    }
}

/**
 * Get display name for a bot mode
 * @param {string} mode - The bot mode
 * @returns {string} Display name
 */
function getModeDisplayName(mode) {
    const modeNames = {
        'imitation': 'Imitation Mode',
        'literal': 'Literal Mode',
        'echo': 'Echo Mode',
        'overunderstanding': 'Over-Understanding Mode',
        'nonsense': 'Nonsense Mode'
    };
    
    return modeNames[mode] || mode;
}

/**
 * Load chat history from the server
 */
function loadChatHistory() {
    fetch('/api/chat-history')
    .then(response => response.json())
    .then(data => {
        if (data.history && data.history.length > 0) {
            // Clear chat container first
            chatContainer.innerHTML = '';
            
            // Add messages to chat
            data.history.forEach(msg => {
                addMessageToChat(msg.sender, msg.content);
            });
        } else {
            // Add welcome message for new conversations
            addMessageToChat('bot', 'Welcome to MirrorBot! I learn from our interactions. Try talking to me in different modes to see how I respond.');
        }
    })
    .catch(error => {
        console.error('Error loading chat history:', error);
        addMessageToChat('bot', 'Welcome to MirrorBot! I learn from our interactions. Try talking to me in different modes to see how I respond.');
    });
}
