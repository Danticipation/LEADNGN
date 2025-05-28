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
    // Fetch both learning stats and accelerated learning progress
    Promise.all([
        fetch('/api/learning-stats').then(r => r.json()),
        fetch('/api/learning-progress').then(r => r.json())
    ])
    .then(([statsData, progressData]) => {
        if (statsData.error) {
            console.error('Error fetching learning stats:', statsData.error);
            return;
        }
        
        updateVocabularyDisplay(statsData);
        updateAcceleratedLearningStage(statsData, progressData);
    })
    .catch(error => {
        console.error('Error:', error);
        // Fallback to old method
        fetch('/api/learning-stats')
            .then(response => response.json())
            .then(data => {
                updateVocabularyDisplay(data);
                updateLearningStage(data);
            })
            .catch(err => console.error('Fallback error:', err));
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
 * Update the accelerated learning stage display
 * @param {Object} statsData - Learning statistics data
 * @param {Object} progressData - Learning progress data
 */
function updateAcceleratedLearningStage(statsData, progressData) {
    if (!progressData || !progressData.current_stage) {
        // Fallback to old method
        updateLearningStage(statsData);
        return;
    }
    
    const currentStage = progressData.current_stage;
    const progress = progressData.next_stage_progress || 0;
    const capabilities = progressData.capabilities || [];
    
    // Update learning stage text with proper capitalization
    const stageNames = {
        'infant': 'Infant',
        'toddler': 'Toddler', 
        'child': 'Child',
        'adolescent': 'Adolescent',
        'adult': 'Adult'
    };
    
    learningStageText.textContent = `Learning Stage: ${stageNames[currentStage] || currentStage}`;
    
    // Update progress bar
    learningProgress.style.width = `${progress}%`;
    learningProgress.setAttribute('aria-valuenow', progress);
    
    // Change progress bar color based on stage
    const stageColors = {
        'infant': 'bg-info',
        'toddler': 'bg-primary', 
        'child': 'bg-success',
        'adolescent': 'bg-warning',
        'adult': 'bg-danger'
    };
    
    // Remove existing color classes
    Object.values(stageColors).forEach(color => {
        learningProgress.classList.remove(color);
    });
    
    // Add current stage color
    learningProgress.classList.add(stageColors[currentStage] || 'bg-info');
    
    // Update progress tooltip with stage info
    const stats = progressData.stats || {};
    learningProgress.title = `${stats.message_count || 0} messages, ${stats.vocabulary_count || 0} words, ${stats.facts_count || 0} facts learned. ${Math.round(100 - progress)}% to next stage.`;
    
    // Display capabilities if available
    if (capabilities.length > 0) {
        displayStageCapabilities(capabilities);
    }
}

/**
 * Display current stage capabilities
 * @param {Array} capabilities - List of current capabilities
 */
function displayStageCapabilities(capabilities) {
    // Get or create capabilities container
    let capabilitiesContainer = document.getElementById('stage-capabilities');
    if (!capabilitiesContainer) {
        const learningContainer = document.querySelector('.learning-container');
        if (!learningContainer) return;
        
        const heading = document.createElement('h6');
        heading.className = 'text-light mt-3';
        heading.textContent = 'Current Capabilities';
        learningContainer.appendChild(heading);
        
        capabilitiesContainer = document.createElement('div');
        capabilitiesContainer.id = 'stage-capabilities';
        capabilitiesContainer.className = 'stage-capabilities mt-2';
        learningContainer.appendChild(capabilitiesContainer);
    }
    
    // Clear and update capabilities
    capabilitiesContainer.innerHTML = '';
    
    capabilities.forEach(capability => {
        const capabilityItem = document.createElement('div');
        capabilityItem.className = 'capability-item small text-success';
        capabilityItem.innerHTML = `<i class="fas fa-check"></i> ${capability}`;
        capabilitiesContainer.appendChild(capabilityItem);
    });
}

/**
 * Update the learning stage display (fallback method)
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
    
    // Display advanced learning patterns if available
    displayAdvancedPatterns(data);
}

/**
 * Display advanced learning patterns
 * @param {Object} data - Learning statistics data
 */
function displayAdvancedPatterns(data) {
    // Check if advanced patterns exist in the data
    if (!data.advanced_patterns) {
        return;
    }
    
    // Get or create container for advanced patterns
    let advancedContainer = document.getElementById('advanced-patterns-container');
    if (!advancedContainer) {
        // Check if parent container exists
        const learningContainer = document.querySelector('.learning-container');
        if (!learningContainer) return;
        
        // Create heading
        const heading = document.createElement('h6');
        heading.className = 'text-light mt-4';
        heading.textContent = 'Advanced Learning Patterns';
        learningContainer.appendChild(heading);
        
        // Create container
        advancedContainer = document.createElement('div');
        advancedContainer.id = 'advanced-patterns-container';
        advancedContainer.className = 'advanced-patterns-container mt-2';
        learningContainer.appendChild(advancedContainer);
    }
    
    // Clear existing content
    advancedContainer.innerHTML = '';
    
    const { counts, examples, template_count } = data.advanced_patterns;
    
    // If no patterns learned yet
    if (Object.keys(counts).length === 0 && template_count === 0) {
        const emptyState = document.createElement('p');
        emptyState.className = 'text-muted small';
        emptyState.textContent = 'No advanced patterns learned yet. Continue chatting to teach the bot more patterns!';
        advancedContainer.appendChild(emptyState);
        return;
    }
    
    // Create pattern counts display
    const statsDiv = document.createElement('div');
    statsDiv.className = 'pattern-stats small';
    
    // Add pattern type counts
    for (const [type, count] of Object.entries(counts)) {
        const patternType = document.createElement('div');
        patternType.className = 'pattern-type-stat';
        
        // Format the pattern type name
        let typeName = type.replace('_', ' ');
        if (typeName.endsWith('-gram')) {
            typeName = typeName.replace('-gram', '-word phrases'); 
        }
        
        patternType.innerHTML = `<span class="pattern-type">${typeName}:</span> <span class="pattern-count">${count}</span>`;
        statsDiv.appendChild(patternType);
    }
    
    // Add template count
    if (template_count > 0) {
        const templatesType = document.createElement('div');
        templatesType.className = 'pattern-type-stat';
        templatesType.innerHTML = `<span class="pattern-type">sentence templates:</span> <span class="pattern-count">${template_count}</span>`;
        statsDiv.appendChild(templatesType);
    }
    
    advancedContainer.appendChild(statsDiv);
    
    // Show examples of patterns (if any)
    if (Object.keys(examples).length > 0) {
        const examplesContainer = document.createElement('div');
        examplesContainer.className = 'pattern-examples mt-2';
        
        // Get current mode
        const currentMode = document.getElementById('mode-select').value;
        
        // Add collapsible section for examples
        if (currentMode === 'advanced_imitation') {
            const examplesToggle = document.createElement('a');
            examplesToggle.href = '#';
            examplesToggle.className = 'examples-toggle small text-info';
            examplesToggle.textContent = 'Show pattern examples';
            examplesToggle.onclick = function(e) {
                e.preventDefault();
                const examplesList = document.getElementById('pattern-examples-list');
                if (examplesList.style.display === 'none') {
                    examplesList.style.display = 'block';
                    examplesToggle.textContent = 'Hide pattern examples';
                } else {
                    examplesList.style.display = 'none';
                    examplesToggle.textContent = 'Show pattern examples';
                }
            };
            examplesContainer.appendChild(examplesToggle);
            
            // Create examples list (hidden by default)
            const examplesList = document.createElement('div');
            examplesList.id = 'pattern-examples-list';
            examplesList.className = 'pattern-examples-list small mt-2';
            examplesList.style.display = 'none';
            
            // Add examples for each pattern type
            for (const [type, patternList] of Object.entries(examples)) {
                if (patternList.length === 0) continue;
                
                // Format pattern type name
                let typeName = type.replace('_', ' ');
                if (typeName.endsWith('-gram')) {
                    typeName = typeName.replace('-gram', '-word phrases'); 
                }
                
                const typeHeading = document.createElement('div');
                typeHeading.className = 'pattern-examples-heading text-info mt-1';
                typeHeading.textContent = typeName + ':';
                examplesList.appendChild(typeHeading);
                
                // Add pattern examples
                patternList.forEach(pattern => {
                    const patternItem = document.createElement('div');
                    patternItem.className = 'pattern-example-item';
                    patternItem.textContent = `"${pattern.pattern}" (used ${pattern.frequency} times)`;
                    examplesList.appendChild(patternItem);
                });
            }
            
            examplesContainer.appendChild(examplesList);
        } else {
            // For other modes, just show a note
            const noteElem = document.createElement('div');
            noteElem.className = 'text-muted small';
            noteElem.textContent = 'Switch to Advanced Imitation Mode to see learned patterns.';
            examplesContainer.appendChild(noteElem);
        }
        
        advancedContainer.appendChild(examplesContainer);
    }
    
    // Add some CSS for the new elements
    addAdvancedPatternsCSS();
}

/**
 * Add CSS for advanced patterns display
 */
function addAdvancedPatternsCSS() {
    // Check if styles are already added
    if (document.getElementById('advanced-patterns-styles')) {
        return;
    }
    
    // Create style element
    const styleElem = document.createElement('style');
    styleElem.id = 'advanced-patterns-styles';
    
    // Add CSS rules
    styleElem.textContent = `
        .advanced-patterns-container {
            background-color: rgba(30, 30, 30, 0.3);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 16px;
        }
        
        .pattern-stats {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .pattern-type-stat {
            background-color: rgba(40, 40, 40, 0.5);
            border-radius: 4px;
            padding: 4px 8px;
        }
        
        .pattern-type {
            color: var(--bs-info);
            font-weight: 500;
        }
        
        .pattern-examples-list {
            background-color: rgba(20, 20, 20, 0.5);
            border-radius: 6px;
            padding: 8px 12px;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .pattern-example-item {
            padding: 3px 0;
            color: #ccc;
        }
    `;
    
    // Add to document
    document.head.appendChild(styleElem);
}
