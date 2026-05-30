import React, { useEffect, useState } from 'react'
import { Sliders, Sparkles, AlertOctagon, Loader2, Zap, ChevronRight, Activity } from 'lucide-react'
import confetti from 'canvas-confetti'

const VARIABLES_METRICS = [
  { id: 'rainfall',     label: 'Curah Hujan',        min: 0,    max: 300,    step: 1,   defaultVal: 80,     unit: 'mm',   desc: 'Akumulasi curah hujan bulanan' },
  { id: 'spi_3m',       label: 'SPI 3 Bulan',        min: -3.0, max: 3.0,   step: 0.1, defaultVal: 0.0,    unit: '',     desc: 'Standardized Precipitation Index' },
  { id: 'temperature',  label: 'Suhu Rata-rata',      min: 15.0, max: 40.0,  step: 0.5, defaultVal: 26.5,   unit: '°C',   desc: 'Suhu lingkungan tanaman' },
  { id: 'wsi',          label: 'WSI',                 min: 0,    max: 100,   step: 1,   defaultVal: 85,     unit: '%',    desc: 'Water Satisfaction Index' },
  { id: 'solar_radiation', label: 'Radiasi Matahari', min: 50000, max: 400000, step: 1000, defaultVal: 180000, unit: 'J/m²', desc: 'Energi radiasi' },
  { id: 'soil_moisture', label: 'Kelembaban Tanah',   min: 0.0,  max: 1.0,   step: 0.01, defaultVal: 0.35,  unit: '',     desc: 'Kadar air tanah (0-1)' },
  { id: 'fpar',          label: 'FPAR Vegetasi',      min: 0,    max: 100,   step: 1,   defaultVal: 65,     unit: '%',    desc: 'Fraction Photosynthetically Active' },
  { id: 'fpar_zscore',   label: 'FPAR Z-Score',       min: -3.0, max: 3.0,   step: 0.1, defaultVal: 0.2,   unit: '',     desc: 'Deviasi kesehatan tanaman' },
]

const MONTHS = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember']

