import React from 'react'
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend 
} from 'recharts'

// Custom Glassmorphic Tooltip
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    // Format tanggal
    const formattedDate = new Date(label).toLocaleDateString('id-ID', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
    
    return (
      <div style={{
        background: 'rgba(8, 12, 24, 0.9)',
        backdropFilter: 'blur(10px)',
        border: '1px solid var(--border-glass-active)',
        padding: '0.85rem 1rem',
        borderRadius: 'var(--radius-md)',
        fontSize: '0.85rem',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.4rem'
      }}>
        <p style={{ fontWeight: 700, color: '#fff', marginBottom: '0.2rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.2rem' }}>
          {formattedDate}
        </p>
        {payload.map((item, idx) => (
          <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', gap: '1.5rem', color: item.color }}>
            <span style={{ fontWeight: 500 }}>{item.name}:</span>
            <strong style={{ color: '#fff' }}>{item.value} {item.unit || ''}</strong>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export function TrendChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-dim)' }}>
        Tidak ada data grafik untuk ditampilkan.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
      
      {/* 1. CHART IKLIM: Curah Hujan & Suhu (Dual Y-Axis) */}
      <div className="glass-card" style={{ padding: '1.75rem' }}>
        <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>🌦️ Tren Parameter Iklim (Curah Hujan vs Suhu)</span>
        </h4>
        <div style={{ width: '100%', height: 350 }}>
          <ResponsiveContainer>
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="colorRainfall" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(217, 91%, 60%)" stopOpacity={0.25}/>
                  <stop offset="95%" stopColor="hsl(217, 91%, 60%)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis 
                dataKey="date" 
                stroke="var(--text-dim)" 
                fontSize={10}
                tickFormatter={(tick) => {
                  const d = new Date(tick);
                  return d.toLocaleDateString('id-ID', { month: 'short', year: '2-digit' });
                }}
              />
              <YAxis 
                yAxisId="left" 
                stroke="hsl(217, 91%, 60%)" 
                fontSize={10} 
                unit=" mm"
                label={{ value: 'Curah Hujan (mm)', angle: -90, position: 'insideLeft', style: { fill: 'hsl(217, 91%, 60%)', fontSize: 10, fontWeight: 600 } }}
              />
              <YAxis 
                yAxisId="right" 
                orientation="right" 
                stroke="var(--warning)" 
                fontSize={10} 
                domain={[20, 35]} 
                unit="°C"
                label={{ value: 'Suhu (°C)', angle: 90, position: 'insideRight', style: { fill: 'var(--warning)', fontSize: 10, fontWeight: 600 } }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: '0.85rem' }} />
              <Area 
                yAxisId="left"
                type="monotone" 
                dataKey="rainfall" 
                name="Curah Hujan" 
                unit="mm"
                stroke="hsl(217, 91%, 60%)" 
                fillOpacity={1} 
                fill="url(#colorRainfall)" 
              />
              <Line 
                yAxisId="right"
                type="monotone" 
                dataKey="temperature" 
                name="Suhu Udara" 
                unit="°C"
                stroke="var(--warning)" 
                strokeWidth={2}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. CHART VEGETASI: FPAR & Kelembaban Tanah */}
      <div className="glass-card" style={{ padding: '1.75rem' }}>
        <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>🌿 Kesehatan Vegetasi &amp; Air Tanah (FPAR vs Soil Moisture)</span>
        </h4>
        <div style={{ width: '100%', height: 350 }}>
          <ResponsiveContainer>
            <LineChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis 
                dataKey="date" 
                stroke="var(--text-dim)" 
                fontSize={10}
                tickFormatter={(tick) => {
                  const d = new Date(tick);
                  return d.toLocaleDateString('id-ID', { month: 'short', year: '2-digit' });
                }}
              />
              <YAxis 
                yAxisId="left" 
                stroke="var(--safe)" 
                fontSize={10}
                label={{ value: 'Indeks FPAR', angle: -90, position: 'insideLeft', style: { fill: 'var(--safe)', fontSize: 10, fontWeight: 600 } }}
              />
              <YAxis 
                yAxisId="right" 
                orientation="right" 
                stroke="var(--info)" 
                fontSize={10} 
                domain={[0, 1]}
                label={{ value: 'Kadar Air Tanah', angle: 90, position: 'insideRight', style: { fill: 'var(--info)', fontSize: 10, fontWeight: 600 } }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: '0.85rem' }} />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="fpar" 
                name="FPAR (Kehijauan)" 
                stroke="var(--safe)" 
                strokeWidth={2}
                dot={false}
              />
              <Line 
                yAxisId="right"
                type="monotone" 
                dataKey="soil_moisture" 
                name="Kelembaban Tanah" 
                stroke="var(--info)" 
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  )
}
export default TrendChart
