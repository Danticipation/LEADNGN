/**
 * Voice input/output functionality for MirrorBot
 */

// DOM elements
const voiceInputButton = document.getElementById('voice-input-button');
const voiceOutputToggle = document.getElementById('voice-output-toggle');
const voiceStatus = document.getElementById('voice-status');

// Speech recognition setup
let recognition = null;
let isListening = false;

// Speech synthesis setup
const synth = window.speechSynthesis;
let voices = [];

// Check if browser supports speech recognition
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const SpeechGrammarList = window.SpeechGrammarList || window.webkitSpeechGrammarList;
const SpeechRecognitionEvent = window.SpeechRecognitionEvent || window.webkitSpeechRecognitionEvent;

// Initialize voice features
document.addEventListener('DOMContentLoaded', () => {
    initVoiceFeatures();
    
    // Load voice output preference from localStorage
    if (localStorage.getItem('voiceOutputEnabled') === 'true') {
        voiceOutputToggle.checked = true;
    }
    
    // Set up event listeners
    voiceInputButton.addEventListener('click', toggleVoiceInput);
    voiceOutputToggle.addEventListener('change', () => {
        localStorage.setItem('voiceOutputEnabled', voiceOutputToggle.checked);
    });
    
    // Populate available voices when they're loaded
    speechSynthesis.onvoiceschanged = loadVoices;
    loadVoices();
});

/**
 * Initialize voice recognition and synthesis features
 */
function initVoiceFeatures() {
    // Check if speech recognition is supported
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        
        // Set up recognition event handlers
        recognition.onresult = handleVoiceResult;
        recognition.onerror = handleVoiceError;
        recognition.onend = handleVoiceEnd;
        
        voiceInputButton.disabled = false;
        voiceStatus.textContent = 'Voice input ready';
    } else {
        // Speech recognition not supported
        voiceInputButton.disabled = true;
        voiceInputButton.classList.add('btn-secondary');
        voiceInputButton.classList.remove('btn-outline-secondary');
        voiceStatus.textContent = 'Voice input not supported in this browser';
    }
    
    // Check if speech synthesis is supported
    if (!synth) {
        voiceOutputToggle.disabled = true;
        document.querySelector('label[for="voice-output-toggle"]').textContent = 
            'Voice output not supported in this browser';
    }
}

/**
 * Toggle voice input on/off
 */
function toggleVoiceInput() {
    if (!recognition) return;
    
    if (isListening) {
        stopListening();
    } else {
        startListening();
    }
}

/**
 * Start listening for voice input
 */
function startListening() {
    if (!recognition) return;
    
    try {
        recognition.start();
        isListening = true;
        
        // Update UI
        voiceInputButton.classList.remove('btn-outline-secondary');
        voiceInputButton.classList.add('btn-danger');
        voiceInputButton.querySelector('i').classList.remove('fa-microphone');
        voiceInputButton.querySelector('i').classList.add('fa-stop');
        voiceStatus.textContent = 'Listening...';
    } catch (error) {
        console.error('Error starting voice recognition:', error);
    }
}

/**
 * Stop listening for voice input
 */
function stopListening() {
    if (!recognition) return;
    
    try {
        recognition.stop();
        isListening = false;
        
        // Update UI
        updateVoiceInputUI();
    } catch (error) {
        console.error('Error stopping voice recognition:', error);
    }
}

/**
 * Update the voice input UI to show not listening state
 */
function updateVoiceInputUI() {
    voiceInputButton.classList.add('btn-outline-secondary');
    voiceInputButton.classList.remove('btn-danger');
    voiceInputButton.querySelector('i').classList.add('fa-microphone');
    voiceInputButton.querySelector('i').classList.remove('fa-stop');
    voiceStatus.textContent = 'Voice input ready';
}

/**
 * Handle voice recognition results
 * @param {SpeechRecognitionEvent} event - The recognition event
 */
function handleVoiceResult(event) {
    const transcript = event.results[0][0].transcript;
    
    // Put the transcript in the input field
    document.getElementById('user-input').value = transcript;
    
    // Send the message
    sendMessage();
}

/**
 * Handle voice recognition errors
 * @param {SpeechRecognitionEvent} event - The error event
 */
function handleVoiceError(event) {
    console.error('Voice recognition error:', event.error);
    
    switch (event.error) {
        case 'no-speech':
            voiceStatus.textContent = 'No speech detected. Try again.';
            break;
        case 'audio-capture':
            voiceStatus.textContent = 'No microphone detected.';
            break;
        case 'not-allowed':
            voiceStatus.textContent = 'Microphone permission denied.';
            break;
        case 'network':
            voiceStatus.textContent = 'Voice input unavailable in this environment';
            // Disable voice input in environments where it doesn't work
            voiceInputButton.disabled = true;
            voiceInputButton.classList.add('btn-secondary');
            voiceInputButton.classList.remove('btn-outline-secondary');
            voiceInputButton.classList.remove('btn-danger');
            voiceInputButton.title = 'Voice recognition is not available in the Replit environment';
            
            // Show a more visible message
            const errorMsg = document.createElement('div');
            errorMsg.className = 'alert alert-info mt-2 small';
            errorMsg.innerHTML = '<i class="fas fa-info-circle"></i> Voice input is not available in this environment, but voice output still works.';
            
            // Only add the message if it doesn't exist yet
            if (!document.querySelector('.voice-controls .alert')) {
                document.querySelector('.voice-controls').appendChild(errorMsg);
            }
            break;
        default:
            voiceStatus.textContent = `Error: ${event.error}`;
    }
    
    updateVoiceInputUI();
}

/**
 * Handle voice recognition end event
 */
function handleVoiceEnd() {
    isListening = false;
    updateVoiceInputUI();
}

/**
 * Load available voices for speech synthesis
 */
function loadVoices() {
    voices = synth.getVoices();
}

/**
 * Speak text using speech synthesis
 * @param {string} text - Text to speak
 */
function speak(text) {
    if (!synth || !voiceOutputToggle.checked) return;
    
    // Cancel any ongoing speech
    synth.cancel();
    
    // Create a new utterance
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Select a voice (prefer English voices)
    const englishVoices = voices.filter(voice => voice.lang.includes('en-'));
    if (englishVoices.length > 0) {
        utterance.voice = englishVoices[0];
    }
    
    // Set properties
    utterance.pitch = 1;
    utterance.rate = 1;
    utterance.volume = 1;
    
    // Speak
    synth.speak(utterance);
}

// Export the speak function for use in chat.js
window.speakText = speak;