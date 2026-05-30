import React, { useState } from 'react'
import { Home as HomeIcon, Map, BarChart3, Sliders, Leaf } from 'lucide-react'
import './styles/index.css'

// Import Pages
import Home from './pages/Home.jsx'
import MapDashboard from './pages/MapDashboard.jsx'
import Statistics from './pages/Statistics.jsx'
import Simulation from './pages/Simulation.jsx'

const NAV_ITEMS = [
  { id: 'home',       label: 'Beranda',      Icon: HomeIcon },
  { id: 'map',        label: 'Peta Risiko',  Icon: Map      },
  { id: 'stats',      label: 'Tren & Ramalan', Icon: BarChart3 },
  { id: 'simulation', label: 'Simulasi EWS', Icon: Sliders  },
]

function App() {
  const [activeTab, setActiveTab] = useState('home')

  const renderActivePage = () => {
    switch (activeTab) {
      case 'home':       return <Home onNavigate={(tab) => setActiveTab(tab)} />
      case 'map':        return <MapDashboard />
      case 'stats':      return <Statistics />
      case 'simulation': return <Simulation />
      default:           return <Home onNavigate={(tab) => setActiveTab(tab)} />
    }
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-neutral-50 text-neutral-900">
      {/* ── Top Navigation Bar (Soft Brutalism) ── */}
      <header className="h-16 shrink-0 bg-white border-b-2 border-neutral-900 shadow-sm flex items-center justify-between px-6 z-50">
        
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="bg-sage-300 p-1.5 border-2 border-neutral-900 rounded-lg shadow-hard-sm">
            <Leaf size={20} className="text-neutral-900" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="font-sans font-black text-xl tracking-tight text-neutral-900">AGRIVA</span>
            <span className="font-mono font-bold text-xs bg-yellow-200 text-neutral-900 px-1.5 py-0.5 rounded border-2 border-neutral-900 shadow-[1px_1px_0px_0px_#171717]">
              EWS
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-2">
          {NAV_ITEMS.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl border-2 transition-all duration-150 font-semibold text-sm ${
                activeTab === id
                  ? 'bg-sage-300 border-neutral-900 shadow-hard-sm text-neutral-900 translate-x-[1px] translate-y-[1px]'
                  : 'bg-transparent border-transparent text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900'
              }`}
            >
              <Icon size={18} strokeWidth={activeTab === id ? 2.5 : 2} />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </nav>
      </header>

      {/* ── Main Content Area (Bento Grid Container) ── */}
      <main className="flex-1 overflow-hidden p-4 sm:p-6 bg-neutral-50">
        {renderActivePage()}
      </main>
    </div>
  )
}

export default App
