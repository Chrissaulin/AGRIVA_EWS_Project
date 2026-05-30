import React, { useEffect, useState, useCallback } from 'react';
import {
  Activity, ShieldAlert, Compass, Layers, Sliders, TrendingDown, BarChart3
} from 'lucide-react';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, RadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, Radar, ReferenceLine, BarChart, Bar
} from 'recharts';

/* ── Custom Dark Tooltip ── */
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{
      background: '#111', border: '2px solid #333', padding: '0.65rem 0.85rem',
      boxShadow: '4px 4px 0 #0a0a0a', fontFamily: 'monospace', fontSize: '0.78rem'
    }}>
      <p style={{ fontWeight: 800, color: '#fff', borderBottom: '1px solid #333', paddingBottom: '0.2rem', marginBottom: '0.3rem' }}>{label}</p>
      {payload.map((item, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', color: item.color }}>
          <span>{item.name}:</span>
          <strong style={{ color: '#fff' }}>{typeof item.value === 'number' ? item.value.toFixed(2) : item.value}</strong>
        </div>
      ))}
    </div>
  );
};

export default function AdvancedAnalytics() {
  const [regions, setRegions] = useState([]);
  const [selectedRegion, setSelectedRegion] = useState('Jawa Timur');
  const [loading, setLoading] = useState(true);
  const [selectedDriver, setSelectedDriver] = useState('soil_moisture');

  // Fetch Provinces
  useEffect(() => {
    fetch('http://localhost:8000/api/regions')
      .then(res => res.ok ? res.json() : [])
      .then(data => {
        setRegions(data);
        if (data.length > 0) {
          const defaultProv = data.find(d => d.region_name === 'Jawa Timur') || data[0];
          setSelectedRegion(defaultProv.region_name);
        }
        setLoading(false);
      })
      .catch(err => console.error(err));
  }, []);

  // 1. GENERATE STATIC MOCK TLCC DATA (BASED ON PEAK BIOLOGICAL CROP RESPONSE LAGS)
  const getTlccData = useCallback(() => {
    const selectedCluster = regions.find(r => r.region_name === selectedRegion)?.cluster_wilayah ?? 0;
    const peakLag = selectedCluster === 0 ? -3 : selectedCluster === 1 ? -2 : -4;
    
    const lags = [-6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6];
    return lags.map(lag => {
      const distance = Math.abs(lag - peakLag);
      const correlation = 0.68 * Math.exp(-Math.pow(distance, 2) / 6.0) - (lag > 0 ? 0.2 : 0);
      return {
        lag: `${lag} Dekad`,
        korelasi: correlation,
        korelasiHujan: correlation * 0.85
      };
    });
  }, [selectedRegion, regions]);

  // 2. RADAR CHART DATA: CLUSTER METEOROLOGICAL SIGNATURES
  const radarData = [
    { indicator: 'Curah Hujan (Rainfall)', 'Cluster 0 (Wet/Mod)': 85, 'Cluster 1 (Dry)': 42, 'Cluster 2 (Equat)': 95 },
    { indicator: 'Suhu Udara (Temp)', 'Cluster 0 (Wet/Mod)': 65, 'Cluster 1 (Dry)': 92, 'Cluster 2 (Equat)': 55 },
    { indicator: 'Soil Moisture', 'Cluster 0 (Wet/Mod)': 80, 'Cluster 1 (Dry)': 35, 'Cluster 2 (Equat)': 88 },
    { indicator: 'WSI Index', 'Cluster 0 (Wet/Mod)': 88, 'Cluster 1 (Dry)': 48, 'Cluster 2 (Equat)': 92 },
    { indicator: 'FPAR Greenness', 'Cluster 0 (Wet/Mod)': 78, 'Cluster 1 (Dry)': 58, 'Cluster 2 (Equat)': 82 }
  ];

  // 3. BAR CHART DATA: ALERT FREQUENCY STACKED BY SEVERITY
  const barData = [
    { region: 'Jawa Timur', 'Aman (L0)': 120, 'Exceptional (L1)': 35, 'Siaga (L2)': 20, 'Awas (L3/4)': 10 },
    { region: 'Jawa Tengah', 'Aman (L0)': 140, 'Exceptional (L1)': 25, 'Siaga (L2)': 15, 'Awas (L3/4)': 5 },
    { region: 'Jawa Barat', 'Aman (L0)': 130, 'Exceptional (L1)': 30, 'Siaga (L2)': 12, 'Awas (L3/4)': 8 },
    { region: 'Nusatenggara T_', 'Aman (L0)': 50, 'Exceptional (L1)': 35, 'Siaga (L2)': 40, 'Awas (L3/4)': 35 },
    { region: 'Bali', 'Aman (L0)': 110, 'Exceptional (L1)': 35, 'Siaga (L2)': 20, 'Awas (L3/4)': 8 },
  ];

  const tlccDataset = getTlccData();
  const currentCluster = regions.find(r => r.region_name === selectedRegion)?.cluster_wilayah ?? 0;

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'var(--nb-yellow)' }}>
        Memuat data analisis korelasi...
      </div>
    );
  }

  return (
    <div className="animate-fade-in" style={{
      height: 'calc(100vh - 4rem)',
      display: 'grid',
      gridTemplateRows: 'auto auto 1fr',
      gap: '0.75rem',
      overflow: 'hidden',
      paddingBottom: '0.5rem'
    }}>
      
      {/* ══ ROW 1: HEADER & SELECTOR ══ */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.85rem', alignItems: 'center' }}>
        <div>
          <div className="section-heading">Advanced Insights Dashboard</div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--nb-white)', lineHeight: 1.1 }}>
            Wawasan Analitik <span style={{ color: 'var(--nb-yellow)' }}>Kerentanan &amp; Korelasi Stress</span>
          </h1>
        </div>
        <div>
          <select
            className="select-input"
            value={selectedRegion}
            onChange={(e) => setSelectedRegion(e.target.value)}
            style={{ minWidth: '220px', fontSize: '0.85rem', padding: '0.45rem 0.75rem' }}
          >
            {regions.map(r => (
              <option key={r.region_name} value={r.region_name}>
                {r.region_name} · Cluster {r.cluster_wilayah}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ══ ROW 2: ADVANCED KNOWLEDGE CARDS ══ */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr 1fr', gap: '0.75rem' }}>
        
        {/* Card 1: Biological Stress Lag */}
        <div className="nb-card" style={{ borderLeft: '4px solid var(--nb-cyan)', padding: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--nb-cyan)', marginBottom: '0.2rem' }}>
            <Activity size={15} />
            <span style={{ fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Jeda Respon Vegetasi (TLCC)</span>
          </div>
          <p style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--nb-white)', fontFamily: 'monospace' }}>
            -{currentCluster === 0 ? '30' : currentCluster === 1 ? '20' : '40'} Hari (Peak Lag)
          </p>
          <p style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '0.1rem' }}>
            Waktu jeda optimal dari stress air tanah hingga daun browning terdeteksi satelit.
          </p>
        </div>

        {/* Card 2: Risk state probabilities */}
        <div className="nb-card" style={{ borderLeft: '4px solid var(--nb-pink)', padding: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--nb-pink)', marginBottom: '0.2rem' }}>
            <ShieldAlert size={15} />
            <span style={{ fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Estimasi Markov Risiko Dekad +1</span>
          </div>
          <p style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--nb-white)', fontFamily: 'monospace' }}>
            {currentCluster === 1 ? '72%' : currentCluster === 0 ? '43%' : '21%'} Probabilitas Kerusakan
          </p>
          <p style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '0.1rem' }}>
            Peluang naiknya Alert EWS ke tingkat waspada/bahaya jika moisture di bawah batas kritis.
          </p>
        </div>

        {/* Card 3: Typology Profile */}
        <div className="nb-card" style={{ borderLeft: '4px solid var(--nb-green)', padding: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--nb-green)', marginBottom: '0.2rem' }}>
            <Compass size={15} />
            <span style={{ fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Tipologi Pertanian Wilayah</span>
          </div>
          <p style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--nb-white)' }}>
            Cluster {currentCluster}: {currentCluster === 0 ? 'Wet/Moderate Base' : currentCluster === 1 ? 'Vulnerable Dry Monsoon' : 'Equatorial High-Rainfall'}
          </p>
          <p style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '0.1rem' }}>
            Kategori kerentanan berdasarkan iklim makro dan pola tanam regional.
          </p>
        </div>

      </div>

      {/* ══ ROW 3: INTERACTIVE CHARTS GRID ══ */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '0.75rem', minHeight: 0 }}>
        
        {/* LEFT PANEL: TLCC Line Chart */}
        <div className="nb-card" style={{ padding: '0.75rem', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <TrendingDown size={14} color="var(--nb-cyan)" />
              <span style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--nb-cyan)' }}>
                Cross-Correlation (TLCC): Climate Driver vs Crop Health
              </span>
            </div>
            
            <div style={{ display: 'flex', gap: '0.3rem' }}>
              {['soil_moisture', 'rainfall'].map(driver => (
                <button
                  key={driver}
                  onClick={() => setSelectedDriver(driver)}
                  style={{
                    fontSize: '0.65rem',
                    padding: '0.2rem 0.5rem',
                    background: selectedDriver === driver ? 'var(--nb-cyan)' : '#222',
                    color: selectedDriver === driver ? '#000' : '#888',
                    border: '1px solid #333',
                    cursor: 'pointer',
                    fontWeight: 700
                  }}
                >
                  {driver === 'soil_moisture' ? 'Air Tanah' : 'Curah Hujan'}
                </button>
              ))}
            </div>
          </div>
          
          <div style={{ flexGrow: 1, minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={tlccDataset} margin={{ top: 10, right: 10, left: -22, bottom: 0 }}>
                <CartesianGrid stroke="#1e1e1e" />
                <XAxis dataKey="lag" stroke="#444" fontSize={9} />
                <YAxis stroke="#00F5FF" fontSize={9} domain={[-0.2, 0.8]} />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine x={`-${currentCluster === 0 ? 3 : currentCluster === 1 ? 2 : 4} Dekad`} stroke="var(--nb-pink)" strokeDasharray="3 3" label={{ value: 'Peak Response', fill: 'var(--nb-pink)', fontSize: 7, position: 'top' }} />
                <ReferenceLine y={0} stroke="#444" />
                <Line
                  type="monotone"
                  dataKey={selectedDriver === 'soil_moisture' ? 'korelasi' : 'korelasiHujan'}
                  name="Koefisien Korelasi (r)"
                  stroke="var(--nb-cyan)"
                  strokeWidth={2.5}
                  dot={{ r: 4, stroke: '#111', strokeWidth: 1.5, fill: 'var(--nb-cyan)' }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* RIGHT PANEL: Stacked Bar Chart & Typology Radar */}
        <div style={{ display: 'grid', gridTemplateRows: '1.1fr 1.1fr', gap: '0.75rem', minHeight: 0 }}>
          
          {/* Stacked Bar Chart (Geographic Alert Severity) */}
          <div className="nb-card" style={{ padding: '0.6rem', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
              <BarChart3 size={14} color="var(--nb-yellow)" />
              <span style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--nb-yellow)' }}>
                Distribusi Tingkat Bahaya EWS Historis (Stacked Bar)
              </span>
            </div>

            <div style={{ flexGrow: 1, minHeight: 0 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} layout="vertical" margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid stroke="#1e1e1e" />
                  <XAxis type="number" stroke="#444" fontSize={8} />
                  <YAxis type="category" dataKey="region" stroke="#888" fontSize={8} width={75} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend iconSize={6} wrapperStyle={{ fontSize: '0.6rem', bottom: -5 }} />
                  <Bar dataKey="Aman (L0)" stackId="ews" fill="#3c3f4a" />
                  <Bar dataKey="Exceptional (L1)" stackId="ews" fill="#00E676" />
                  <Bar dataKey="Siaga (L2)" stackId="ews" fill="#FFE500" />
                  <Bar dataKey="Awas (L3/4)" stackId="ews" fill="#FF2D78" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Radar Chart (Cluster Typologies) */}
          <div className="nb-card" style={{ padding: '0.6rem', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.2rem' }}>
              <Layers size={14} color="var(--nb-green)" />
              <span style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--nb-green)' }}>
                Profil Tipologi Lingkungan Cluster Wilayah
              </span>
            </div>

            <div style={{ flexGrow: 1, minHeight: 0 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" radius="70%" data={radarData}>
                  <PolarGrid stroke="#222" />
                  <PolarAngleAxis dataKey="indicator" stroke="#777" fontSize={8} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#333" fontSize={7} />
                  <Radar name="Cluster 0 (Wet/Mod)" dataKey="Cluster 0 (Wet/Mod)" stroke="#00F5FF" fill="#00F5FF" fillOpacity={0.12} />
                  <Radar name="Cluster 1 (Dry Monsoon)" dataKey="Cluster 1 (Dry)" stroke="#FFE500" fill="#FFE500" fillOpacity={0.12} />
                  <Radar name="Cluster 2 (Equatorial Wet)" dataKey="Cluster 2 (Equat)" stroke="#00E676" fill="#00E676" fillOpacity={0.12} />
                  <Legend iconSize={6} wrapperStyle={{ fontSize: '0.6rem', bottom: -5 }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
