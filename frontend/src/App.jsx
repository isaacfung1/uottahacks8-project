import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

// Fix for default marker icons
import icon from 'leaflet/dist/images/marker-icon.png'
import iconShadow from 'leaflet/dist/images/marker-shadow.png'

let DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41]
})
L.Marker.prototype.options.icon = DefaultIcon

const API_BASE = 'http://localhost:8000'

// Timeline Chart Component
function TimelineChart({ hotspots, selectedBin, capacity, predictedLoads }) {
  const chartHeight = 200
  const chartWidth = hotspots.length * 40
  const padding = { top: 20, right: 20, bottom: 40, left: 60 }
  const innerWidth = chartWidth - padding.left - padding.right
  const innerHeight = chartHeight - padding.top - padding.bottom
  
  const maxCount = Math.max(...hotspots.map(h => h.legacy_count), capacity * 2)
  const scale = innerHeight / maxCount
  
  return (
    <div className="timeline-chart-container" style={{ overflowX: 'auto' }}>
      <svg width={chartWidth} height={chartHeight} className="timeline-chart">
        <g transform={`translate(${padding.left},${padding.top})`}>
          {/* Capacity line */}
          <line
            x1={0}
            y1={innerHeight - capacity * scale}
            x2={innerWidth}
            y2={innerHeight - capacity * scale}
            stroke="#28a745"
            strokeWidth={2}
            strokeDasharray="4,4"
          />
          <text
            x={-5}
            y={innerHeight - capacity * scale}
            fill="#28a745"
            fontSize="10"
            textAnchor="end"
            dominantBaseline="middle"
          >
            Capacity
          </text>
          
          {/* Bars for legacy count */}
          {hotspots.map((hotspot, idx) => {
            const x = (idx * innerWidth) / hotspots.length
            const width = innerWidth / hotspots.length - 2
            const height = hotspot.legacy_count * scale
            const isSelected = selectedBin === hotspot.bin_start
            
            return (
              <g key={idx}>
                <rect
                  x={x}
                  y={innerHeight - height}
                  width={width}
                  height={height}
                  fill={isSelected ? "#d32f2f" : "#ff6b6b"}
                  stroke={isSelected ? "#000" : "none"}
                  strokeWidth={isSelected ? 2 : 0}
                  opacity={isSelected ? 1 : 0.7}
                />
                {/* Predicted load line */}
                {predictedLoads[idx] && (
                  <line
                    x1={x + width / 2}
                    y1={innerHeight - predictedLoads[idx] * scale}
                    x2={x + width / 2 + innerWidth / hotspots.length}
                    y2={innerHeight - predictedLoads[idx] * scale}
                    stroke="#0066ff"
                    strokeWidth={2}
                  />
                )}
                {/* Time labels */}
                {idx % 3 === 0 && (
                  <text
                    x={x + width / 2}
                    y={innerHeight + 15}
                    fill="#666"
                    fontSize="9"
                    textAnchor="middle"
                  >
                    {new Date(hotspot.bin_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </text>
                )}
              </g>
            )
          })}
          
          {/* Y-axis labels */}
          {[0, maxCount * 0.5, maxCount].map((val) => (
            <g key={val}>
              <line
                x1={-5}
                y1={innerHeight - val * scale}
                x2={0}
                y2={innerHeight - val * scale}
                stroke="#ccc"
                strokeWidth={1}
              />
              <text
                x={-10}
                y={innerHeight - val * scale}
                fill="#666"
                fontSize="10"
                textAnchor="end"
                dominantBaseline="middle"
              >
                {val.toFixed(0)}
              </text>
            </g>
          ))}
        </g>
      </svg>
      <div className="timeline-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#ff6b6b' }}></span>
          Legacy Count
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#0066ff' }}></span>
          Predicted Load
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#28a745', border: '1px dashed #000' }}></span>
          Capacity
        </div>
      </div>
    </div>
  )
}

// Component to fit bounds when data changes
function FitBounds({ geojson }) {
  const map = useMap()
  
  useEffect(() => {
    if (geojson && geojson.features && geojson.features.length > 0) {
      const geoJsonLayer = L.geoJSON(geojson)
      const bounds = geoJsonLayer.getBounds()
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [50, 50] })
      }
    }
  }, [geojson, map])
  
  return null
}

