import React, { useEffect, useState } from 'react'
import { MapPin, Thermometer, Droplet, AlertOctagon, SlidersHorizontal, Info, Activity } from 'lucide-react'
import IndonesiaMap from '../components/IndonesiaMap.jsx'

function MapDashboard() {
  const [regions, setRegions] = useState([])
  const [nationalSummary, setNationalSummary] = useState(null)
  const [filterCluster, setFilterCluster] = useState('all')
  const [filterRisk, setFilterRisk] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true)
        setError(null)

        const regRes = await fetch('http://localhost:8000/api/regions')
        if (!regRes.ok) throw new Error('Gagal mengambil daftar wilayah.')
        const regData = await regRes.json()
        setRegions(regData)

        const sumRes = await fetch('http://localhost:8000/api/summary')
        if (sumRes.ok) {
          const sumData = await sumRes.json()
          setNationalSummary(sumData)
        }
      } catch (err) {
        console.error('Gagal memuat dashboard EWS:', err)
        setError('Koneksi gagal! Silakan jalankan FastAPI backend terlebih dahulu.')
      } finally {
        setLoading(false)
      }
    }
    fetchDashboardData()
  }, [])

  // Calculate stats
  const riskCount = regions.filter(r => r.risk_status === 1).length
  const safeCount = regions.filter(r => r.risk_status === 0).length

  return (
    <div className="h-full flex flex-col gap-4 animate-fade-in overflow-hidden">
      
      {/* ── ROW 1: HEADER & KPI CARDS ── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 shrink-0">
        {/* Header Title */}
        <div className="md:col-span-1 flex flex-col justify-center">
          <h1 className="text-2xl font-black text-neutral-900 leading-tight tracking-tight mb-1">
            Peta Risiko <br/>
            <span className="text-sage-600">Ketahanan Pangan</span>
          </h1>
          <p className="text-xs text-neutral-500 font-medium">Pemantauan 33 Provinsi EWS</p>
        </div>

        {/* KPIs */}
        <div className="bento-card p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-neutral-500 uppercase tracking-wider mb-1">Provinsi Aman</div>
            <div className="font-mono text-3xl font-black text-green-600">{loading ? '—' : safeCount}</div>
          </div>
          <div className="w-12 h-12 bg-green-100 rounded-xl border-2 border-neutral-900 shadow-hard-sm flex items-center justify-center shrink-0">
            <Droplet size={24} className="text-green-600" />
          </div>
        </div>
        
        <div className="bento-card p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-neutral-500 uppercase tracking-wider mb-1">Provinsi Risiko</div>
            <div className="font-mono text-3xl font-black text-red-600">{loading ? '—' : riskCount}</div>
          </div>
          <div className="w-12 h-12 bg-red-100 rounded-xl border-2 border-neutral-900 shadow-hard-sm flex items-center justify-center shrink-0">
            <AlertOctagon size={24} className="text-red-600" />
          </div>
        </div>

        <div className="bento-card p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-neutral-500 uppercase tracking-wider mb-1">Suhu Nasional</div>
            <div className="font-mono text-3xl font-black text-blue-600">{loading || !nationalSummary ? '—' : `${nationalSummary.avg_temperature}°`}</div>
          </div>
          <div className="w-12 h-12 bg-blue-100 rounded-xl border-2 border-neutral-900 shadow-hard-sm flex items-center justify-center shrink-0">
            <Thermometer size={24} className="text-blue-600" />
          </div>
        </div>
      </div>

      {/* ── ROW 2: MAP & FILTERS (fills remaining height) ── */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-0">
        
        {/* Map Container (col-span-3) */}
        <div className="lg:col-span-3 bento-card p-4 flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-4 shrink-0">
            <div className="flex items-center gap-2">
              <MapPin size={18} className="text-neutral-900" />
              <h2 className="font-bold text-sm uppercase tracking-wider text-neutral-900">Peta Sebaran Nasional</h2>
            </div>
            
            {/* Legend Map */}
            <div className="hidden sm:flex items-center gap-4 text-xs font-bold font-mono">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 bg-green-600 border-2 border-neutral-900 rounded-full"></span>
                <span>AMAN</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 bg-red-600 border-2 border-neutral-900 rounded-full"></span>
                <span>RISIKO</span>
              </div>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border-2 border-red-500 text-red-700 p-4 rounded-xl flex items-center gap-3 mb-4 font-medium text-sm">
              <AlertOctagon size={20} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex-1 rounded-xl overflow-hidden border-2 border-neutral-900 relative">
            {!loading ? (
              <IndonesiaMap
                regions={regions}
                filterCluster={filterCluster}
                filterRisk={filterRisk}
              />
            ) : (
              <div className="absolute inset-0 bg-neutral-100 flex items-center justify-center text-sm font-mono font-bold text-neutral-500 z-10">
                Memuat data peta...
              </div>
            )}
          </div>
        </div>

        {/* Filter Panel (col-span-1) */}
        <div className="bento-card p-5 flex flex-col gap-6 overflow-y-auto">
          <div className="flex items-center gap-2 border-b-2 border-neutral-100 pb-3 shrink-0">
            <SlidersHorizontal size={18} className="text-neutral-900" />
            <h2 className="font-bold text-sm uppercase tracking-wider text-neutral-900">Kontrol Peta</h2>
          </div>

          <div className="space-y-5">
            <div className="space-y-2">
              <label className="text-xs font-bold text-neutral-500 uppercase tracking-wider">
                Filter Kluster
              </label>
              <select
                className="w-full bento-input"
                value={filterCluster}
                onChange={(e) => setFilterCluster(e.target.value)}
              >
                <option value="all">Semua Kluster</option>
                <option value="0">Cluster 0 (Moderat)</option>
                <option value="1">Cluster 1 (Optimal)</option>
                <option value="2">Cluster 2 (Rentan)</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-neutral-500 uppercase tracking-wider">
                Filter Riwayat Alarm
              </label>
              <select
                className="w-full bento-input"
                value={filterRisk}
                onChange={(e) => setFilterRisk(e.target.value)}
              >
                <option value="all">Semua Tingkat</option>
                <option value="high">Sangat Rawan (≥ 10 Alarm)</option>
                <option value="medium">Sedang (3 – 9 Alarm)</option>
                <option value="low">Sangat Aman (0 – 2 Alarm)</option>
              </select>
            </div>
          </div>

          <div className="mt-auto bg-sage-50 border-2 border-sage-200 rounded-xl p-4 flex items-start gap-3">
            <Info size={20} className="text-sage-600 shrink-0 mt-0.5" />
            <p className="text-xs text-sage-800 font-medium leading-relaxed">
              Hover marker pada peta untuk melihat metrik detail provinsi. Ukuran lingkaran mencerminkan frekuensi historis alarm pangan.
            </p>
          </div>
        </div>

      </div>
    </div>
  )
}

export default MapDashboard
