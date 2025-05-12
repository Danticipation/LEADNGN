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
let selectedVoice = null;

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
 * Load available voices for speech synthesis and create voice selector
 */
function loadVoices() {
    voices = synth.getVoices();
    
    // Create voice selector if not already created
    if (!document.getElementById('voice-selector') && voices.length > 0) {
        createVoiceSelector();
    }
    
    // Load previously selected voice from localStorage
    const savedVoiceURI = localStorage.getItem('selectedVoiceURI');
    if (savedVoiceURI) {
        selectedVoice = voices.find(voice => voice.voiceURI === savedVoiceURI);
    } else {
        // Default to an English voice if available
        selectedVoice = voices.find(voice => voice.lang.startsWith('en-')) || voices[0];
    }
    
    // Update the selector if it exists
    updateVoiceSelector();
}

/**
 * Create voice selector UI
 */
function createVoiceSelector() {
    // Create container for the voice selector
    const voiceSelectorContainer = document.createElement('div');
    voiceSelectorContainer.className = 'voice-selector-container mt-2';
    
    // Create a row for better alignment
    const row = document.createElement('div');
    row.className = 'd-flex align-items-center flex-wrap';
    
    // Create a label
    const label = document.createElement('label');
    label.htmlFor = 'voice-selector';
    label.className = 'form-label small text-muted me-2 mb-0';
    label.textContent = 'Bot Voice:';
    
    // Create the select element
    const select = document.createElement('select');
    select.id = 'voice-selector';
    select.className = 'form-select form-select-sm';
    select.style.maxWidth = '180px';
    
    // Create test button
    const testButton = document.createElement('button');
    testButton.type = 'button';
    testButton.className = 'btn btn-sm btn-outline-secondary ms-2';
    testButton.innerHTML = '<i class="fas fa-play"></i> Test';
    testButton.title = 'Test selected voice';
    testButton.addEventListener('click', function() {
        if (selectedVoice) {
            // Speak a test phrase
            const testUtterance = new SpeechSynthesisUtterance('Hello, I am Mirror Bot');
            testUtterance.voice = selectedVoice;
            synth.speak(testUtterance);
        }
    });
    
    // Add change event handler for select
    select.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        if (selectedOption) {
            const voiceURI = selectedOption.value;
            selectedVoice = voices.find(voice => voice.voiceURI === voiceURI);
            
            if (selectedVoice) {
                localStorage.setItem('selectedVoiceURI', selectedVoice.voiceURI);
            }
        }
    });
    
    // Append elements
    row.appendChild(label);
    row.appendChild(select);
    row.appendChild(testButton);
    voiceSelectorContainer.appendChild(row);
    
    // Add description text
    const description = document.createElement('div');
    description.className = 'small text-muted mt-1';
    description.textContent = 'Voice pitch and rate adapt to bot personality mode';
    voiceSelectorContainer.appendChild(description);
    
    // Add to the voice controls section
    const voiceControls = document.querySelector('.voice-controls');
    voiceControls.appendChild(voiceSelectorContainer);
    
    // Populate the selector
    updateVoiceSelector();
}

/**
 * Update voice selector with available voices
 */
function updateVoiceSelector() {
    const selector = document.getElementById('voice-selector');
    if (!selector) return;
    
    // Clear existing options
    selector.innerHTML = '';
    
    // Group voices by language
    const voicesByLang = {};
    
    // Process English voices first (most common)
    const englishVoices = voices.filter(voice => voice.lang.startsWith('en-'));
    if (englishVoices.length > 0) {
        voicesByLang['English'] = englishVoices;
    }
    
    // Process other voices
    voices.forEach(voice => {
        if (!voice.lang.startsWith('en-')) {
            // Extract language name from the language code
            const langCode = voice.lang.split('-')[0];
            let langName = langCode;
            
            // Try to get human-readable language name if Intl.DisplayNames is supported
            try {
                if (typeof Intl !== 'undefined' && typeof Intl.DisplayNames === 'function') {
                    langName = new Intl.DisplayNames(['en'], { type: 'language' }).of(langCode) || langCode;
                }
            } catch (e) {
                console.warn('Intl.DisplayNames not supported in this browser');
                // Fallback to using basic language mapping
                const langMap = {
                    'en': 'English',
                    'fr': 'French',
                    'es': 'Spanish',
                    'de': 'German',
                    'it': 'Italian',
                    'pt': 'Portuguese',
                    'ru': 'Russian',
                    'ja': 'Japanese',
                    'zh': 'Chinese'
                };
                langName = langMap[langCode] || langCode;
            }
            
            if (!voicesByLang[langName]) {
                voicesByLang[langName] = [];
            }
            voicesByLang[langName].push(voice);
        }
    });
    
    // Add options grouped by language
    Object.keys(voicesByLang).sort().forEach(langName => {
        // Create optgroup for language
        const optgroup = document.createElement('optgroup');
        optgroup.label = langName;
        
        // Add voices for this language
        voicesByLang[langName].forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.voiceURI;
            option.textContent = voice.name;
            option.selected = selectedVoice && voice.voiceURI === selectedVoice.voiceURI;
            optgroup.appendChild(option);
        });
        
        selector.appendChild(optgroup);
    });
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
    
    // Use selected voice if available
    if (selectedVoice) {
        utterance.voice = selectedVoice;
    } else {
        // Fallback to an English voice if none selected
        const englishVoices = voices.filter(voice => voice.lang.includes('en-'));
        if (englishVoices.length > 0) {
            utterance.voice = englishVoices[0];
        }
    }
    
    // Adjust properties based on bot personality mode
    const currentMode = document.getElementById('mode-select').value;
    
    // Default properties
    let pitch = 1.0;
    let rate = 1.0;
    
    // Adjust based on bot personality
    switch (currentMode) {
        case 'imitation':
            // Normal human-like speech
            pitch = 1.0;
            rate = 1.0;
            break;
        case 'literal':
            // Slightly mechanical, precise
            pitch = 0.9;
            rate = 0.9;
            break;
        case 'echo':
            // Slightly higher pitch for echo effect
            pitch = 1.1;
            rate = 0.95;
            break;
        case 'overunderstanding':
            // Enthusiastic, slightly faster
            pitch = 1.15;
            rate = 1.1;
            break;
        case 'nonsense':
            // Varied, unpredictable
            pitch = 0.9 + Math.random() * 0.4; // 0.9 to 1.3
            rate = 0.8 + Math.random() * 0.4;  // 0.8 to 1.2
            break;
    }
    
    // Set properties
    utterance.pitch = pitch;
    utterance.rate = rate;
    utterance.volume = 1;
    
    // Speak
    synth.speak(utterance);
}

// Export the speak function for use in chat.js
window.speakText = speak;