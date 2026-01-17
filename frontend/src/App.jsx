import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

function App() {
  const [metrics, setMetrics] = useState(null)
  const [geojson, setGeojson] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchAnalysis = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setMetrics(data.metrics)
      setGeojson(data.geojson)
    } catch (err) {
      setError(err.message)
      console.error('Error fetching analysis:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalysis()
  }, [])

  return (
    <div>
        
    </div>
  )
}

export default App
