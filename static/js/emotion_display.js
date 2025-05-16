/**
 * Emotion Display JS - Visualizes user emotions for MirrorBot
 */

// Emotion color mappings for visualization
const EMOTION_COLORS = {
    'happy': '#4BBF73',     // Green
    'sad': '#5091CD',       // Blue
    'angry': '#D9534F',     // Red
    'afraid': '#EFAD4D',    // Yellow/Gold
    'surprised': '#9B59B6', // Purple
    'neutral': '#6C757D'    // Gray
};

// Emotion icons for visualization
const EMOTION_ICONS = {
    'happy': 'fa-smile',
    'sad': 'fa-sad-tear',
    'angry': 'fa-angry',
    'afraid': 'fa-grimace',
    'surprised': 'fa-surprise',
    'neutral': 'fa-meh'
};

// Function to initialize emotion visualization
function initEmotionDisplay() {
    // Add a tab for emotions to the memory page
    const memoryTabs = document.getElementById('memory-tabs');
    if (memoryTabs) {
        // Only run this code on the memory page
        fetchEmotionData();
    }
}

// Fetch emotion data from the API
function fetchEmotionData() {
    fetch('/api/emotion-stats')
        .then(response => response.json())
        .then(data => {
            displayEmotionHistory(data.recent_emotions || []);
            displayEmotionDistribution(data.emotion_distribution || {});
            displayEmotionTimeline(data.emotion_timeline || {});
            displayEmotionalPatterns(data.emotional_patterns || {});
        })
        .catch(error => {
            console.error('Error fetching emotion data:', error);
            document.getElementById('emotion-container').innerHTML = 
                '<div class="alert alert-danger">Error loading emotion data. Please try again later.</div>';
        });
}

// Display recent emotion history
function displayEmotionHistory(emotions) {
    const container = document.getElementById('recent-emotions');
    
    if (!container) return;
    
    if (!emotions || emotions.length === 0) {
        container.innerHTML = '<p class="text-center">No emotions detected yet. Try having a conversation!</p>';
        return;
    }
    
    let html = '<div class="list-group">';
    
    emotions.forEach(emotion => {
        // Format the date
        const date = new Date(emotion.created_at);
        const formattedDate = date.toLocaleString();
        
        // Calculate opacity based on confidence and intensity
        const opacity = Math.max(0.3, Math.min(0.9, emotion.confidence * emotion.intensity));
        
        // Get the emotion color
        const color = EMOTION_COLORS[emotion.primary_emotion] || EMOTION_COLORS.neutral;
        const icon = EMOTION_ICONS[emotion.primary_emotion] || EMOTION_ICONS.neutral;
        
        // Create a styled list item
        html += `
        <div class="list-group-item list-group-item-action" 
             style="border-left: 4px solid ${color}; background-color: rgba(${hexToRgb(color)}, ${opacity});">
            <div class="d-flex w-100 justify-content-between align-items-center">
                <h6 class="mb-1">
                    <i class="fas ${icon} me-2"></i>
                    ${capitalizeFirst(emotion.primary_emotion)}
                </h6>
                <small>${formattedDate}</small>
            </div>
            <p class="mb-1 text-truncate">${emotion.text_sample}</p>
            <small>Confidence: ${(emotion.confidence * 100).toFixed(1)}% | Intensity: ${(emotion.intensity * 100).toFixed(1)}%</small>
        </div>`;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Display emotion distribution as a pie chart
function displayEmotionDistribution(distribution) {
    const container = document.getElementById('emotion-distribution');
    
    if (!container) return;
    
    if (!distribution || Object.keys(distribution).length === 0) {
        container.innerHTML = '<p class="text-center">No emotion distribution data available yet.</p>';
        return;
    }
    
    // Prepare data for chart
    const labels = [];
    const data = [];
    const backgroundColor = [];
    
    for (const [emotion, count] of Object.entries(distribution)) {
        labels.push(capitalizeFirst(emotion));
        data.push(count);
        backgroundColor.push(EMOTION_COLORS[emotion] || EMOTION_COLORS.neutral);
    }
    
    // Create canvas element for the chart
    container.innerHTML = '<canvas id="emotion-chart"></canvas>';
    const ctx = document.getElementById('emotion-chart').getContext('2d');
    
    // Create the pie chart
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColor,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#fff'
                    }
                },
                title: {
                    display: true,
                    text: 'Emotion Distribution',
                    color: '#fff'
                }
            }
        }
    });
}

