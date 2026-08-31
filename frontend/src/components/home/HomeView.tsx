import React, { useState } from 'react';

interface HomeViewProps {
  onNavigate: (route: string) => void;
  initialPageStep?: 1 | 2;
}

export const HomeView: React.FC<HomeViewProps> = ({ onNavigate, initialPageStep = 1 }) => {
  // Step 1: Logo & Down Arrow. Step 2: 3-Card Feature Briefing Page
  const [pageStep, setPageStep] = useState<1 | 2>(initialPageStep);

  return (
    <div className="w-full min-h-screen bg-[#151515] text-white flex flex-col justify-between font-body select-none">
      {pageStep === 1 ? (
        /* ================= PAGE 1 OF HOME SCREEN ================= */
        /* Logo fixed centered, down arrow pulled up very high right under logo text */
        <section className="h-screen max-h-screen w-full flex flex-col items-center justify-center px-4 select-none bg-[#151515] overflow-hidden">
          {/* Main Logo with Slogan (Fixed Centered) */}
          <div className="max-w-3xl w-full flex justify-center px-4">
            <img 
              src="/assets/Logo_Slogan_BG.svg" 
              alt="TRACE - Tracking Recognition Analysis City Wide Traffic Enforcement" 
              className="w-full max-w-2xl h-auto object-contain drop-shadow-2xl"
            />
          </div>

          {/* Down Arrow Button -> Pulled up very high directly under slogan text line */}
          <div className="-mt-24 md:-mt-36 z-10">
            <button
              onClick={() => setPageStep(2)}
              className="cursor-pointer focus:outline-none transition-transform hover:scale-110 active:scale-95 duration-200"
              title="Next Page"
              aria-label="Next Page"
            >
              <img 
                src="/assets/down_start.svg" 
                alt="Next Page" 
                className="w-12 h-12 md:w-14 md:h-14 drop-shadow-xl"
              />
            </button>
          </div>
        </section>
      ) : (
        /* ================= PAGE 2 OF HOME SCREEN ================= */
        <div className="min-h-screen flex flex-col justify-between bg-[#151515]">
          {/* Page 2 Top Header */}
          <header className="h-24 bg-[#151515] border-b border-[#F2D04E] px-6 md:px-12 flex items-center justify-between z-20">
            {/* Left Logo -> Enlarged size */}
            <div 
              onClick={() => setPageStep(1)}
              className="cursor-pointer flex items-center"
              title="Back to Home Page 1"
            >
              <img 
                src="/assets/Logo_BG_enlarged.svg" 
                alt="TRACE Logo" 
                className="h-20 md:h-24 w-auto object-contain transition-transform hover:scale-105"
              />
            </div>

            {/* Right Action: start_button.svg -> Decreased size */}
            <button
              onClick={() => onNavigate('dashboard')}
              className="cursor-pointer focus:outline-none transition-transform hover:scale-105 active:scale-95 duration-200"
              title="Start Dashboard"
            >
              <img 
                src="/assets/start_button.svg" 
                alt="Start Dashboard" 
                className="h-7 md:h-8 w-auto object-contain drop-shadow-md"
              />
            </button>
          </header>

          {/* Main Content Area */}
          <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-4 flex flex-col justify-center space-y-6">
            {/* Introductory Statement */}
            <div className="max-w-4xl space-y-2 font-body text-base md:text-lg text-white/90 leading-relaxed">
              <p className="font-semibold text-white">
                TRACE is a city-wide AI platform that connects multi-camera ANPR data to recognize, track, and understand vehicle movement.
              </p>
              <p className="text-[#A0A0A0]">
                It delivers real-time vehicle trajectories, traffic analytics, and intelligent anomaly detection through one unified platform.
              </p>
            </div>

            {/* 3 Feature Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {/* Card 1: High - Precision OCR */}
              <div className="bg-[#1E1E1E] rounded-xl p-6 flex flex-col min-h-[350px] shadow-2xl">
                <h3 className="text-xl font-bold font-heading text-[#F2D04E] mb-4">
                  High - Precision OCR
                </h3>
                <div className="mb-4">
                  <img src="/assets/Scan.svg" alt="OCR Scan Icon" className="w-9 h-9" />
                </div>
                <p className="text-xs md:text-sm text-[#A0A0A0] leading-relaxed mb-4">
                  Advanced neural networks deliver &gt;90% accuracy in challenging lighting and weather conditions.
                </p>

                {/* Bottom OCR Tag SVG: Moved somewhat down using mt-8 */}
                <div className="w-full flex justify-center items-center mt-8">
                  <img 
                    src="/assets/ocr.svg" 
                    alt="OCR Plate Graphic" 
                    className="h-10 md:h-11 w-auto object-contain"
                  />
                </div>
              </div>

              {/* Card 2: Vehicle Tracking */}
              <div className="bg-[#1E1E1E] rounded-xl p-6 flex flex-col justify-between min-h-[350px] shadow-2xl">
                <div>
                  <h3 className="text-xl font-bold font-heading text-[#F2D04E] mb-4">
                    Vehicle Tracking
                  </h3>
                  <div className="mb-4">
                    <img src="/assets/route.svg" alt="Vehicle Tracking Icon" className="w-8 h-8 text-[#F2D04E]" />
                  </div>
                  <p className="text-xs md:text-sm text-[#A0A0A0] leading-relaxed">
                    GIS-mapped historical paths interpolate missing data points to track anomalous vehicle behavior across zones.
                  </p>
                </div>

                {/* Bottom Vehicle Tracking Graphic */}
                <div className="w-full flex justify-center items-center pt-4">
                  <div className="w-full h-24 bg-[#151515] rounded-lg overflow-hidden relative border border-white/5">
                    <img 
                      src="/assets/trajectory_map.svg" 
                      alt="Vehicle Tracking Graphic" 
                      className="w-full h-full object-cover opacity-80"
                    />
                    <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 200 60">
                      <path d="M 20 40 Q 80 10, 140 45 T 180 20" stroke="#F2D04E" strokeWidth="3" fill="none" />
                      <circle cx="20" cy="40" r="4" fill="#AC251D" />
                      <circle cx="180" cy="20" r="4" fill="#1B7A43" />
                    </svg>
                  </div>
                </div>
              </div>

              {/* Card 3: Traffic Analytics */}
              <div className="bg-[#1E1E1E] rounded-xl p-6 flex flex-col justify-between min-h-[350px] shadow-2xl">
                <div>
                  <h3 className="text-xl font-bold font-heading text-[#F2D04E] mb-4">
                    Traffic Analytics
                  </h3>
                  <div className="mb-4">
                    <img src="/assets/traffic.svg" alt="Traffic Analytics Icon" className="w-9 h-9" />
                  </div>
                  <p className="text-xs md:text-sm text-[#A0A0A0] leading-relaxed">
                    Generate heatmaps and Origin-Destination (OD) patterns to optimize city flow and identify congestion bottlenecks.
                  </p>
                </div>

                {/* Bottom Traffic Analytics Graphic */}
                <div className="w-full flex justify-center items-center pt-4">
                  <img 
                    src="/assets/traffic_analystics.svg" 
                    alt="Traffic Analytics Graphic" 
                    className="h-16 md:h-20 w-auto object-contain" 
                  />
                </div>
              </div>
            </div>
          </main>

          {/* Page 2 Footer */}
          <footer className="py-4 text-center text-[11px] text-[#666666] font-heading border-t border-white/5">
            © 2026 TRACE — Tracking, Recognition, Analytics & City-wide Traffic Enforcement. All Rights Reserved.
          </footer>
        </div>
      )}
    </div>
  );
};
