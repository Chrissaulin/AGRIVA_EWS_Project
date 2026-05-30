import React, { useEffect, useState, useMemo } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

// IMPORTANT WARNING COLORS (SOLID & HIGH CONTRAST)
const RISK_COLORS = {
  0: '#16A34A', // EWS Safe - Green-600
  1: '#DC2626', // EWS Risk - Red-600
}

// Coordinate mapping (same as before)
const PROVINCE_COORDS = {
  'Aceh': [4.6951, 96.7494],
  'Sumatera Utara': [2.1154, 99.5451],
  'Sumatera Barat': [-0.7399, 100.8000],
  'Riau': [0.2933, 101.7068],
  'Jambi': [-1.6110, 103.6131],
  'Sumatera Selatan': [-3.3194, 104.9147],
  'Bengkulu': [-3.7928, 102.2608],
  'Lampung': [-4.5586, 105.1793],
  'Kepulauan Bangka Belitung': [-2.7411, 106.4406],
  'Kepulauan Riau': [3.9456, 108.1429],
  'DKI Jakarta': [-6.2088, 106.8456],
  'Jawa Barat': [-6.9147, 107.6098],
  'Jawa Tengah': [-7.1509, 110.1403],
  'DI Yogyakarta': [-7.7956, 110.3695],
  'Jawa Timur': [-7.5360, 112.2384],
  'Banten': [-6.4058, 106.0640],
  'Bali': [-8.4095, 115.1889],
  'Nusa Tenggara Barat': [-8.6529, 117.3616],
  'Nusa Tenggara Timur': [-8.6574, 121.0794],
  'Kalimantan Barat': [-0.2788, 111.4753],
  'Kalimantan Tengah': [-1.6815, 113.3824],
  'Kalimantan Selatan': [-3.0926, 115.2838],
  'Kalimantan Timur': [0.5387, 116.4194],
  'Kalimantan Utara': [3.0731, 116.0414],
  'Sulawesi Utara': [0.6247, 123.9750],
  'Sulawesi Tengah': [-1.4300, 121.4456],
  'Sulawesi Selatan': [-4.1449, 119.9071],
  'Sulawesi Tenggara': [-4.1449, 122.1746],
  'Gorontalo': [0.6999, 122.4467],
  'Sulawesi Barat': [-2.8441, 119.2321],
  'Maluku': [-3.2385, 130.1453],
  'Maluku Utara': [1.5709, 127.8088],
  'Papua Barat': [-1.3361, 133.1747],
  'Papua': [-4.2699, 138.0804]
}

function MapController({ center, zoom }) {
  const map = useMap()
  useEffect(() => { map.setView(center, zoom) }, [center, zoom, map])
  return null
}

function IndonesiaMap({ regions, filterCluster, filterRisk }) {
  const defaultCenter = [-2.5, 118.0]
  const defaultZoom = 5

  const mapData = useMemo(() => {
    return regions
      .map(r => ({
        ...r,
        coords: PROVINCE_COORDS[r.region_name] || null
      }))
      .filter(r => r.coords !== null)
      .filter(r => filterCluster === 'all' || r.cluster_wilayah.toString() === filterCluster)
      .filter(r => {
        if (filterRisk === 'all') return true
        if (filterRisk === 'high') return r.total_historical_warnings >= 10
        if (filterRisk === 'medium') return r.total_historical_warnings >= 3 && r.total_historical_warnings <= 9
        if (filterRisk === 'low') return r.total_historical_warnings <= 2
        return true
      })
  }, [regions, filterCluster, filterRisk])

  return (
    <MapContainer
      center={defaultCenter}
      zoom={defaultZoom}
      zoomControl={true}
      style={{ width: '100%', height: '100%', background: '#f8fafc', zIndex: 0 }}
      attributionControl={false}
    >
      <MapController center={defaultCenter} zoom={defaultZoom} />
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />

      {mapData.map((reg, idx) => {
        const isWarning = reg.risk_status === 1
        const fillColor = isWarning ? RISK_COLORS[1] : RISK_COLORS[0]
        
        // Base radius is 8, grows up to +12 based on historical warnings
        const baseRadius = 8
        const dynamicRadius = baseRadius + Math.min(12, (reg.total_historical_warnings || 0) * 1.5)

        return (
          <CircleMarker
            key={idx}
            center={reg.coords}
            radius={dynamicRadius}
            pathOptions={{
              fillColor: fillColor,
              fillOpacity: 0.9,
              color: '#171717', // Neutral 900 border
              weight: 2,
            }}
          >
            <Tooltip
              direction="top"
              offset={[0, -10]}
              opacity={1}
              className="custom-leaflet-tooltip"
            >
              <div className="p-3 min-w-[200px]">
                <div className="flex items-center justify-between mb-2 pb-2 border-b-2 border-neutral-100">
                  <h4 className="font-black text-neutral-900 text-sm tracking-tight">{reg.region_name}</h4>
                  <span className={`px-1.5 py-0.5 rounded border-2 border-neutral-900 text-[10px] font-bold shadow-[2px_2px_0px_0px_#171717] ${isWarning ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>
                    {isWarning ? 'RISIKO' : 'AMAN'}
                  </span>
                </div>
                
                <div className="space-y-1.5 text-xs text-neutral-600 font-medium">
                  <div className="flex justify-between items-center">
                    <span>Cluster Identitas:</span>
                    <span className="font-mono font-bold bg-neutral-100 text-neutral-900 px-1 rounded border border-neutral-200">
                      C-{reg.cluster_wilayah}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>Total Alarm Historis:</span>
                    <span className="font-mono font-bold text-neutral-900">
                      {reg.total_historical_warnings || 0}x
                    </span>
                  </div>
                </div>
              </div>
            </Tooltip>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}

export default IndonesiaMap
