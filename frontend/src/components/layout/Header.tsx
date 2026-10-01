import React from 'react';
import { useDataset } from '../../context/DatasetContext';

interface HeaderProps {
  currentRoute: string;
  onNavigate: (route: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ currentRoute, onNavigate }) => {
  const isHome = currentRoute === 'home';
  const { activeDataset, label, switchDataset, availableDatasets, isSwitching } = useDataset();

  return (
    /* Top header with full-width yellow bottom border */
    <header className="h-24 bg-[#151515] px-6 flex items-center justify-between select-none relative z-30">
      {/* Left Logo Section: Logo enlarged */}
      <div 
        className="flex items-center gap-3 cursor-pointer"
        onClick={() => onNavigate('dashboard')}
        title="TRACE Dashboard"
      >
        <img 
          src="/assets/Logo_BG_enlarged.svg" 
          alt="TRACE Logo" 
          className="h-32 md:h-36 max-h-[80px] md:max-h-[88px] w-auto object-contain" 
        />
      </div>

      {/* Right Header Section */}
      <div className="flex items-center gap-4">
        {/* Active Dataset Selector Dropdown */}
        <div 
          className="flex items-center gap-2 px-3 py-1.5 rounded-[3px] bg-[#1E1E1E] border border-[#F2D04E]/40 text-xs font-semibold tracking-wider font-body"
          title={`Active Perception Dataset: ${label}`}
        >
          <span className="w-2 h-2 rounded-full bg-[#1B7A43] animate-pulse" />
          <span className="text-[#AEA793] uppercase text-[10px] tracking-widest hidden sm:inline">DATASET:</span>
          <select
            value={activeDataset}
            onChange={(e) => switchDataset(e.target.value)}
            disabled={isSwitching}
            className="bg-transparent text-[#F2D04E] uppercase font-bold text-[11px] focus:outline-none cursor-pointer border-none pr-1"
            title="Switch Active Perception Dataset"
          >
            {availableDatasets.map((ds) => (
              <option key={ds.id} value={ds.id} className="bg-[#151515] text-[#F2D04E] py-1">
                {ds.label || ds.id}
              </option>
            ))}
          </select>
          {isSwitching && (
            <span className="text-[10px] text-[#AEA793] animate-pulse">Switching...</span>
          )}
        </div>

        {/* Home Page Icon Button */}
        <button
          onClick={() => onNavigate('home')}
          className={`p-2.5 rounded-[3px] flex items-center justify-center transition-all ${
            isHome
              ? 'bg-[#F2D04E] text-black'
              : 'bg-transparent text-white'
          }`}
          title="Home Page"
          aria-label="Home"
        >
          <img 
            src="/assets/home.svg" 
            alt="Home Icon" 
            className={`w-5 h-5 transition-transform ${
              isHome ? 'brightness-0' : ''
            }`} 
          />
        </button>
      </div>
    </header>
  );
};
