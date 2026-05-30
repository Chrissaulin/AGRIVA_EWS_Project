import React, { useEffect, useState, useCallback } from 'react'
import {
  TrendingUp, ChevronRight, AlertOctagon, Loader2,
  BarChart3, CloudRain, Thermometer, Droplets, Wind,
} from 'lucide-react'
import {
  ResponsiveContainer, AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'

/* ── Custom Tooltip for charts ── */
const NbTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null
  const d = new Date(label)
  const dateStr = isNaN(d) ? label : d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: '2-digit' })
  return (
    <div className="bg-white border-2 border-neutral-900 p-3 shadow-[4px_4px_0px_0px_rgba(23,23,23,1)] font-sans text-xs min-w-[160px] rounded-xl z-50">
      <p className="font-bold text-neutral-900 mb-2 border-b-2 border-neutral-100 pb-1 font-mono">{dateStr}</p>
      <div className="space-y-1.5">
        {payload.map((item, i) => (
          <div key={i} className="flex justify-between gap-4" style={{ color: item.color }}>
            <span className="font-medium">{item.name}:</span>
            <strong className="font-mono font-bold text-neutral-900">
              {typeof item.value === 'number' ? item.value.toFixed(2) : item.value}
            </strong>
          </div>
        ))}
      </div>
    </div>
  )
}