// Zoom to selected hotspot
function HotspotZoom({ selectedBin, hotspotGeojson }) {
  const map = useMap()

  useEffect(() => {
    if (!selectedBin || !hotspotGeojson?.features?.length) {
      return
    }

    const match = hotspotGeojson.features.find(
      (feature) => feature?.properties?.bin_start === selectedBin
    )

    if (match?.geometry?.type === 'Point') {
      const [lng, lat] = match.geometry.coordinates
      map.flyTo([lat, lng], 9, { duration: 0.8 })
    }
  }, [selectedBin, hotspotGeojson, map])

  return null
}

// Styled GeoJSON component for flights
function FlightGeoJSON({ data }) {
  const pointToLayer = (feature, latlng) => {
    return L.circleMarker(latlng, { radius: 4 })
  }
  
  const style = (feature) => {
    const props = feature.properties
    let color = '#0066FF'
    let weight = 1.5
    let opacity = 1.0
    let dashArray = null

    const arrivalProb = Math.max(0.1, Math.min(1, props.arrival_probability ?? 0.85))
    opacity = arrivalProb
    
    if (props.rerouted_flag) {
      color = '#FFA500'
      weight = 3
      dashArray = '5, 5'
    } else if (props.in_hotspot_bin) {
      color = '#FF0000'
      weight = 2.5
    } else if (props.ghost_flag) {
      color = '#CCCCCC'
      weight = 1
    }
    
    return {
      color,
      weight,
      opacity,
      dashArray
    }
  }
  
  return data ? <GeoJSON data={data} style={style} /> : null
}

// Sector overlay component
function SectorOverlay({ data }) {
  const style = (feature) => {
    return {
      fillColor: '#FF6B6B',
      fillOpacity: 0.2,
      color: '#FF6B6B',
      weight: 2
    }
  }
  
  return data ? <GeoJSON data={data} style={style} /> : null
}

// Hotspot overlay component
function HotspotGeoJSON({ data }) {
  const pointToLayer = (feature, latlng) => {
    const baseRadius = feature?.properties?.radius ?? 8
    const radius = baseRadius + 3
    const severityRaw = feature?.properties?.severity
    const severity = Number.isFinite(Number(severityRaw)) ? Number(severityRaw) : 0
    let color = '#28a745'
    if (severity >= 85) {
      color = '#FF0000'
    } else if (severity >= 60) {
      color = '#FFC107'
    }
    return L.circleMarker(latlng, {
      radius,
      color,
      weight: 2,
      fillColor: color,
      fillOpacity: 0.35
    })
  }
  const onEachFeature = (feature, layer) => {
    const props = feature?.properties || {}
    const content = `
      <div>
        <strong>Hotspot</strong><br />
        Center: center of activity for this time window<br />
        Time: ${props.bin_start ? new Date(props.bin_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A'}<br />
        Count: ${props.legacy_count ?? 'N/A'}<br />
        Weighted Load: ${props.weighted_load?.toFixed ? props.weighted_load.toFixed(2) : 'N/A'}<br />
        Severity: ${props.severity?.toFixed ? props.severity.toFixed(0) : 'N/A'}%
      </div>
    `
    layer.bindTooltip(content, { sticky: true })
  }

  return data ? <GeoJSON data={data} pointToLayer={pointToLayer} onEachFeature={onEachFeature} /> : null
}