// Display emotion timeline as a line chart
function displayEmotionTimeline(timeline) {
    const container = document.getElementById('emotion-timeline');
    
    if (!container) return;
    
    if (!timeline || !timeline.timestamps || timeline.timestamps.length === 0) {
        container.innerHTML = '<p class="text-center">No timeline data available yet.</p>';
        return;
    }
    
    // Create canvas element for the chart
    container.innerHTML = '<canvas id="timeline-chart"></canvas>';
    const ctx = document.getElementById('timeline-chart').getContext('2d');
    
    // Format dates for display
    const formattedDates = timeline.timestamps.map(ts => {
        const date = new Date(ts);
        return date.toLocaleString();
    });
    
    // Prepare datasets for each emotion
    const datasets = [];
    
    for (const [emotion, values] of Object.entries(timeline.emotions)) {
        datasets.push({
            label: capitalizeFirst(emotion),
            data: values,
            borderColor: EMOTION_COLORS[emotion] || EMOTION_COLORS.neutral,
            backgroundColor: `rgba(${hexToRgb(EMOTION_COLORS[emotion] || EMOTION_COLORS.neutral)}, 0.2)`,
            borderWidth: 2,
            tension: 0.4
        });
    }
    
    // Create the line chart
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: formattedDates,
            datasets: datasets
        },
        options: {
            responsive: true,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#fff'
                    }
                },
                title: {
                    display: true,
                    text: 'Emotion Timeline',
                    color: '#fff'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1,
                    ticks: {
                        color: '#fff'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: '#fff',
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

// Display emotional patterns analysis
function displayEmotionalPatterns(patterns) {
    const container = document.getElementById('emotional-patterns');
    
    if (!container) return;
    
    if (!patterns || Object.keys(patterns).length === 0) {
        container.innerHTML = '<p class="text-center">No pattern analysis available yet.</p>';
        return;
    }
    
    // Create HTML for emotional pattern display
    let html = '<div class="card bg-dark text-light">';
    html += '<div class="card-body">';
    
    // Show dominant emotion
    const dominantColor = EMOTION_COLORS[patterns.dominant_emotion] || EMOTION_COLORS.neutral;
    const dominantIcon = EMOTION_ICONS[patterns.dominant_emotion] || EMOTION_ICONS.neutral;
    
    html += `<div class="mb-3">
                <h6>Dominant Emotion</h6>
                <div class="d-flex align-items-center">
                    <span class="badge p-2 me-2" style="background-color: ${dominantColor};">
                        <i class="fas ${dominantIcon}"></i>
                    </span>
                    <span>${capitalizeFirst(patterns.dominant_emotion)}</span>
                </div>
            </div>`;
    
    // Show emotional stability and range
    html += `<div class="row mb-3">
                <div class="col-6">
                    <h6>Emotional Stability</h6>
                    <div class="progress" style="height: 20px">
                        <div class="progress-bar bg-info" role="progressbar" 
                             style="width: ${patterns.emotional_stability * 100}%" 
                             aria-valuenow="${patterns.emotional_stability * 100}" 
                             aria-valuemin="0" aria-valuemax="100">
                            ${(patterns.emotional_stability * 100).toFixed(0)}%
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <h6>Emotional Range</h6>
                    <div class="progress" style="height: 20px">
                        <div class="progress-bar bg-warning" role="progressbar" 
                             style="width: ${patterns.emotional_range * 100}%" 
                             aria-valuenow="${patterns.emotional_range * 100}" 
                             aria-valuemin="0" aria-valuemax="100">
                            ${(patterns.emotional_range * 100).toFixed(0)}%
                        </div>
                    </div>
                </div>
            </div>`;
    
    // Show emotion counts
    if (patterns.emotion_counts && Object.keys(patterns.emotion_counts).length > 0) {
        html += '<h6>Emotion Distribution</h6>';
        html += '<div class="emotion-count-container d-flex flex-wrap">';
        
        for (const [emotion, count] of Object.entries(patterns.emotion_counts)) {
            const color = EMOTION_COLORS[emotion] || EMOTION_COLORS.neutral;
            const icon = EMOTION_ICONS[emotion] || EMOTION_ICONS.neutral;
            
            html += `<div class="emotion-count-item p-2 m-1 rounded" 
                         style="background-color: ${color};">
                        <i class="fas ${icon} me-1"></i>
                        ${capitalizeFirst(emotion)}: ${count}
                    </div>`;
        }
        
        html += '</div>';
    }
    
    html += '</div></div>';
    container.innerHTML = html;
}

// Helper function to capitalize first letter
function capitalizeFirst(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

// Helper function to convert hex to RGB
function hexToRgb(hex) {
    // Remove # if present
    hex = hex.replace('#', '');
    
    // Parse the hex values
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    
    return `${r}, ${g}, ${b}`;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initEmotionDisplay);