import React from 'react';

interface HeaderProps {
  currentRoute: string;
  onNavigate: (route: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ currentRoute, onNavigate }) => {
  const isHome = currentRoute === 'home';

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
