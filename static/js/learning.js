/**
 * Learning visualization functionality for MirrorBot
 */

// DOM elements
const learningStageText = document.getElementById('learning-stage');
const learningProgress = document.getElementById('learning-progress');
const vocabularyContainer = document.getElementById('vocabulary-container');

// Initialize learning visualization
document.addEventListener('DOMContentLoaded', () => {
    updateLearningStats();
});

/**
 * Update learning statistics and visualization
 */
function updateLearningStats() {
    fetch('/api/learning-stats')
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error('Error fetching learning stats:', data.error);
            return;
        }
        
        updateVocabularyDisplay(data);
        updateLearningStage(data);
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

/**
 * Update the vocabulary display
 * @param {Object} data - Learning statistics data
 */
function updateVocabularyDisplay(data) {
    if (!data.vocabulary || !Array.isArray(data.vocabulary)) {
        return;
    }
    
    // Clear current vocabulary
    vocabularyContainer.innerHTML = '';
    
    // Get current mode
    const currentMode = document.getElementById('mode-select').value;
    
    // Filter words by current mode for focused display
    const modeWords = data.vocabulary.filter(item => item.mode === currentMode);
    
    // Sort by frequency
    const sortedWords = modeWords.sort((a, b) => b.frequency - a.frequency);
    
    // Only show top words (to avoid cluttering the UI)
    const displayWords = sortedWords.slice(0, 20);
    
    // Calculate font size range based on frequencies
    let maxFreq = 1;
    if (displayWords.length > 0) {
        maxFreq = Math.max(...displayWords.map(w => w.frequency));
    }
    
    // Add words to display
    displayWords.forEach(word => {
        const wordSpan = document.createElement('span');
        wordSpan.className = 'word-item';
        wordSpan.textContent = word.word;
        
        // Scale font size by frequency (min 0.8rem, max 1.5rem)
        const fontSize = 0.8 + (word.frequency / maxFreq) * 0.7;
        wordSpan.style.fontSize = `${fontSize}rem`;
        
        // Add mode-specific color accent
        wordSpan.classList.add(`mode-${word.mode}`);
        
        vocabularyContainer.appendChild(wordSpan);
    });
    
    // Add empty state if no words
    if (displayWords.length === 0) {
        const emptyState = document.createElement('p');
        emptyState.className = 'text-muted small';
        emptyState.textContent = 'No vocabulary learned yet in this mode. Try chatting more!';
        vocabularyContainer.appendChild(emptyState);
    }
}

/**
 * Update the learning stage display
 * @param {Object} data - Learning statistics data
 */
function updateLearningStage(data) {
    const totalVocab = data.total || 0;
    
    // Calculate learning stage
    const learningStages = [
        { threshold: 0, name: 'Newborn' },
        { threshold: 10, name: 'Infant' },
        { threshold: 25, name: 'Toddler' },
        { threshold: 50, name: 'Child' },
        { threshold: 100, name: 'Teen' },
        { threshold: 200, name: 'Young Adult' },
        { threshold: 500, name: 'Adult' },
        { threshold: 1000, name: 'Wise Elder' }
    ];
    
    // Find current stage
    let currentStage = learningStages[0];
    let nextStage = learningStages[1];
    
    for (let i = 0; i < learningStages.length - 1; i++) {
        if (totalVocab >= learningStages[i].threshold && totalVocab < learningStages[i + 1].threshold) {
            currentStage = learningStages[i];
            nextStage = learningStages[i + 1];
            break;
        } else if (i === learningStages.length - 2 && totalVocab >= learningStages[i + 1].threshold) {
            currentStage = learningStages[i + 1];
            nextStage = null;
        }
    }
    
    // Calculate progress percentage to next stage
    let progressPercentage = 0;
    
    if (nextStage) {
        const rangeSize = nextStage.threshold - currentStage.threshold;
        const progress = totalVocab - currentStage.threshold;
        progressPercentage = Math.min(100, Math.max(0, Math.floor((progress / rangeSize) * 100)));
    } else {
        // At max stage
        progressPercentage = 100;
    }
    
    // Update learning stage text
    learningStageText.textContent = `Learning Stage: ${currentStage.name}`;
    
    // Update progress bar
    learningProgress.style.width = `${progressPercentage}%`;
    learningProgress.setAttribute('aria-valuenow', progressPercentage);
    
    // Change progress bar color based on stage
    const stageColors = [
        'bg-info', 'bg-primary', 'bg-success', 
        'bg-warning', 'bg-danger', 'bg-purple'
    ];
    
    // Remove existing color classes
    stageColors.forEach(color => {
        learningProgress.classList.remove(color);
    });
    
    // Add current stage color
    const stageIndex = learningStages.indexOf(currentStage);
    const colorIndex = stageIndex % stageColors.length;
    learningProgress.classList.add(stageColors[colorIndex]);
    
    // Update progress text tooltip
    if (nextStage) {
        learningProgress.title = `${totalVocab} words learned. ${nextStage.threshold - totalVocab} more until next stage.`;
    } else {
        learningProgress.title = `${totalVocab} words learned. Maximum stage reached!`;
    }
    
    // Get mode-specific stats
    const modeStats = data.by_mode || {};
    const currentMode = document.getElementById('mode-select').value;
    const modeCount = modeStats[currentMode] || 0;
    
    // Add mode-specific info
    const modeStatsElem = document.getElementById('mode-stats');
    if (modeStatsElem) {
        modeStatsElem.textContent = `Words in current mode: ${modeCount}`;
    }
}
