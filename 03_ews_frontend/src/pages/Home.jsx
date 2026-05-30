import React from 'react'
import { Map, Sliders, ChevronRight, ShieldAlert, Activity, Globe, ArrowUpRight } from 'lucide-react'

function Home({ onNavigate }) {
  return (
    <div className="h-full overflow-y-auto pr-2 animate-fade-in pb-8">
      {/* ── BENTO GRID LAYOUT ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-7xl mx-auto">
        
        {/* 1. HERO MISSION (col-span-2) */}
        <div className="lg:col-span-2 bento-card p-8 flex flex-col justify-between bg-white bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:16px_16px]">
          <div className="space-y-6">
            <div className="flex gap-3 items-center flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-100 text-red-700 border-2 border-neutral-900 rounded-lg font-bold text-xs uppercase tracking-wider shadow-hard-sm">
                <ShieldAlert size={14} /> Sistem Peringatan Dini
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-sage-200 text-neutral-900 border-2 border-neutral-900 rounded-lg font-bold text-xs uppercase tracking-wider shadow-hard-sm">
                Ketahanan Pangan
              </span>
            </div>

            <div className="space-y-4">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-neutral-900 leading-[1.1] tracking-tight">
                AGRIVA EWS <br/>
                <span className="text-sage-500">INDONESIA</span>
              </h1>
              <p className="text-neutral-600 text-lg max-w-xl leading-relaxed font-medium">
                Sistem Peringatan Dini untuk mendeteksi ancaman krisis iklim terhadap 
                ketahanan pangan 270+ juta jiwa. 
                <span className="text-neutral-900 font-bold bg-yellow-200 px-1 mx-1 rounded">Memantau sebelum krisis terjadi.</span>
              </p>
            </div>
          </div>

          <div className="mt-10 flex flex-wrap gap-4">
            <button onClick={() => onNavigate('map')} className="bento-button">
              <Map size={18} /> Buka Peta Risiko
            </button>
            <button onClick={() => onNavigate('simulation')} className="bento-button-secondary">
              <Sliders size={18} /> Coba Simulasi
            </button>
          </div>
        </div>

        {/* 2. KPI STACK */}
        <div className="flex flex-col gap-6">
          {[
            { num: '33', label: 'Provinsi Dipantau', color: 'bg-blue-100' },
            { num: '28K+', label: 'Data Historis', color: 'bg-yellow-100' },
            { num: '≥85%', label: 'Recall Model EWS', color: 'bg-sage-200' },
          ].map((kpi, idx) => (
            <div key={idx} className={`bento-card p-6 flex-1 flex flex-col justify-center ${kpi.color}`}>
              <div className="font-mono text-4xl font-black text-neutral-900">{kpi.num}</div>
              <div className="text-sm font-bold text-neutral-700 uppercase tracking-wide mt-1">{kpi.label}</div>
            </div>
          ))}
        </div>

        {/* 3. PILAR DETEKSI */}
        <div className="bento-card p-6 group bento-interactive" onClick={() => onNavigate('map')}>
          <div className="flex justify-between items-start mb-6">
            <div className="w-12 h-12 bg-blue-100 border-2 border-neutral-900 rounded-xl flex items-center justify-center shadow-hard-sm group-hover:scale-105 transition-transform">
              <Globe size={24} className="text-blue-600" />
            </div>
            <ArrowUpRight size={24} className="text-neutral-400 group-hover:text-neutral-900 transition-colors" />
          </div>
          <h3 className="text-xl font-black text-neutral-900 mb-3">Peta Risiko Geografis</h3>
          <p className="text-neutral-600 font-medium text-sm leading-relaxed mb-4">
            Pantau status <span className="text-green-600 font-bold">AMAN</span> dan <span className="text-red-600 font-bold">RISIKO</span> 
            di 33 provinsi secara interaktif real-time.
          </p>
        </div>

        {/* 4. PILAR ANALISIS */}
        <div className="bento-card p-6 group bento-interactive" onClick={() => onNavigate('stats')}>
          <div className="flex justify-between items-start mb-6">
            <div className="w-12 h-12 bg-yellow-100 border-2 border-neutral-900 rounded-xl flex items-center justify-center shadow-hard-sm group-hover:scale-105 transition-transform">
              <Activity size={24} className="text-yellow-600" />
            </div>
            <ArrowUpRight size={24} className="text-neutral-400 group-hover:text-neutral-900 transition-colors" />
          </div>
          <h3 className="text-xl font-black text-neutral-900 mb-3">Tren & Ramalan Iklim</h3>
          <p className="text-neutral-600 font-medium text-sm leading-relaxed mb-4">
            Visualisasi historis dan peramalan XGBoost Auto-Regressive untuk kondisi iklim dekad mendatang.
          </p>
        </div>

        {/* 5. PILAR SIMULASI */}
        <div className="bento-card p-6 group bento-interactive" onClick={() => onNavigate('simulation')}>
          <div className="flex justify-between items-start mb-6">
            <div className="w-12 h-12 bg-sage-200 border-2 border-neutral-900 rounded-xl flex items-center justify-center shadow-hard-sm group-hover:scale-105 transition-transform">
              <Sliders size={24} className="text-sage-700" />
            </div>
            <ArrowUpRight size={24} className="text-neutral-400 group-hover:text-neutral-900 transition-colors" />
          </div>
          <h3 className="text-xl font-black text-neutral-900 mb-3">Simulator Skenario</h3>
          <p className="text-neutral-600 font-medium text-sm leading-relaxed mb-4">
            Ubah parameter cuaca secara manual untuk melihat prediksi biner dampak pada ketahanan pangan.
          </p>
        </div>

        {/* 6. CTA BANNER (col-span-full) */}
        <div className="lg:col-span-3 bento-card p-6 sm:p-8 bg-neutral-900 text-white flex flex-col sm:flex-row items-center justify-between gap-6 border-neutral-900 shadow-hard">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-red-500 rounded-xl border-2 border-neutral-900 shadow-hard-sm flex items-center justify-center shrink-0">
              <ShieldAlert size={28} className="text-white" />
            </div>
            <div>
              <h2 className="text-xl sm:text-2xl font-black tracking-tight mb-1">Krisis Pangan Tidak Menunggu.</h2>
              <p className="text-neutral-400 font-medium text-sm">Pantau kondisi seluruh provinsi Indonesia sekarang.</p>
            </div>
          </div>
          <button onClick={() => onNavigate('map')} className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-sage-300 text-neutral-900 font-black border-2 border-neutral-900 rounded-xl shadow-hard hover:bg-sage-400 active:translate-x-[2px] active:translate-y-[2px] active:shadow-hard-sm transition-all whitespace-nowrap uppercase tracking-wider text-sm">
            <Map size={18} /> Monitor Sekarang
          </button>
        </div>

      </div>
    </div>
  )
}

export default Home