function Statistics() {
  const [regions, setRegions]           = useState([])
  const [selectedRegion, setSelectedRegion] = useState('Jawa Timur')
  const [trendsData, setTrendsData]     = useState([])
  const [forecastSteps, setForecastSteps] = useState(5)
  const [forecastData, setForecastData] = useState([])
  const [combinedChartData, setCombinedChartData] = useState([])
  const [loadingTrends, setLoadingTrends] = useState(true)
  const [loadingForecast, setLoadingForecast] = useState(false)
  const [error, setError]               = useState(null)

  /* ── Fetch regions list ── */
  useEffect(() => {
    fetch('http://localhost:8000/api/regions')
      .then(r => r.ok ? r.json() : [])
      .then(data => setRegions(data))
      .catch(console.error)
  }, [])

  /* ── Fetch historical trends ── */
  const fetchTrends = useCallback(async (name) => {
    try {
      setLoadingTrends(true)
      setError(null)
      setForecastData([])
      setCombinedChartData([])
      const res = await fetch(`http://localhost:8000/api/trends/${encodeURIComponent(name)}`)
      if (!res.ok) throw new Error()
      setTrendsData(await res.json())
    } catch {
      setError('Gagal memuat data tren. Pastikan backend online.')
    } finally {
      setLoadingTrends(false)
    }
  }, [])

  useEffect(() => { if (selectedRegion) fetchTrends(selectedRegion) }, [selectedRegion, fetchTrends])

  /* ── Run forecast ── */
  const handleRunForecast = async () => {
    setLoadingForecast(true)
    try {
      const res = await fetch('http://localhost:8000/api/simulate/forecast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region_name: selectedRegion, steps: forecastSteps }),
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setForecastData(data.forecasts)

      const recent = trendsData.slice(-12).map(h => ({ ...h, isForecast: false }))
      const mapped = data.forecasts.map(f => ({
        date: f.date, rainfall: f.rainfall, temperature: f.temperature,
        fpar: f.fpar, soil_moisture: f.soil_moisture, isForecast: true,
      }))
      if (recent.length > 0 && mapped.length > 0) {
        mapped.unshift({ ...recent[recent.length - 1], isForecast: true })
      }
      setCombinedChartData([...recent, ...mapped])
    } catch {
      setError('Gagal memproses peramalan.')
    } finally {
      setLoadingForecast(false)
    }
  }

  const latest = trendsData[trendsData.length - 1] || null

  return (
    <div className="h-full flex flex-col gap-4 animate-fade-in overflow-hidden">

      {/* ── ROW 1: HEADER & CONTROLS ── */}
      <div className="flex flex-col lg:flex-row gap-4 justify-between items-start lg:items-end shrink-0">
        
        <div>
          <div className="text-xs font-bold text-neutral-500 uppercase tracking-wider mb-1">Dashboard Analitik</div>
          <h1 className="text-2xl font-black text-neutral-900 leading-tight tracking-tight">
            Tren Historis &amp; <span className="text-sage-600">Peramalan AI</span>
          </h1>
        </div>

        <div className="flex flex-wrap items-end gap-3 w-full lg:w-auto">
          {/* Province select */}
          <div className="flex-1 lg:flex-none min-w-[200px]">
            <label className="block text-[10px] font-bold text-neutral-500 uppercase tracking-wider mb-1">
              Provinsi
            </label>
            <select
              className="w-full bento-input"
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
            >
              {regions.map(r => (
                <option key={r.region_name} value={r.region_name}>
                  {r.region_name} · C{r.cluster_wilayah}
                </option>
              ))}
            </select>
          </div>

          {/* Forecast steps */}
          <div className="flex-1 lg:flex-none min-w-[160px] bg-white border-2 border-neutral-900 rounded-xl px-4 py-2 shadow-hard-sm">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Horizon</span>
              <span className="text-[10px] font-mono font-bold bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded border border-blue-200">
                {forecastSteps} Dekad
              </span>
            </div>
            <input
              type="range" className="range-slider"
              min={1} max={12} value={forecastSteps}
              onChange={(e) => setForecastSteps(parseInt(e.target.value))}
            />
          </div>

          {/* Run button */}
          <button
            className="bento-button whitespace-nowrap h-[44px]"
            onClick={handleRunForecast}
            disabled={loadingForecast || loadingTrends}
          >
            {loadingForecast ? (
              <><Loader2 size={16} className="animate-spin" /><span>Meramal...</span></>
            ) : (
              <><BarChart3 size={16} /><span>Jalankan Ramalan</span><ChevronRight size={14} /></>
            )}
          </button>
        </div>
      </div>

      {/* ── ROW 2: KPI PILLS ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 shrink-0">
        {[
          { label: 'Curah Hujan', value: latest ? `${parseFloat(latest.rainfall).toFixed(1)} mm` : '—', icon: <CloudRain size={18} />, bg: 'bg-blue-50', text: 'text-blue-600' },
          { label: 'Suhu', value: latest ? `${parseFloat(latest.temperature).toFixed(1)} °C` : '—', icon: <Thermometer size={18} />, bg: 'bg-yellow-50', text: 'text-yellow-600' },
          { label: 'Soil Moisture', value: latest ? parseFloat(latest.soil_moisture).toFixed(3) : '—', icon: <Droplets size={18} />, bg: 'bg-sage-50', text: 'text-sage-600' },
          { label: 'Ramalan Aktif', value: forecastData.length > 0 ? `+${forecastData.length} Dekad` : 'Belum dijalankan', icon: <Wind size={18} />, bg: 'bg-neutral-100', text: 'text-neutral-600' },
        ].map(({ label, value, icon, bg, text }, idx) => (
          <div key={idx} className={`bento-card p-3 flex items-center gap-3 ${bg}`}>
            <div className={`w-10 h-10 rounded-xl bg-white border-2 border-neutral-900 shadow-hard-sm flex items-center justify-center shrink-0 ${text}`}>
              {icon}
            </div>
            <div>
              <div className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider">{label}</div>
              <div className={`font-mono text-lg font-black ${text} leading-none mt-0.5`}>{value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── ROW 3: CHARTS & TABLE (Fills remaining height) ── */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
        
        {/* Left Col: Charts Stack (col-span-2) */}
        <div className="lg:col-span-2 flex flex-col gap-4 min-h-0">
          
          {/* Chart 1 */}
          <div className="bento-card flex-1 p-4 flex flex-col min-h-0">
            <div className="flex items-center gap-2 mb-3 shrink-0">
              <CloudRain size={16} className="text-blue-600" />
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-700">Curah Hujan & Suhu</span>
              {loadingTrends && <Loader2 size={14} className="animate-spin text-neutral-400 ml-auto" />}
            </div>
            
            {error && !loadingTrends && (
              <div className="text-red-600 text-xs bg-red-50 p-2 rounded flex items-center gap-2 font-medium mb-2 border border-red-200">
                <AlertOctagon size={14} /> {error}
              </div>
            )}

            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={combinedChartData.length > 0 ? combinedChartData : trendsData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gRain" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" vertical={false} />
                  <XAxis dataKey="date" stroke="#a3a3a3" fontSize={10} tickLine={false} axisLine={false} tickFormatter={t => { const d = new Date(t); return isNaN(d) ? t : d.toLocaleDateString('id-ID', { month: 'short', year: '2-digit' }) }} />
                  <YAxis yAxisId="left" stroke="#2563eb" fontSize={10} tickLine={false} axisLine={false} width={40} />
                  <YAxis yAxisId="right" orientation="right" stroke="#ca8a04" fontSize={10} tickLine={false} axisLine={false} domain={['auto', 'auto']} width={35} />
                  <Tooltip content={<NbTooltip />} />
                  <Legend verticalAlign="top" height={24} iconSize={8} wrapperStyle={{ fontSize: '10px', fontWeight: '600' }} />
                  
                  <Area yAxisId="left" type="monotone" dataKey="rainfall" name="Curah Hujan" stroke="#2563eb" strokeWidth={2} fill="url(#gRain)" dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="temperature" name="Suhu" stroke="#eab308" strokeWidth={2} dot={false} />
                  
                  {combinedChartData.length > 0 && (
                    <Line yAxisId="left" type="monotone" dataKey="rainfall" name="Ramalan" stroke="#dc2626" strokeWidth={2} strokeDasharray="4 4" dot={{ r: 3, fill: '#dc2626', strokeWidth: 0 }} data={combinedChartData.filter(d => d.isForecast)} />
                  )}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2 */}
          <div className="bento-card flex-1 p-4 flex flex-col min-h-0">
            <div className="flex items-center gap-2 mb-3 shrink-0">
              <Droplets size={16} className="text-sage-600" />
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-700">Vegetasi & Air Tanah (FPAR · Soil Moisture)</span>
            </div>
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendsData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" vertical={false} />
                  <XAxis dataKey="date" stroke="#a3a3a3" fontSize={10} tickLine={false} axisLine={false} tickFormatter={t => { const d = new Date(t); return isNaN(d) ? t : d.toLocaleDateString('id-ID', { month: 'short', year: '2-digit' }) }} />
                  <YAxis yAxisId="left" stroke="#16a34a" fontSize={10} tickLine={false} axisLine={false} width={40} />
                  <YAxis yAxisId="right" orientation="right" stroke="#0ea5e9" fontSize={10} tickLine={false} axisLine={false} domain={[0, 1]} width={35} />
                  <Tooltip content={<NbTooltip />} />
                  <Legend verticalAlign="top" height={24} iconSize={8} wrapperStyle={{ fontSize: '10px', fontWeight: '600' }} />
                  
                  <Line yAxisId="left" type="monotone" dataKey="fpar" name="FPAR" stroke="#16a34a" strokeWidth={2} dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="soil_moisture" name="Kelembaban Tanah" stroke="#0ea5e9" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

        {/* Right Col: Forecast Table */}
        <div className="bento-card flex flex-col min-h-0 bg-white">
          <div className="p-4 border-b-2 border-neutral-100 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <TrendingUp size={16} className="text-red-600" />
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-900">Proyeksi AI</span>
            </div>
            {forecastData.length > 0 && (
              <span className="text-[10px] font-bold bg-red-100 text-red-700 px-2 py-0.5 rounded-full border border-red-200">
                +{forecastData.length} Dekad
              </span>
            )}
          </div>

          <div className="flex-1 overflow-auto p-0">
            {forecastData.length > 0 ? (
              <table className="w-full text-left border-collapse">
                <thead className="bg-neutral-50 sticky top-0 z-10 border-b-2 border-neutral-200 shadow-sm">
                  <tr>
                    <th className="py-2 px-3 text-[10px] font-bold uppercase tracking-wider text-neutral-500">Step</th>
                    <th className="py-2 px-3 text-[10px] font-bold uppercase tracking-wider text-neutral-500">Tanggal</th>
                    <th className="py-2 px-3 text-[10px] font-bold uppercase tracking-wider text-neutral-500">Hujan (mm)</th>
                    <th className="py-2 px-3 text-[10px] font-bold uppercase tracking-wider text-neutral-500">SPI-3</th>
                    <th className="py-2 px-3 text-[10px] font-bold uppercase tracking-wider text-neutral-500">Tanah</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100 text-xs font-mono">
                  {forecastData.map((f) => (
                    <tr key={f.step} className="hover:bg-neutral-50 transition-colors">
                      <td className="py-2.5 px-3 font-bold text-red-600">+{f.step}</td>
                      <td className="py-2.5 px-3 font-medium text-neutral-700">{new Date(f.date).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: '2-digit' })}</td>
                      <td className="py-2.5 px-3">{parseFloat(f.rainfall).toFixed(1)}</td>
                      <td className={`py-2.5 px-3 font-bold ${parseFloat(f.spi_3m) < -1.0 ? 'text-red-600' : 'text-green-600'}`}>
                        {parseFloat(f.spi_3m).toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-blue-600">{parseFloat(f.soil_moisture).toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-neutral-400">
                <Wind size={32} className="mb-2 opacity-50" />
                <p className="text-xs font-medium max-w-[200px]">Jalankan ramalan untuk melihat proyeksi tabel di sini.</p>
              </div>
            )}
          </div>
          
          <div className="p-3 bg-neutral-50 border-t-2 border-neutral-100 shrink-0">
            <p className="text-[10px] text-neutral-500 font-medium">
              * SPI &lt; -1.0 menandakan potensi kekeringan. Data dihasilkan menggunakan model regresi XGBoost Multi-Output.
            </p>
          </div>
        </div>

      </div>
    </div>
  )
}

export default Statistics