function Simulation() {
  const [regions, setRegions]         = useState([])
  const [selectedRegion, setSelectedRegion] = useState('Jawa Timur')
  const [simulationInputs, setSimulationInputs] = useState(
    VARIABLES_METRICS.reduce((acc, v) => { acc[v.id] = v.defaultVal; return acc }, {})
  )
  const [simulationMonth, setSimulationMonth] = useState(5)
  const [predictionResult, setPredictionResult] = useState(null)
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState(null)

  useEffect(() => {
    fetch('http://localhost:8000/api/regions')
      .then(r => r.ok ? r.json() : [])
      .then(data => setRegions(data))
      .catch(console.error)
  }, [])

  const handleSliderChange = (id, val) =>
    setSimulationInputs(prev => ({ ...prev, [id]: parseFloat(val) }))

  const handleRunSimulation = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setPredictionResult(null)
    try {
      const res = await fetch('http://localhost:8000/api/simulate/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          region_name: selectedRegion,
          ...simulationInputs,
          month: simulationMonth,
        }),
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setPredictionResult(data)
      if (!data.is_warning) {
        confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 }, colors: ['#22c55e', '#86efac', '#facc15'] })
      }
    } catch {
      setError('Gagal terhubung ke API Simulasi. Pastikan uvicorn server telah aktif.')
    } finally {
      setLoading(false)
    }
  }

  /* ── SVG Semicircular Dial (Soft Brutalism Style) ── */
  const renderDial = (probability, threshold) => {
    const R = 90
    const circ = 2 * Math.PI * R
    const arc = circ / 2
    const offset = arc - probability * arc
    const thAngle = threshold * 180 - 180
    const isRisk = probability >= threshold
    
    // EWS Solid colors
    const color = isRisk ? '#dc2626' : '#16a34a' 
    const bgColor = '#e5e5e5'

    return (
      <svg width="240" height="140" viewBox="0 0 240 140" className="overflow-visible">
        {/* BG arc */}
        <path d="M 30,120 A 90,90 0 0,1 210,120" fill="none" stroke={bgColor} strokeWidth="18" strokeLinecap="round" />
        {/* Value arc */}
        <path d="M 30,120 A 90,90 0 0,1 210,120" fill="none" stroke={color} strokeWidth="18"
          strokeLinecap="round" strokeDasharray={arc} strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
        {/* Threshold needle */}
        <g transform={`translate(120,120) rotate(${thAngle})`}>
          <line x1="0" y1="0" x2="-98" y2="0" stroke="#171717" strokeWidth="3" strokeDasharray="4 2" />
          <rect x="-103" y="-5" width="10" height="10" fill="#171717" rx="2" />
        </g>
        {/* Threshold label */}
        <text
          x={120 + 78 * Math.cos((thAngle * Math.PI) / 180)}
          y={120 + 78 * Math.sin((thAngle * Math.PI) / 180) - 14}
          fill="#525252" fontSize="10" fontWeight="bold" textAnchor="middle" className="font-mono"
        >
          {Math.round(threshold * 100)}%
        </text>
      </svg>
    )
  }

  return (
    <div className="h-full flex flex-col gap-4 animate-fade-in overflow-hidden pb-4">

      {/* ── HEADER ── */}
      <div className="shrink-0">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-white border-2 border-neutral-900 rounded-lg text-xs font-bold uppercase tracking-wider text-neutral-900 shadow-hard-sm mb-3">
          <Zap size={14} className="text-yellow-500" /> Simulator EWS
        </div>
        <h1 className="text-3xl md:text-4xl font-black text-neutral-900 leading-tight tracking-tight">
          Simulator Skenario <span className="text-sage-600">Bahaya</span>
        </h1>
        <p className="text-neutral-600 font-medium max-w-2xl mt-2 text-sm">
          Ubah parameter pertanian (suhu, curah hujan, vegetasi) secara interaktif untuk memprediksi ancaman ketahanan pangan secara instan dengan klasifikasi biner AI.
        </p>
      </div>

      {/* ── MAIN CONTENT (Split 2 Cols) ── */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">

        {/* ── LEFT COL: Parameter Inputs ── */}
        <div className="bento-card flex flex-col min-h-0 bg-white">
          <div className="p-5 border-b-2 border-neutral-100 flex items-center gap-2 shrink-0">
            <Sliders size={20} className="text-neutral-900" />
            <h2 className="font-black text-base uppercase tracking-wider text-neutral-900">Parameter Input</h2>
          </div>

          <div className="flex-1 overflow-y-auto p-5">
            <form onSubmit={handleRunSimulation} className="space-y-6">

              {/* Selectors */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-neutral-500 uppercase tracking-wider">Provinsi</label>
                  <select className="w-full bento-input" value={selectedRegion} onChange={(e) => setSelectedRegion(e.target.value)}>
                    {regions.map(r => <option key={r.region_name} value={r.region_name}>{r.region_name}</option>)}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-neutral-500 uppercase tracking-wider">Bulan</label>
                  <select className="w-full bento-input" value={simulationMonth} onChange={(e) => setSimulationMonth(parseInt(e.target.value))}>
                    {MONTHS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
                  </select>
                </div>
              </div>

              {/* Sliders Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5">
                {VARIABLES_METRICS.map(v => (
                  <div key={v.id} className="space-y-2">
                    <div className="flex justify-between items-end">
                      <span className="text-xs font-bold text-neutral-600">{v.label}</span>
                      <span className="text-xs font-mono font-bold text-sage-700 bg-sage-100 px-1.5 py-0.5 rounded border border-sage-200">
                        {simulationInputs[v.id].toLocaleString()} {v.unit}
                      </span>
                    </div>
                    <input
                      type="range" className="range-slider"
                      min={v.min} max={v.max} step={v.step}
                      value={simulationInputs[v.id]}
                      onChange={(e) => handleSliderChange(v.id, e.target.value)}
                    />
                  </div>
                ))}
              </div>

              {/* Submit Button */}
              <button
                type="submit" 
                className="w-full bento-button mt-4"
                disabled={loading}
              >
                {loading ? (
                  <><Loader2 size={18} className="animate-spin" /><span>Menganalisis...</span></>
                ) : (
                  <><Sparkles size={18} /><span>Jalankan Simulasi Deteksi</span><ChevronRight size={16} /></>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* ── RIGHT COL: Prediction Output ── */}
        <div className="flex flex-col min-h-0 gap-6">

          {error && (
            <div className="bg-red-50 border-2 border-red-500 text-red-700 p-4 rounded-2xl flex items-center gap-3 font-medium text-sm shadow-hard-sm shrink-0">
              <AlertOctagon size={20} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Empty State */}
          {!predictionResult && !loading && !error && (
            <div className="bento-card flex-1 flex flex-col items-center justify-center p-8 text-center bg-neutral-50/50">
              <div className="w-20 h-20 bg-white border-2 border-neutral-200 rounded-2xl flex items-center justify-center mb-4 shadow-sm">
                <Activity size={32} className="text-neutral-300" />
              </div>
              <h3 className="text-lg font-black text-neutral-700 mb-2">Menunggu Input Parameter</h3>
              <p className="text-sm text-neutral-500 max-w-sm font-medium">
                Sesuaikan slider parameter iklim dan vegetasi di panel sebelah kiri, lalu jalankan simulasi untuk melihat prediksi AI.
              </p>
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="bento-card flex-1 flex flex-col items-center justify-center p-8 text-center bg-white border-sage-400">
              <Loader2 size={48} className="text-sage-500 animate-spin mb-4" />
              <h3 className="text-lg font-black text-neutral-900 mb-2">Memproses Model XGBoost...</h3>
              <p className="text-sm text-neutral-500 max-w-sm font-medium">
                Mengevaluasi input terhadap batas optimal kluster wilayah...
              </p>
            </div>
          )}

          {/* Result State */}
          {predictionResult && !loading && (
            <div className={`bento-card flex-1 flex flex-col items-center justify-center p-6 text-center transition-all duration-500 ${predictionResult.is_warning ? 'bg-red-50/30 border-red-500' : 'bg-green-50/30 border-green-500'}`}>
              
              <div className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">
                Status Kerawanan Pangan
              </div>

              <div className={`text-4xl md:text-5xl font-black mb-8 px-6 py-2 rounded-2xl border-4 shadow-hard ${predictionResult.is_warning ? 'bg-red-600 text-white border-neutral-900' : 'bg-green-600 text-white border-neutral-900'}`}>
                {predictionResult.status_label}
              </div>

              <div className="relative flex flex-col items-center mb-6">
                {renderDial(predictionResult.probability, predictionResult.threshold_used)}
                <div className="-mt-10 flex flex-col items-center">
                  <span className={`text-5xl font-black font-mono leading-none ${predictionResult.is_warning ? 'text-red-600' : 'text-green-600'}`}>
                    {Math.round(predictionResult.probability * 100)}<span className="text-2xl">%</span>
                  </span>
                  <span className="text-xs font-bold text-neutral-500 uppercase tracking-widest mt-1">Peluang Bahaya</span>
                </div>
              </div>

              <div className="w-full max-w-md bg-white border-2 border-neutral-900 rounded-xl p-4 text-left shadow-hard-sm space-y-3">
                <div className="flex justify-between items-center border-b-2 border-neutral-100 pb-2">
                  <span className="text-xs font-bold text-neutral-500 uppercase">Provinsi Target</span>
                  <span className="text-sm font-bold text-neutral-900">{predictionResult.region_name}</span>
                </div>
                <div className="flex justify-between items-center border-b-2 border-neutral-100 pb-2">
                  <span className="text-xs font-bold text-neutral-500 uppercase">Karakteristik</span>
                  <span className="text-xs font-bold font-mono bg-neutral-100 px-2 py-1 rounded">Cluster {predictionResult.cluster_wilayah}</span>
                </div>
                <div className="pt-1">
                  <p className="text-xs font-medium text-neutral-600 leading-relaxed">
                    {predictionResult.is_warning 
                      ? `⚠️ Prediksi bahaya melampaui ambang toleransi kluster (${Math.round(predictionResult.threshold_used * 100)}%). Kondisi kritis terdeteksi!`
                      : `✅ Indikator berada dalam zona stabil, di bawah ambang batas bahaya (${Math.round(predictionResult.threshold_used * 100)}%).`}
                  </p>
                </div>
              </div>

            </div>
          )}

        </div>
      </div>
    </div>
  )
}

export default Simulation
