import { useState } from 'react';
import './ResolutionCenter.css';

/**
 * ResolutionCenter - A 3-tier Decision Support System for Air Traffic Control
 * Provides AI recommendations, manual control, and legacy protocol options
 */
function ResolutionCenter({ contextData, recommendations = [], onResolve }) {
  // Manual intervention form state
  const [manualForm, setManualForm] = useState({
    flightId: '',
    actionType: '',
    value: ''
  });

  // Gemini analysis state
  const [geminiState, setGeminiState] = useState({
    loading: false,
    analysisText: '',
    activeSection: null // 'ai' | 'manual' | null
  });

  // Get primary recommendation from props
  const primaryRecommendation = recommendations[0] || {
    flightId: 'N/A',
    action: 'No recommendation available',
    score: 0,
    reasoning: 'Insufficient data for analysis'
  };

  // Extract available flights from context data for dropdown
  const availableFlights = contextData?.flights?.map(f => f.ACID || f.flightId) || 
    recommendations.map(r => r.flightId) || 
    ['ACA821', 'WJA134', 'ACA320'];

  /**
   * Mock Gemini API call
   * Simulates AI analysis with different responses based on type
   */
  const handleAskGemini = async (type) => {
    setGeminiState({
      loading: true,
      analysisText: '',
      activeSection: type
    });

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1500));

    let responseText = '';

    if (type === 'ai') {
      responseText = `✅ **AI Recommendation Analysis**

This recommendation achieves optimal efficiency by:
• Minimizing sector congestion by 23%
• Reducing fuel consumption by an estimated 340 gallons
• Maintaining safe separation with 99.7% confidence
• Projected delay reduction: 4.2 minutes per affected aircraft

The algorithm considered 847 possible routing combinations and selected this option based on current traffic density, weather patterns, and downstream sector capacity. This approach follows ICAO Doc 4444 guidelines while optimizing for both safety and efficiency.`;
    } else if (type === 'manual') {
      responseText = `⚠️ **Risk Assessment for Manual Intervention**

Potential side effects detected:
• **Fuel Impact:** +180-220 gallons additional burn for rerouted aircraft
• **Secondary Bottleneck:** YYZ_EAST sector may experience 15% capacity increase in T+12 minutes
• **Cascade Risk:** 3 trailing aircraft may require speed adjustments
• **Controller Workload:** Estimated +2 additional handoffs required

**Mitigation Suggestions:**
1. Coordinate with downstream sector before execution
2. Consider speed reduction for trailing traffic
3. Monitor fuel states for extended routing

Proceed with caution. Human judgment validated for non-standard situations.`;
    }

    setGeminiState({
      loading: false,
      analysisText: responseText,
      activeSection: type
    });
  };

  /**
   * Handle manual form field changes
   */
  const handleFormChange = (field, value) => {
    setManualForm(prev => ({
      ...prev,
      [field]: value
    }));
  };

  /**
   * Handle resolution action
   */
  const handleResolve = (tier, data) => {
    if (onResolve) {
      onResolve({
        tier,
        timestamp: Date.now(),
        ...data
      });
    }
  };

  return (
    <div className="resolution-center">
      <h2 className="resolution-title">🎯 Decision Support System</h2>
      <p className="resolution-subtitle">Choose your resolution approach</p>

      <div className="resolution-tiers">
        {/* Tier 1: AI Recommendation (The Scalpel) */}
        <div className="option-card ai-option">
          <div className="tier-header">
            <span className="tier-badge tier-1">Tier 1</span>
            <h3>🔬 AI Recommendation</h3>
            <span className="tier-nickname">The Scalpel</span>
          </div>

          <div className="recommendation-details">
            <div className="detail-row">
              <span className="detail-label">Flight:</span>
              <span className="detail-value">{primaryRecommendation.flightId}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Action:</span>
              <span className="detail-value">{primaryRecommendation.action}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Score:</span>
              <span className="detail-value score-badge">
                {primaryRecommendation.score}/100
              </span>
            </div>
            <div className="detail-row reasoning">
              <span className="detail-label">Reasoning:</span>
              <span className="detail-value">{primaryRecommendation.reasoning}</span>
            </div>
          </div>

          <div className="tier-metrics">
            <div className="metric positive">
              <span className="metric-value">Low</span>
              <span className="metric-label">Cost</span>
            </div>
            <div className="metric positive">
              <span className="metric-value">~2 min</span>
              <span className="metric-label">Delay</span>
            </div>
            <div className="metric positive">
              <span className="metric-value">High</span>
              <span className="metric-label">Precision</span>
            </div>
          </div>

          <div className="tier-actions">
            <button 
              className="btn btn-gemini"
              onClick={() => handleAskGemini('ai')}
              disabled={geminiState.loading}
            >
              ✨ Ask Gemini Why
            </button>
            <button 
              className="btn btn-primary"
              onClick={() => handleResolve('ai', primaryRecommendation)}
            >
              Accept Recommendation
            </button>
          </div>

          {geminiState.activeSection === 'ai' && (
            <div className="gemini-box">
              {geminiState.loading ? (
                <div className="loading-pulse">
                  <span>🤖 Gemini is analyzing...</span>
                </div>
              ) : (
                <div className="gemini-response">
                  <pre>{geminiState.analysisText}</pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Tier 2: Manual Control (The Controller) */}
        <div className="option-card manual-option">
          <div className="tier-header">
            <span className="tier-badge tier-2">Tier 2</span>
            <h3>🎮 Manual Control</h3>
            <span className="tier-nickname">The Controller</span>
          </div>

          <form className="manual-form" onSubmit={(e) => e.preventDefault()}>
            <div className="form-group">
              <label htmlFor="flightId">Select Flight</label>
              <select
                id="flightId"
                value={manualForm.flightId}
                onChange={(e) => handleFormChange('flightId', e.target.value)}
              >
                <option value="">-- Select Flight --</option>
                {availableFlights.map(flight => (
                  <option key={flight} value={flight}>{flight}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="actionType">Select Action</label>
              <select
                id="actionType"
                value={manualForm.actionType}
                onChange={(e) => handleFormChange('actionType', e.target.value)}
              >
                <option value="">-- Select Action --</option>
                <option value="altitude">Altitude Change</option>
                <option value="vector">Vector/Heading</option>
                <option value="speed">Speed Adjustment</option>
                <option value="hold">Holding Pattern</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="value">Value</label>
              <input
                type="text"
                id="value"
                placeholder={
                  manualForm.actionType === 'altitude' ? 'e.g., FL350' :
                  manualForm.actionType === 'vector' ? 'e.g., HDG 270' :
                  manualForm.actionType === 'speed' ? 'e.g., M0.82' :
                  manualForm.actionType === 'hold' ? 'e.g., BRAVO fix' :
                  'Enter value...'
                }
                value={manualForm.value}
                onChange={(e) => handleFormChange('value', e.target.value)}
              />
            </div>
          </form>

          <div className="tier-metrics">
            <div className="metric neutral">
              <span className="metric-value">Medium</span>
              <span className="metric-label">Cost</span>
            </div>
            <div className="metric neutral">
              <span className="metric-value">Variable</span>
              <span className="metric-label">Delay</span>
            </div>
            <div className="metric positive">
              <span className="metric-value">Full</span>
              <span className="metric-label">Control</span>
            </div>
          </div>

          <div className="tier-actions">
            <button 
              className="btn btn-gemini"
              onClick={() => handleAskGemini('manual')}
              disabled={geminiState.loading || !manualForm.flightId || !manualForm.actionType}
            >
              🔍 Analyze Risk
            </button>
            <button 
              className="btn btn-secondary"
              onClick={() => handleResolve('manual', manualForm)}
              disabled={!manualForm.flightId || !manualForm.actionType || !manualForm.value}
            >
              Execute Manual Action
            </button>
          </div>

          {geminiState.activeSection === 'manual' && (
            <div className="gemini-box">
              {geminiState.loading ? (
                <div className="loading-pulse">
                  <span>🤖 Gemini is analyzing risks...</span>
                </div>
              ) : (
                <div className="gemini-response warning">
                  <pre>{geminiState.analysisText}</pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Tier 3: Legacy Protocol (The Sledgehammer) */}
        <div className="option-card legacy-option">
          <div className="tier-header">
            <span className="tier-badge tier-3">Tier 3</span>
            <h3>🔨 Legacy Protocol</h3>
            <span className="tier-nickname">The Sledgehammer</span>
          </div>

          <div className="legacy-content">
            <div className="legacy-protocol">
              <h4>Miles-in-Trail (MIT) Restriction</h4>
              <p className="protocol-description">
                Implement a blanket 15 MIT restriction for all traffic entering 
                the affected sector. This is a proven, conservative approach that 
                guarantees separation but at significant cost.
              </p>
            </div>

            <div className="legacy-warning">
              <span className="warning-icon">⚠️</span>
              <span>High impact on traffic flow</span>
            </div>
          </div>

          <div className="tier-metrics">
            <div className="metric negative">
              <span className="metric-value">High</span>
              <span className="metric-label">Cost</span>
            </div>
            <div className="metric negative">
              <span className="metric-value">+12 min</span>
              <span className="metric-label">Avg Delay</span>
            </div>
            <div className="metric neutral">
              <span className="metric-value">Proven</span>
              <span className="metric-label">Reliability</span>
            </div>
          </div>

          <div className="tier-actions">
            <button 
              className="btn btn-warning"
              onClick={() => handleResolve('legacy', { 
                protocol: 'MIT', 
                value: '15 miles',
                affectedSector: contextData?.sector || 'ALL'
              })}
            >
              Implement MIT Restriction
            </button>
          </div>

          <div className="legacy-stats">
            <p>📊 Historical data: Used in 34% of severe congestion events</p>
            <p>💰 Estimated cost: $45,000 - $120,000 in delays</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ResolutionCenter;
