/**
 * Frontend Integration for Calm Profile Assessment
 * 
 * This script modifies the existing HTML assessment to send data
 * to the Flask API and display enhanced results.
 */

// Configuration
const API_BASE_URL = 'http://localhost:5000/api';

// Store answers in the format expected by the API
let apiAnswers = {
    responses: {},
    meta: {
        team_size: "2-5",
        meetings: "7-10", 
        platform: "microsoft"
    }
};

// Override the existing selectAnswer function
window.selectAnswer = function(element, questionNum) {
    // Remove selection from other options
    element.parentNode.querySelectorAll('.answer-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    // Select current option
    element.classList.add('selected');
    
    // Store answer in both formats
    const trait = element.dataset.value;
    const questionId = `q${String(questionNum).padStart(2, '0')}`;
    
    // Store for API
    apiAnswers.responses[questionId] = trait;
    
    // Store for existing logic
    answers[questionNum - 1] = trait;
    
    // Enable next button
    document.getElementById(`nextBtn${questionNum}`).disabled = false;
}

// Override calculateResults to call the API
window.calculateResults = async function() {
    try {
        // Show loading state
        showLoadingState();
        
        // Add metadata from user (you might want to collect this via form)
        // For now, using defaults or you can add form fields to collect these
        
        // Call the API
        const response = await fetch(`${API_BASE_URL}/assess`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(apiAnswers)
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayEnhancedResults(data.results);
        } else {
            console.error('Assessment failed:', data.error);
            // Fallback to original calculation
            fallbackToOriginalResults();
        }
        
    } catch (error) {
        console.error('API call failed:', error);
        // Fallback to original calculation
        fallbackToOriginalResults();
    }
}

function showLoadingState() {
    // Hide all question sections
    document.querySelectorAll('.question-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show loading indicator
    const container = document.getElementById('questionsContainer');
    container.innerHTML = `
        <div style="text-align: center; padding: 60px 0;">
            <h2>analyzing your responses<span class="dot">.</span></h2>
            <p style="color: var(--gray-600); margin-top: 20px;">
                calculating your productivity metrics and generating recommendations...
            </p>
            <div style="margin-top: 40px;">
                <div class="loading-spinner"></div>
            </div>
        </div>
    `;
    
    // Add loading spinner CSS if not exists
    if (!document.querySelector('#loading-styles')) {
        const style = document.createElement('style');
        style.id = 'loading-styles';
        style.textContent = `
            .loading-spinner {
                display: inline-block;
                width: 40px;
                height: 40px;
                border: 3px solid var(--gray-200);
                border-top-color: var(--primary);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            .metric-card {
                background: var(--gray-50);
                border-radius: 8px;
                padding: 24px;
                margin-bottom: 16px;
            }
            .metric-value {
                font-size: 32px;
                font-weight: 600;
                color: var(--primary);
                font-family: var(--mono);
            }
            .metric-label {
                font-size: 14px;
                color: var(--gray-600);
                margin-top: 8px;
            }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
                margin: 32px 0;
            }
            .insight-box {
                background: linear-gradient(135deg, rgba(0,201,167,0.05) 0%, rgba(0,201,167,0.02) 100%);
                border-left: 3px solid var(--primary);
                padding: 20px;
                margin: 24px 0;
                border-radius: 4px;
            }
        `;
        document.head.appendChild(style);
    }
}

function displayEnhancedResults(results) {
    const archetype = results.archetype.primary;
    const profile = {
        title: `the ${archetype}`,
        description: results.insights.summary,
        strengths: results.recommendations.strengths,
        workflow: results.recommendations.quick_wins,
        tools: results.recommendations.tool_stack
    };
    
    // Update basic profile display
    document.getElementById('profileType').textContent = profile.title;
    document.getElementById('profileDescription').textContent = profile.description;
    
    // Update lists
    document.getElementById('strengthsList').innerHTML = 
        profile.strengths.map(s => `<li>${s}</li>`).join('');
    document.getElementById('workflowList').innerHTML = 
        profile.workflow.map(w => `<li>${w}</li>`).join('');
    document.getElementById('toolsList').innerHTML = 
        profile.tools.map(t => `<li>${t}</li>`).join('');
    
    // Add enhanced metrics section before profile details
    const metricsHTML = `
        <div class="metrics-section" style="margin-bottom: var(--space-lg);">
            <h2 style="text-align: center; margin-bottom: var(--space-md);">
                your productivity metrics<span class="dot">.</span>
            </h2>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">${results.metrics.hours_lost_per_person_weekly}h</div>
                    <div class="metric-label">hours lost per week</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${results.metrics.coordination_share * 100}%</div>
                    <div class="metric-label">time in coordination</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${results.metrics.productivity_impact}%</div>
                    <div class="metric-label">productivity impact</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">$${Math.round(results.metrics.annual_cost_estimate / 1000)}k</div>
                    <div class="metric-label">annual overhead cost</div>
                </div>
            </div>
            
            <div class="insight-box">
                <h3 style="margin-bottom: 12px;">Primary Friction Point: 
                    <span style="color: var(--primary);">${results.insights.primary_friction_point.area}</span>
                </h3>
                <p style="margin: 0; color: var(--gray-600);">
                    Score: ${results.insights.primary_friction_point.score}/100 
                    (${results.insights.primary_friction_point.impact} impact)
                </p>
            </div>
            
            ${results.archetype.confidence === 'low' ? `
                <div class="insight-box" style="background: linear-gradient(135deg, rgba(255,193,7,0.1) 0%, rgba(255,193,7,0.02) 100%); border-left-color: #FFC107;">
                    <p style="margin: 0;">
                        <strong>Hybrid Profile Detected:</strong> You show characteristics of both 
                        ${results.archetype.primary} and ${results.archetype.secondary} archetypes.
                        Consider blending recommendations from both profiles.
                    </p>
                </div>
            ` : ''}
        </div>
    `;
    
    // Insert metrics before profile details
    const profileDetails = document.getElementById('profileDetails');
    profileDetails.insertAdjacentHTML('beforebegin', metricsHTML);
    
    // Set profile type for form
    document.getElementById('profileTypeInput').value = `${profile.title} - OI: ${results.scores.overhead_index}`;
    
    // Show results section
    document.getElementById('resultsSection').classList.add('active');
    
    // Clear loading state
    document.getElementById('questionsContainer').innerHTML = '';
    
    // Update progress to 100%
    document.getElementById('progressFill').style.width = '100%';
    document.getElementById('progressText').textContent = 'assessment complete';
}

function fallbackToOriginalResults() {
    // Use the original calculateResults logic as fallback
    const archetypeScores = {
        architect: 0,
        curator: 0,
        conductor: 0,
        craftsperson: 0
    };
    
    // Simplified scoring for fallback
    const traitToArchetype = {
        structured: 'architect',
        analytical: 'architect',
        visual: 'curator',
        adaptive: 'curator',
        collaborative: 'conductor',
        social: 'conductor',
        hands_on: 'craftsperson',
        focused: 'craftsperson'
    };
    
    answers.forEach(trait => {
        const archetype = traitToArchetype[trait];
        if (archetype) {
            archetypeScores[archetype] += 1;
        }
    });
    
    let primaryArchetype = 'architect';
    let highestScore = 0;
    for (const archetype in archetypeScores) {
        if (archetypeScores[archetype] > highestScore) {
            highestScore = archetypeScores[archetype];
            primaryArchetype = archetype;
        }
    }
    
    // Use original showResults
    showResults(primaryArchetype);
}

// Add metadata collection before assessment starts
function addMetadataSection() {
    const introSection = document.getElementById('introSection');
    
    // Check if metadata section already exists
    if (document.getElementById('metadataSection')) return;
    
    const metadataHTML = `
        <div id="metadataSection" style="margin: var(--space-md) 0; padding: var(--space-md); background: var(--gray-50); border-radius: 8px;">
            <h3 style="margin-bottom: var(--space-sm);">customize your assessment<span class="dot">.</span></h3>
            <div style="display: grid; gap: var(--space-sm); max-width: 400px; margin: 0 auto;">
                <div>
                    <label style="display: block; font-size: 14px; color: var(--gray-600); margin-bottom: 8px;">
                        Team Size
                    </label>
                    <select id="teamSize" style="width: 100%; padding: 8px; border: 1px solid var(--gray-200); border-radius: 4px; font-family: var(--sans);">
                        <option value="solo">Solo</option>
                        <option value="2-5" selected>2-5 people</option>
                        <option value="6-15">6-15 people</option>
                        <option value="16-50">16-50 people</option>
                        <option value="50+">50+ people</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; font-size: 14px; color: var(--gray-600); margin-bottom: 8px;">
                        Weekly Meetings
                    </label>
                    <select id="meetings" style="width: 100%; padding: 8px; border: 1px solid var(--gray-200); border-radius: 4px; font-family: var(--sans);">
                        <option value="0-2">0-2 meetings</option>
                        <option value="3-6">3-6 meetings</option>
                        <option value="7-10" selected>7-10 meetings</option>
                        <option value="11-15">11-15 meetings</option>
                        <option value="16+">16+ meetings</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; font-size: 14px; color: var(--gray-600); margin-bottom: 8px;">
                        Primary Platform
                    </label>
                    <select id="platform" style="width: 100%; padding: 8px; border: 1px solid var(--gray-200); border-radius: 4px; font-family: var(--sans);">
                        <option value="microsoft" selected>Microsoft 365</option>
                        <option value="google">Google Workspace</option>
                    </select>
                </div>
            </div>
        </div>
    `;
    
    // Insert before the start button
    const startButton = introSection.querySelector('.btn');
    startButton.insertAdjacentHTML('beforebegin', metadataHTML);
}

// Update startAssessment to capture metadata
const originalStartAssessment = window.startAssessment;
window.startAssessment = function() {
    // Capture metadata
    const teamSize = document.getElementById('teamSize')?.value || "2-5";
    const meetings = document.getElementById('meetings')?.value || "7-10";
    const platform = document.getElementById('platform')?.value || "microsoft";
    
    apiAnswers.meta = {
        team_size: teamSize,
        meetings: meetings,
        platform: platform
    };
    
    // Call original function
    originalStartAssessment();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    addMetadataSection();
});