function App() {
  const [analysisData, setAnalysisData] = useState(null)
  const [selectedFlight, setSelectedFlight] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedBin, setSelectedBin] = useState(null)

  useEffect(() => {
    loadAnalysisData()
  }, [selectedBin])

  const loadAnalysisData = async () => {
    try {
      setLoading(true)
      const url = selectedBin 
        ? `${API_BASE}/analyze?bin=${encodeURIComponent(selectedBin)}`
        : `${API_BASE}/analyze`
      
      const response = await fetch(url)
      if (!response.ok) throw new Error('Failed to load data')
      
      const data = await response.json()
      setAnalysisData(data)
      setError(null)
    } catch (err) {
      setError(err.message)
      console.error('Error loading data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleHotspotSelect = (binStart) => {
    setSelectedBin(binStart)
  }

  const handleApprovePlan = async () => {
    if (!analysisData || !analysisData.recommended_actions || analysisData.recommended_actions.length === 0) {
      return
    }

    try {
      const response = await fetch(`${API_BASE}/plan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          selected_hotspot_id: selectedBin || analysisData.selected_hotspot?.bin_start,
          approved_actions: analysisData.recommended_actions.map(a => ({
            acid: a.acid,
            action_type: a.action_type
          }))
        })
      })

      if (!response.ok) throw new Error('Failed to apply plan')
      
      const data = await response.json()
      setAnalysisData(data)
    } catch (err) {
      setError(err.message)
      console.error('Error applying plan:', err)
    }
  }

  if (loading && !analysisData) {
    return <div className="loading">Loading flight data...</div>
  }

  if (error) {
    return <div className="error">Error: {error}</div>
  }

  if (!analysisData) {
    return <div className="error">No data available</div>
  }

  const { map_geojson, sector_geojson, hotspot_geojson, hotspots, metrics, recommended_actions, flights_in_hotspot } = analysisData

  return (
    <div className="app">
      <header className="app-header">
        <h1>SkyFlow - Air Traffic Management</h1>
      </header>
      
      <div className="app-layout">
        {/* Left Sidebar */}
        <aside className="sidebar">
          {/* Metrics Dashboard */}
          <div className="metrics-section">
            <h2>Legacy vs SkyFlow</h2>
            
            <div className="metric-card legacy">
              <h3>Legacy System</h3>
              <div className="metric-value">
                {metrics.legacy.count} / {metrics.legacy.capacity.toFixed(1)}
              </div>
              <div className={`status-badge ${metrics.legacy.status.toLowerCase()}`}>
                {metrics.legacy.status}
              </div>
              <p className="recommendation">{metrics.legacy.recommendation}</p>
            </div>

            <div className="metric-card skyflow">
              <h3>SkyFlow</h3>
              <div className="metric-value">
                {metrics.skyflow.predicted_load.toFixed(1)} / {metrics.skyflow.capacity.toFixed(1)}
              </div>
              <div className={`status-badge ${metrics.skyflow.status.toLowerCase()}`}>
                {metrics.skyflow.status}
              </div>
              <p className="recommendation">{metrics.skyflow.recommendation}</p>
            </div>
          </div>

          {/* Hotspot List */}
          <div className="hotspot-section">
            <h2>Hotspots</h2>
            <div className="hotspot-list">
              {hotspots && hotspots.slice(0, 10).map((hotspot, idx) => (
                <div
                  key={idx}
                  className={`hotspot-item ${selectedBin === hotspot.bin_start ? 'selected' : ''}`}
                  onClick={() => handleHotspotSelect(hotspot.bin_start)}
                >
                  <div className="hotspot-time">
                    {new Date(hotspot.bin_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                  <div className="hotspot-metrics">
                    <span className="count">{hotspot.legacy_count}</span>
                    <span className="severity">Severity: {hotspot.severity.toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recommended Actions */}
          {recommended_actions && recommended_actions.length > 0 && (
            <div className="recommendations-section">
              <h2>Recommended Actions</h2>
              <div className="recommendations-list">
                {recommended_actions.map((action, idx) => (
                  <div key={idx} className="recommendation-item">
                    <div className="recommendation-acid">{action.acid}</div>
                    <div className="recommendation-action">{action.action_type}</div>
                    <div className="recommendation-score">Score: {action.score.toFixed(2)}</div>
                    <ul className="recommendation-explanations">
                      {action.explanations.map((exp, i) => (
                        <li key={i}>{exp}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
              <button className="approve-button" onClick={handleApprovePlan}>
                Approve Plan
              </button>
            </div>
          )}
        </aside>

        {/* Main Content Area */}
        <main className="main-content">
          {/* Map */}
          <div className="map-container">
            <MapContainer
              center={[45.42, -75.69]}
              zoom={6}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />
              <FitBounds geojson={map_geojson} />
              <HotspotZoom selectedBin={selectedBin} hotspotGeojson={hotspot_geojson} />
              <SectorOverlay data={sector_geojson} />
              <FlightGeoJSON data={map_geojson} />
              <HotspotGeoJSON data={hotspot_geojson} />
            </MapContainer>
          </div>

          {/* Timeline Chart */}
          {hotspots && hotspots.length > 0 && (
            <div className="timeline-section">
              <h2>Demand Timeline</h2>
              <TimelineChart 
                hotspots={hotspots.slice(0, 20)} 
                selectedBin={selectedBin}
                capacity={metrics.legacy.capacity}
                predictedLoads={hotspots.slice(0, 20).map(h => {
                  // For simplicity, estimate predicted load (in real app, calculate from flights)
                  return h.legacy_count * 0.85 // Rough estimate
                })}
              />
            </div>
          )}

          {/* Flight List */}
          <div className="flight-list-section">
            <h2>Flights in Hotspot</h2>
            <div className="flight-table-container">
              <table className="flight-table">
                <thead>
                  <tr>
                    <th>ACID</th>
                    <th>Type</th>
                    <th>Passengers</th>
                    <th>Cargo</th>
                    <th>Arrival Prob</th>
                    <th>Ghost</th>
                    <th>Cost Index</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {flights_in_hotspot && flights_in_hotspot.map((flight, idx) => (
                    <tr
                      key={idx}
                      className={`flight-row ${flight.is_recommended ? 'recommended' : ''} ${flight.ghost_flag ? 'ghost' : ''}`}
                      onClick={() => setSelectedFlight(flight)}
                    >
                      <td>{flight.acid}</td>
                      <td>{flight.plane_type}</td>
                      <td>{flight.passengers}</td>
                      <td>{flight.is_cargo ? 'Yes' : 'No'}</td>
                      <td>{(flight.arrival_probability * 100).toFixed(0)}%</td>
                      <td>{flight.ghost_flag ? '⚠️' : ''}</td>
                      <td>{flight.cost_index.toFixed(1)}</td>
                      <td>{flight.is_recommended ? '⭐ Recommended' : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </main>

        {/* Right Sidebar - Flight Details */}
        {selectedFlight && (
          <aside className="details-sidebar">
            <h2>Flight Details</h2>
            <button className="close-button" onClick={() => setSelectedFlight(null)}>×</button>
            <div className="flight-details">
              <div className="detail-row">
                <strong>ACID:</strong> {selectedFlight.acid}
              </div>
              <div className="detail-row">
                <strong>Aircraft:</strong> {selectedFlight.plane_type}
              </div>
              <div className="detail-row">
                <strong>Passengers:</strong> {selectedFlight.passengers}
              </div>
              <div className="detail-row">
                <strong>Cargo:</strong> {selectedFlight.is_cargo ? 'Yes' : 'No'}
              </div>
              <div className="detail-row">
                <strong>Arrival Probability:</strong> {(selectedFlight.arrival_probability * 100).toFixed(1)}%
              </div>
              <div className="detail-row">
                <strong>Cost Index:</strong> {selectedFlight.cost_index.toFixed(1)}
              </div>
              {selectedFlight.ghost_flag && (
                <div className="detail-row warning">
                  ⚠️ Flagged as ghost flight (low arrival probability)
                </div>
              )}
              <div className="explanations-section">
                <h3>Explanations</h3>
                <ul>
                  {selectedFlight.explanations && selectedFlight.explanations.map((exp, i) => (
                    <li key={i}>{exp}</li>
                  ))}
                </ul>
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  )
}

export default App
