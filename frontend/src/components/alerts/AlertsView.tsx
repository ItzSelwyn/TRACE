import React, { useState } from 'react';

export interface AlertItem {
  id: string;
  plateNumber: string;
  type: 'BLACKLIST' | 'ANOMALY';
  status: 'UNVERIFIED' | 'VERIFIED';
  confidence: number;
  vehicleType: string;
  vehicleColor: string;
  scannedTimestamp: string;
  cameraName: string;
  location: string;
  reason?: string;
}

export const AlertsView: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isFilterOpen, setIsFilterOpen] = useState<boolean>(false);
  const [verifyToast, setVerifyToast] = useState<string | null>(null);

  // Multi-Category Selected Filter States matching design defaults
  const [selectedVerifications, setSelectedVerifications] = useState<string[]>(['Verified', 'Unverified']);
  const [selectedLocations, setSelectedLocations] = useState<string[]>(['North Highway 1', 'North Highway 2', 'North Highway 3']);
  const [selectedCameras, setSelectedCameras] = useState<string[]>(['Camera 14', 'Camera 15', 'Camera 16']);
  const [selectedTypes, setSelectedTypes] = useState<string[]>(['SUV', 'TRUCK', 'SEDAN']);
  const [selectedColors, setSelectedColors] = useState<string[]>(['RED', 'ORANGE', 'BLUE']);
  const [selectedCategories, setSelectedCategories] = useState<string[]>(['BLACKLIST', 'ANOMALY']);

  // Mock Alerts
  const [alerts, setAlerts] = useState<AlertItem[]>([
    {
      id: 'alert-1',
      plateNumber: 'TN 37 CY 1234',
      type: 'BLACKLIST',
      status: 'UNVERIFIED',
      confidence: 92,
      vehicleType: 'SUV',
      vehicleColor: 'BLUE',
      scannedTimestamp: '10:20:38 pm (10 mins ago)',
      cameraName: 'Camera 16',
      location: 'North Highway 02',
    },
    {
      id: 'alert-2',
      plateNumber: 'TN 57 CY 1314',
      type: 'ANOMALY',
      status: 'UNVERIFIED',
      confidence: 84,
      vehicleType: 'SEDAN',
      vehicleColor: 'RED',
      scannedTimestamp: '12:12:12 am (1 hr ago)',
      cameraName: 'Camera 13',
      location: 'North Highway 12',
      reason: 'Impossible journey',
    },
    {
      id: 'alert-3',
      plateNumber: 'TN 57 CY 1314',
      type: 'ANOMALY',
      status: 'VERIFIED',
      confidence: 94,
      vehicleType: 'TRUCK',
      vehicleColor: 'ORANGE',
      scannedTimestamp: '01:06:08 am (1 hr ago)',
      cameraName: 'Camera 16',
      location: 'North Highway 06',
      reason: 'No number plate detected',
    },
    {
      id: 'alert-4',
      plateNumber: 'TN 57 CY 1314',
      type: 'BLACKLIST',
      status: 'VERIFIED',
      confidence: 94,
      vehicleType: 'TRUCK',
      vehicleColor: 'Orange',
      scannedTimestamp: '01:06:08 am (1 hr ago)',
      cameraName: 'Camera 14',
      location: 'North Highway 3',
    },
  ]);

  // Compute live Verified & Unverified counts
  const verifiedCount = alerts.filter((a) => a.status === 'VERIFIED').length;
  const unverifiedCount = alerts.filter((a) => a.status === 'UNVERIFIED').length;

  // Toggle selection in filter arrays
  const toggleFilter = (list: string[], setList: React.Dispatch<React.SetStateAction<string[]>>, item: string) => {
    if (list.includes(item)) {
      setList(list.filter((i) => i !== item));
    } else {
      setList([...list, item]);
    }
  };

  // Helper for confidence rate background color for unverified boxes
  const getConfidenceBg = (conf: number) => {
    if (conf >= 90) return 'bg-[#1B7A43]';
    if (conf >= 75) return 'bg-[#B8860B]';
    return 'bg-[#971D1B]';
  };

  // Handle Verify Action
  const handleVerifyAlert = (alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, status: 'VERIFIED' } : a))
    );
    setVerifyToast('Alert marked as VERIFIED successfully!');
    setTimeout(() => setVerifyToast(null), 3000);
  };

  // Multi-Category Real-time Filter Logic
  const filteredAlerts = alerts.filter((item) => {
    // 1. Search Query
    const matchesSearch =
      item.plateNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.cameraName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.location.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    // 2. Verification Filter
    if (selectedVerifications.length > 0) {
      const isVerifSelected = selectedVerifications.includes('Verified') && item.status === 'VERIFIED';
      const isUnverifSelected = selectedVerifications.includes('Unverified') && item.status === 'UNVERIFIED';
      if (!isVerifSelected && !isUnverifSelected) return false;
    }

    // 3. Category Filter
    if (selectedCategories.length > 0 && !selectedCategories.includes(item.type)) {
      return false;
    }

    return true;
  });

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-6 select-none relative">
      {/* Toast Notification */}
      {verifyToast && (
        <div className="fixed top-20 right-8 z-50 bg-[#F2D04E] text-black font-heading font-bold text-sm px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2">
          <span>✓</span>
          <span>{verifyToast}</span>
        </div>
      )}

      {/* ================= 1. TOP HEADER & SEARCH / FILTER BAR ================= */}
      <div className="bg-[#151515] rounded-[3px] p-4 md:px-6 flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-30">
        {/* Left Side: Search Bar */}
        <div className="relative flex-1 max-w-xl">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search Number Plate (e.g. TN 37 CY 1234)"
            className="w-full bg-[#000000] text-white placeholder-[#A0A0A0] text-sm font-body px-4 py-3 pr-10 rounded-[3px] focus:outline-none transition-all"
          />
          <img
            src="/assets/alert_search.svg"
            alt="Search Icon"
            className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 object-contain opacity-80"
          />
        </div>

        {/* Right Side: Stats & Filter Dropdown Toggle Button */}
        <div className="flex items-center gap-3 self-end md:self-auto relative">
          {/* Verified Count Pill */}
          <div className="bg-[#000000] px-5 py-2.5 rounded-[3px] text-[#A0A0A0] font-body font-bold text-base md:text-lg">
            {verifiedCount} Verified
          </div>

          {/* Unverified Count Pill */}
          <div className="bg-[#000000] px-5 py-2.5 rounded-[3px] text-[#A0A0A0] font-body font-bold text-base md:text-lg">
            {unverifiedCount} Unverified
          </div>

          {/* Filter Dropdown Button */}
          <div className="relative">
            <button
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className="outline-none focus:outline-none flex items-center justify-center cursor-pointer"
              title="Filter"
            >
              <img
                src={isFilterOpen ? "/assets/alert_filter_opened.svg" : "/assets/alert_filter.svg"}
                alt="Filter"
                className="h-10 w-auto object-contain"
              />
            </button>

            {/* ================= ENHANCED MULTI-CATEGORY FILTER PANEL ================= */}
            {isFilterOpen && (
              <div 
                className="absolute right-0 mt-3 w-64 md:w-72 bg-[#000000] rounded-[3px] z-50 p-4 space-y-4 text-xs font-body"
                style={{ boxShadow: '0px 14px 35px rgba(0, 0, 0, 0.3)' }}
              >
                {/* 1. Verification Category */}
                <div className="space-y-2">
                  <h4 className="text-white font-bold tracking-wider uppercase text-[11px] font-body block mb-1">
                    Verification
                  </h4>
                  {['Verified', 'Unverified'].map((item) => {
                    const isChecked = selectedVerifications.includes(item);
                    return (
                      <div
                        key={item}
                        onClick={() => toggleFilter(selectedVerifications, setSelectedVerifications, item)}
                        className="flex items-center justify-between text-[#AEA793] font-body cursor-pointer hover:text-white py-0.5"
                      >
                        <span>{item}</span>
                        {isChecked && (
                          <img src="/assets/tick.svg" alt="Checked" className="w-3.5 h-3 object-contain" />
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="border-b border-[#AEA793]" />

                {/* 2. Location Category */}
                <div className="space-y-2">
                  <h4 className="text-white font-bold tracking-wider uppercase text-[11px] font-body block mb-1">
                    Location
                  </h4>
                  {['North Highway 1', 'North Highway 2', 'North Highway 3', 'North Highway 4'].map((item) => {
                    const isChecked = selectedLocations.includes(item);
                    return (
                      <div
                        key={item}
                        onClick={() => toggleFilter(selectedLocations, setSelectedLocations, item)}
                        className="flex items-center justify-between text-[#AEA793] font-body cursor-pointer hover:text-white py-0.5"
                      >
                        <span>{item}</span>
                        {isChecked && (
                          <img src="/assets/tick.svg" alt="Checked" className="w-3.5 h-3 object-contain" />
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="border-b border-[#AEA793]" />

                {/* 3. CCTV Cameras Category */}
                <div className="space-y-2">
                  <h4 className="text-white font-bold tracking-wider uppercase text-[11px] font-body block mb-1">
                    CCTV Cameras
                  </h4>
                  {['Camera 13', 'Camera 14', 'Camera 15', 'Camera 16'].map((item) => {
                    const isChecked = selectedCameras.includes(item);
                    return (
                      <div
                        key={item}
                        onClick={() => toggleFilter(selectedCameras, setSelectedCameras, item)}
                        className="flex items-center justify-between text-[#AEA793] font-body cursor-pointer hover:text-white py-0.5"
                      >
                        <span>{item}</span>
                        {isChecked && (
                          <img src="/assets/tick.svg" alt="Checked" className="w-3.5 h-3 object-contain" />
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="border-b border-[#AEA793]" />

                {/* 4. Vehicle Type Category */}
                <div className="space-y-2">
                  <h4 className="text-white font-bold tracking-wider uppercase text-[11px] font-body block mb-1">
                    Vehicle Type
                  </h4>
                  {['SUV', 'TRUCK', 'SEDAN', 'AUTO'].map((item) => {
                    const isChecked = selectedTypes.includes(item);
                    return (
                      <div
                        key={item}
                        onClick={() => toggleFilter(selectedTypes, setSelectedTypes, item)}
                        className="flex items-center justify-between text-[#AEA793] font-body cursor-pointer hover:text-white py-0.5"
                      >
                        <span>{item}</span>
                        {isChecked && (
                          <img src="/assets/tick.svg" alt="Checked" className="w-3.5 h-3 object-contain" />
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="border-b border-[#AEA793]" />

                {/* 5. Vehicle Color Category */}
                <div className="space-y-2">
                  <h4 className="text-white font-bold tracking-wider uppercase text-[11px] font-body block mb-1">
                    Vehicle Color
                  </h4>
                  {['RED', 'YELLOW', 'ORANGE', 'BLUE', 'BLACK'].map((item) => {
                    const isChecked = selectedColors.includes(item);
                    return (
                      <div
                        key={item}
                        onClick={() => toggleFilter(selectedColors, setSelectedColors, item)}
                        className="flex items-center justify-between text-[#AEA793] font-body cursor-pointer hover:text-white py-0.5"
                      >
                        <span>{item}</span>
                        {isChecked && (
                          <img src="/assets/tick.svg" alt="Checked" className="w-3.5 h-3 object-contain" />
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="border-b border-[#AEA793]" />

                {/* 6. Category Section */}
                <div className="space-y-2">
                  <h4 className="text-white font-bold tracking-wider uppercase text-[11px] font-body block mb-1">
                    Category
                  </h4>
                  {['BLACKLIST', 'ANOMALY'].map((item) => {
                    const isChecked = selectedCategories.includes(item);
                    return (
                      <div
                        key={item}
                        onClick={() => toggleFilter(selectedCategories, setSelectedCategories, item)}
                        className="flex items-center justify-between text-[#AEA793] font-body cursor-pointer hover:text-white py-0.5"
                      >
                        <span>{item}</span>
                        {isChecked && (
                          <img src="/assets/tick.svg" alt="Checked" className="w-3.5 h-3 object-contain" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ================= 2. ALERTS CARDS LIST ================= */}
      <div className="space-y-4">
        {filteredAlerts.length === 0 ? (
          <div className="bg-[#1E1E1E] rounded-xl p-12 text-center text-[#A0A0A0] font-body">
            No alerts found matching your selected criteria.
          </div>
        ) : (
          filteredAlerts.map((item) => {
            const isUnverified = item.status === 'UNVERIFIED';

            return (
              <div
                key={item.id}
                className="bg-[#151515] rounded-[3px] p-5 md:px-6 flex flex-col md:flex-row md:items-center justify-between gap-6 transition-all"
              >
                {/* Left Section: Car Icon & Primary Meta */}
                <div className="flex items-center gap-5">
                  <div className="shrink-0">
                    <img
                      src={isUnverified ? '/assets/alert_car_red.svg' : '/assets/alert_car_grey.svg'}
                      alt="Alert Icon"
                      className="w-12 h-12 md:w-14 md:h-14 object-contain"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center gap-3">
                      <h2
                        className={`text-lg md:text-xl font-bold font-body tracking-wide ${
                          isUnverified ? 'text-white' : 'text-white/60 line-through'
                        }`}
                      >
                        {item.plateNumber}
                      </h2>

                      <span
                        className={`text-[10px] font-body font-bold px-2 py-0.5 rounded-[3px] tracking-wider text-[#151515] ${
                          isUnverified
                            ? 'bg-[#AC251D]'
                            : 'bg-[#A0A0A0]'
                        }`}
                      >
                        {item.type}
                      </span>
                    </div>

                    <div className="text-xs md:text-sm font-body text-white/90 space-y-0.5">
                      <p>
                        <span className="text-[#A0A0A0]">Vehicle Type : </span>
                        <span className="font-semibold text-[#AEA793]">{item.vehicleType}</span>
                      </p>
                      <p>
                        <span className="text-[#A0A0A0]">Vehicle Color : </span>
                        <span className="font-semibold text-[#AEA793]">{item.vehicleColor}</span>
                      </p>
                      <p>
                        <span className="text-[#A0A0A0]">Scanned Timestamp : </span>
                        <span className="font-semibold text-[#AEA793]">{item.scannedTimestamp}</span>
                      </p>
                    </div>
                  </div>
                </div>

                {/* Center Section: Camera & Location Info */}
                <div className="space-y-1.5 text-xs md:text-sm font-body text-white/90 min-w-[220px]">
                  <div className="flex items-center gap-2">
                    <img src="/assets/alert_camera.svg" alt="Camera" className="w-4 h-4 object-contain opacity-80" />
                    <span className="font-semibold text-[#AEA793]">{item.cameraName}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <img src="/assets/alert_location.svg" alt="Location" className="w-4 h-4 object-contain opacity-80" />
                    <span className="font-semibold text-[#AEA793]">{item.location}</span>
                  </div>
                  {item.reason && (
                    <p className="pt-0.5">
                      <span className="text-[#A0A0A0]">Reason : </span>
                      <span className="font-semibold text-[#AEA793]">{item.reason}</span>
                    </p>
                  )}
                </div>

                {/* Right Section: Confidence Badge & Verify Action Button */}
                <div className="flex flex-col items-end justify-between gap-4 shrink-0">
                  {/* Confidence rate box: No stroke, text in #151515, corner radius 3, color as per rate for unverified, #A0A0A0 for verified */}
                  <div
                    className={`px-3 py-1 rounded-[3px] font-body font-bold text-sm tracking-wider text-[#151515] ${
                      isUnverified
                        ? getConfidenceBg(item.confidence)
                        : 'bg-[#A0A0A0]'
                    }`}
                  >
                    {item.confidence} %
                  </div>

                  {/* VERIFY box button: #000000 bg & #A0A0A0 text for unverified, #A0A0A0 bg & #151515 text for verified, corner radius 3 */}
                  {isUnverified ? (
                    <button
                      onClick={() => handleVerifyAlert(item.id)}
                      className="bg-[#000000] hover:bg-white/10 text-[#A0A0A0] font-body font-bold text-xs px-5 py-2 rounded-[3px] transition-all cursor-pointer uppercase tracking-wider"
                    >
                      VERIFY
                    </button>
                  ) : (
                    <div className="bg-[#A0A0A0] text-[#151515] font-body font-bold text-xs px-5 py-2 rounded-[3px] uppercase tracking-wider">
                      VERIFIED
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
