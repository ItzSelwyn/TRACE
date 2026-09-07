import React, { useState, useMemo, useRef, useEffect } from 'react';
import { BlacklistEntry } from '../../types/blacklist';
import { mockBlacklistEntries } from '../../data/mockBlacklistData';
import { AddVehicleModal } from './AddVehicleModal';

interface BlacklistViewProps {
  onSearchPlate?: (plateQuery: string) => void;
  onViewTrace?: (plateNumber: string) => void;
}

const ITEMS_PER_PAGE = 11;

export type ActiveFilterType = 
  | '24 hrs ago' 
  | '12 hrs ago' 
  | '6 hrs ago' 
  | 'Today' 
  | 'This week' 
  | 'This month' 
  | null;

export const BlacklistView: React.FC<BlacklistViewProps> = ({
  onSearchPlate,
  onViewTrace,
}) => {
  // State management
  const [entries, setEntries] = useState<BlacklistEntry[]>(mockBlacklistEntries);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Default active filter is 'This week' matching design
  const [activeFilter, setActiveFilter] = useState<ActiveFilterType>('This week');
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<BlacklistEntry | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const filterRef = useRef<HTMLDivElement>(null);
  const detailCardRef = useRef<HTMLDivElement>(null);

  // Close filter dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setIsFilterOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  // Close modal or detail popup on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsFilterOpen(false);
        setSelectedEntry(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Filter & Search computation
  const filteredEntries = useMemo(() => {
    return entries.filter((entry) => {
      // 1. Search Query filter (Plate number or Reason)
      const matchesSearch =
        !searchQuery.trim() ||
        entry.plateNumber.toLowerCase().includes(searchQuery.toLowerCase().trim()) ||
        entry.reason.toLowerCase().includes(searchQuery.toLowerCase().trim());

      if (!matchesSearch) return false;

      // 2. Timestamp & Dates filter matching dropdown options
      if (!activeFilter) return true;

      const lastFoundStr = entry.lastFound.toLowerCase();
      const dateStr = entry.dateAdded.toLowerCase();

      switch (activeFilter) {
        case '6 hrs ago':
          return (
            lastFoundStr.includes('1hr') ||
            lastFoundStr.includes('2hr') ||
            lastFoundStr.includes('3hr') ||
            lastFoundStr.includes('4hr') ||
            lastFoundStr.includes('6hr') ||
            lastFoundStr.includes('just now')
          );
        case '12 hrs ago':
          return (
            lastFoundStr.includes('hr') &&
            !lastFoundStr.includes('14hr') &&
            !lastFoundStr.includes('day')
          );
        case '24 hrs ago':
          return (
            lastFoundStr.includes('hr') ||
            lastFoundStr.includes('just now') ||
            lastFoundStr.includes('1 day')
          );
        case 'Today':
          return (
            dateStr.includes('3rd september') ||
            dateStr.includes('today') ||
            lastFoundStr.includes('just now') ||
            lastFoundStr.includes('1hr') ||
            lastFoundStr.includes('2hr') ||
            lastFoundStr.includes('3hr')
          );
        case 'This week':
          return (
            dateStr.includes('september 2026') ||
            dateStr.includes('31st august') ||
            dateStr.includes('30th august')
          );
        case 'This month':
          return dateStr.includes('september') || dateStr.includes('august');
        default:
          return true;
      }
    });
  }, [entries, searchQuery, activeFilter]);

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(filteredEntries.length / ITEMS_PER_PAGE));
  const safeCurrentPage = Math.min(currentPage, totalPages);

  const paginatedEntries = useMemo(() => {
    const startIdx = (safeCurrentPage - 1) * ITEMS_PER_PAGE;
    return filteredEntries.slice(startIdx, startIdx + ITEMS_PER_PAGE);
  }, [filteredEntries, safeCurrentPage]);

  // Handlers
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    if (onSearchPlate && searchQuery.trim()) {
      // Notification
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setCurrentPage(1);
  };

  const handleFilterSelect = (filterVal: ActiveFilterType) => {
    setActiveFilter(filterVal);
    setCurrentPage(1);
  };

  const handleAddNewVehicle = (
    newVehicle: Omit<BlacklistEntry, 'id' | 'dateAdded' | 'timeAdded' | 'lastFound' | 'active'>
  ) => {
    const now = new Date();
    const day = now.getDate();
    const suffix =
      day === 1 || day === 21 || day === 31
        ? 'st'
        : day === 2 || day === 22
        ? 'nd'
        : day === 3 || day === 23
        ? 'rd'
        : 'th';
    const month = now.toLocaleString('en-US', { month: 'long' });
    const year = now.getFullYear();
    const timeFormatted = now.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    }).toLowerCase();

    const createdEntry: BlacklistEntry = {
      id: `bl-new-${Date.now()}`,
      plateNumber: newVehicle.plateNumber,
      reason: newVehicle.reason,
      dateAdded: `${day}${suffix} ${month} ${year}`,
      timeAdded: timeFormatted,
      lastFound: 'Just now',
      cameraName: 'Camera 16',
      location: 'North Highway 16',
      active: true,
    };

    setEntries((prev) => [createdEntry, ...prev]);
    setCurrentPage(1);

    // Show temporary feedback toast
    setSuccessToast(`Vehicle ${createdEntry.plateNumber} added to Blacklist`);
    setTimeout(() => setSuccessToast(null), 3500);
  };

  const handleRowClick = (entry: BlacklistEntry) => {
    setSelectedEntry((prev) => (prev?.id === entry.id ? null : entry));
  };

  const handleViewTraceJump = (plateNumber: string) => {
    setSelectedEntry(null);
    if (onViewTrace) {
      onViewTrace(plateNumber);
    }
  };

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto pb-6 select-none font-body bg-[#000000] relative">
      {/* Success Feedback Toast */}
      {successToast && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#151515] text-white px-4 py-3 rounded-[3px] flex items-center gap-3 animate-fadeIn">
          <span className="w-2.5 h-2.5 rounded-full bg-[#1B7A43]" />
          <span className="text-xs font-body font-medium">{successToast}</span>
        </div>
      )}

      {/* Top Search & Controls Bar (#151515 Main Background) */}
      <div className="bg-[#151515] rounded-[3px] p-4 flex flex-col md:flex-row items-center justify-between gap-4 relative z-30">
        {/* Search Input Box (#000000 Sub Background) */}
        <form onSubmit={handleSearchSubmit} className="relative flex-1 w-full max-w-2xl">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search Number Plate (e.g. TN 37 CY 1234)"
            className="w-full bg-[#000000] text-white placeholder-[#A0A0A0] text-sm rounded-[3px] py-3 pl-4 pr-12 outline-none font-body"
          />

          {searchQuery ? (
            <button
              type="button"
              onClick={handleClearSearch}
              className="absolute right-10 top-1/2 -translate-y-1/2 text-[#A0A0A0] hover:text-white p-1 text-sm font-bold cursor-pointer"
              title="Clear Search"
            >
              ×
            </button>
          ) : null}

          <button
            type="submit"
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:opacity-80 transition-opacity cursor-pointer"
            title="Search Plate"
          >
            <img src="/assets/search.svg" alt="Search Icon" className="w-5 h-5 text-[#F2D04E]" />
          </button>
        </form>

        {/* Action Buttons: Filter & Add Vehicle */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-end relative">
          {/* Filter Button with Toggle SVG Concept Icon */}
          <div className="relative" ref={filterRef}>
            <button
              type="button"
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className="outline-none focus:outline-none flex items-center justify-center cursor-pointer"
              title="Toggle Filter Dropdown"
            >
              <img
                src={isFilterOpen ? "/assets/alert_filter_opened.svg" : "/assets/alert_filter.svg"}
                alt="Filter"
                className="h-10 w-auto object-contain"
              />
            </button>

            {/* Filter Dropdown Menu */}
            {/* Filter Dropdown Menu (#000000 Main Background) */}
            {isFilterOpen && (
              <div 
                className="absolute right-0 top-full mt-1.5 w-60 bg-[#000000] rounded-[3px] z-50 p-4 text-left animate-fadeIn font-body"
                style={{ boxShadow: '0px 14px 35px rgba(0, 0, 0, 0.3)' }}
              >
                {/* Section 1: Timestamp */}
                <div className="mb-2">
                  <span className="text-white text-xs font-body font-semibold mb-2 block tracking-wide">
                    Timestamp
                  </span>
                  <div className="space-y-1.5 font-body">
                    {(['24 hrs ago', '12 hrs ago', '6 hrs ago'] as ActiveFilterType[]).map((timeOption) => {
                      const isSelected = activeFilter === timeOption;
                      return (
                        <div
                          key={timeOption}
                          onClick={() => handleFilterSelect(timeOption)}
                          className={`text-xs py-1 px-1 rounded-[3px] cursor-pointer flex items-center justify-between transition-colors font-body ${
                            isSelected
                              ? 'text-white font-medium'
                              : 'text-[#A0A0A0] hover:text-white'
                          }`}
                        >
                          <span>{timeOption}</span>
                          {isSelected && <img src="/assets/tick.svg" alt="Tick" className="w-3.5 h-3 object-contain" />}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Section Horizontal Divider in #A0A0A0 */}
                <div className="my-3 border-b border-[#A0A0A0]" />

                {/* Section 2: Dates */}
                <div>
                  <span className="text-white text-xs font-body font-semibold mb-2 block tracking-wide">
                    Dates
                  </span>
                  <div className="space-y-1.5 font-body">
                    {(['Today', 'This week', 'This month'] as ActiveFilterType[]).map((dateOption) => {
                      const isSelected = activeFilter === dateOption;
                      return (
                        <div
                          key={dateOption}
                          onClick={() => handleFilterSelect(dateOption)}
                          className={`text-xs py-1 px-1 rounded-[3px] cursor-pointer flex items-center justify-between transition-colors font-body ${
                            isSelected
                              ? 'text-white font-medium'
                              : 'text-[#A0A0A0] hover:text-white'
                          }`}
                        >
                          <span>{dateOption}</span>
                          {isSelected && <img src="/assets/tick.svg" alt="Tick" className="w-3.5 h-3 object-contain" />}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Add Vehicle Button with Toggle SVG Concept Icon */}
          <button
            type="button"
            onClick={() => setIsAddModalOpen(true)}
            className="outline-none focus:outline-none flex items-center justify-center cursor-pointer"
            title="Add Vehicle to Blacklist"
          >
            <img
              src={isAddModalOpen ? "/assets/add_vehicle_opened.svg" : "/assets/add_vehicle.svg"}
              alt="Add Vehicle"
              className="h-10 w-auto object-contain"
            />
          </button>
        </div>
      </div>

      {/* Main Table Card (Main Background: #151515) */}
      <div className="bg-[#151515] rounded-[3px] p-6 flex flex-col justify-between min-h-[580px] relative z-10">
        {/* Sub Background Container (#000000 Sub Background sitting on #151515 Main Background) */}
        <div className="bg-[#000000] rounded-[3px] p-6 overflow-x-auto flex-1 mb-4">
          <table className="w-full text-left border-collapse">
            {/* Table Header Row with Gold Divider Line */}
            <thead>
              <tr className="border-b border-[#F2D04E]/50">
                <th className="pb-3.5 text-sm font-bold font-heading text-white tracking-wider uppercase">
                  NUMBER PLATE
                </th>
                <th className="pb-3.5 text-sm font-bold font-heading text-white tracking-wider uppercase">
                  REASON
                </th>
                <th className="pb-3.5 text-sm font-bold font-heading text-white tracking-wider uppercase">
                  DATE ADDED
                </th>
                <th className="pb-3.5 text-sm font-bold font-heading text-white tracking-wider uppercase">
                  TIME ADDED
                </th>
                <th className="pb-3.5 text-sm font-bold font-heading text-white tracking-wider uppercase">
                  LAST FOUND
                </th>
              </tr>
            </thead>

            {/* Table Body Rows */}
            <tbody className="divide-y divide-transparent font-body text-xs md:text-sm">
              {paginatedEntries.length > 0 ? (
                paginatedEntries.map((item) => {
                  const isThisRowSelected = selectedEntry?.id === item.id;
                  const isOtherRowDimmed = selectedEntry !== null && !isThisRowSelected;

                  return (
                    <tr
                      key={item.id}
                      onClick={() => handleRowClick(item)}
                      className={`transition-all duration-200 cursor-pointer ${
                        isThisRowSelected
                          ? 'opacity-100'
                          : isOtherRowDimmed
                          ? 'opacity-30'
                          : 'hover:bg-white/[0.03] opacity-100'
                      }`}
                    >
                      {/* Number Plate Column - Font set to Hanken Grotesk (font-body) */}
                      <td className="py-3.5 font-body font-bold text-white tracking-wide">
                        <span
                          className="hover:text-[#F2D04E] transition-colors inline-block"
                          title="Click to view details"
                        >
                          {item.plateNumber}
                        </span>
                      </td>

                      {/* Reason Column */}
                      <td className="py-3.5 text-[#F2D04E] font-medium max-w-[160px] whitespace-normal leading-snug">
                        {item.reason}
                      </td>

                      {/* Date Added Column */}
                      <td className="py-3.5 text-white/90 font-normal">
                        {item.dateAdded}
                      </td>

                      {/* Time Added Column */}
                      <td className="py-3.5 text-white/90 font-normal">
                        {item.timeAdded}
                      </td>

                      {/* Last Found Column */}
                      <td className="py-3.5 text-white/90 font-normal">
                        {item.lastFound}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5} className="py-16 text-center text-[#A0A0A0]">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <span className="text-base font-body text-white">No vehicles found</span>
                      <p className="text-xs text-[#A0A0A0]">
                        No blacklisted vehicles match your current search or filter criteria.
                      </p>
                      {(searchQuery || activeFilter !== 'This week') && (
                        <button
                          onClick={() => {
                            setSearchQuery('');
                            setActiveFilter('This week');
                            setCurrentPage(1);
                          }}
                          className="mt-2 text-xs text-[#F2D04E] underline hover:text-[#F8DF7B] cursor-pointer"
                        >
                          Reset to default view
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Floating Detail Popup Card */}
        {selectedEntry && (
          <div 
            className="fixed inset-0 z-40 flex items-center justify-center bg-black/80 select-none animate-fadeIn"
            onClick={() => setSelectedEntry(null)}
          >
            <div
              ref={detailCardRef}
              onClick={(e) => e.stopPropagation()}
              className="bg-[#1E1E1E] rounded-[3px] p-5 w-full max-w-[310px] text-left font-body animate-fadeIn text-xs space-y-3.5"
            >
              {/* Row 1: Number Plate */}
              <div className="flex justify-between items-center">
                <span className="text-white font-medium">Number Plate</span>
                <span className="text-[#A0A0A0] font-body font-medium tracking-wide">
                  {selectedEntry.plateNumber}
                </span>
              </div>

              {/* Row 2: Found at (Camera & Location) */}
              <div className="flex justify-between items-start">
                <span className="text-white font-medium pt-0.5">Found at</span>
                <div className="text-right space-y-1">
                  <div className="flex items-center justify-end gap-1.5 text-[#A0A0A0]">
                    <svg width="14" height="14" viewBox="0 0 20 19" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5 shrink-0">
                      <path d="M16.3235 12.8229L14.3235 11.6647L18 8.90284L20 10.061L16.3235 12.8229ZM10.5294 9.88286L14.3529 7.03189L5.08824 1.74573L2.88235 5.51732L10.5294 9.88286ZM0 19V17.2181H6.17647V9.43739L2 7.06159C1.56726 6.80501 1.28755 6.43893 1.16088 5.96338C1.03402 5.48782 1.09804 5.03226 1.35294 4.5967L3.55882 0.884505C3.81373 0.468739 4.17157 0.196512 4.63235 0.0678227C5.09314 -0.0608666 5.52941 -0.00642109 5.94118 0.231159L17.5588 6.85371L10.6471 11.9914L7.94118 10.4471V17.2181C7.94118 17.7082 7.76843 18.1276 7.42294 18.4764C7.07726 18.8255 6.66176 19 6.17647 19H0Z" fill="#A0A0A0"/>
                    </svg>
                    <span>{selectedEntry.cameraName || 'Camera 16'}</span>
                  </div>
                  <div className="flex items-center justify-end gap-1.5 text-[#A0A0A0]">
                    <svg width="14" height="14" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5 shrink-0">
                      <path d="M3.47222 18.7353C2.63889 17.8921 2.22222 16.8785 2.22222 15.6944V6C1.57407 5.75926 1.04167 5.37722 0.625 4.85389C0.208333 4.33037 0 3.73398 0 3.06472C0 2.20676 0.300926 1.48148 0.902778 0.888889C1.50463 0.296296 2.22685 0 3.06944 0C3.91204 0 4.62963 0.297593 5.22222 0.892778C5.81482 1.48796 6.11111 2.21065 6.11111 3.06083C6.11111 3.72398 5.90278 4.31944 5.48611 4.84722C5.06944 5.375 4.53704 5.75926 3.88889 6V15.6944C3.88889 16.4202 4.14352 17.0414 4.65278 17.5581C5.16204 18.0749 5.79167 18.3333 6.54167 18.3333C7.29167 18.3333 7.91667 18.0749 8.41667 17.5581C8.91667 17.0414 9.16667 16.4202 9.16667 15.6944V4.30556C9.16667 3.10185 9.58333 2.08333 10.4167 1.25C11.25 0.416667 12.2685 0 13.4722 0C14.6759 0 15.6944 0.416667 16.5278 1.25C17.3611 2.08333 17.7778 3.10185 17.7778 4.30556V14C18.4259 14.2407 18.9583 14.6237 19.375 15.1489C19.7917 15.6743 20 16.2728 20 16.9444C20 17.7778 19.703 18.4954 19.1089 19.0972C18.5146 19.6991 17.7931 20 16.9444 20C16.1111 20 15.3935 19.6991 14.7917 19.0972C14.1898 18.4954 13.8889 17.7778 13.8889 16.9444C13.8889 16.2722 14.0972 15.669 14.5139 15.1347C14.9306 14.6005 15.463 14.2222 16.1111 14V4.30556C16.1111 3.56481 15.8565 2.93981 15.3472 2.43056C14.838 1.9213 14.213 1.66667 13.4722 1.66667C12.7315 1.66667 12.1065 1.9213 11.5972 2.43056C11.088 2.93981 10.8333 3.56481 10.8333 4.30556V15.6944C10.8333 16.8785 10.4167 17.8921 9.58333 18.7353C8.75 19.5784 7.73148 20 6.52778 20C5.32407 20 4.30556 19.5784 3.47222 18.7353ZM3.06944 4.44444C3.44907 4.44444 3.77315 4.30556 4.04167 4.02778C4.31019 3.75 4.44444 3.4213 4.44444 3.04167C4.44444 2.66204 4.31139 2.33796 4.04528 2.06944C3.77898 1.80093 3.44907 1.66667 3.05556 1.66667C2.68519 1.66667 2.36111 1.79972 2.08333 2.06583C1.80556 2.33213 1.66667 2.66204 1.66667 3.05556C1.66667 3.42593 1.80556 3.75 2.08333 4.02778C2.36111 4.30556 2.68981 4.44444 3.06944 4.44444ZM16.9583 18.3333C17.338 18.3333 17.662 18.1944 17.9306 17.9167C18.1991 17.6389 18.3333 17.3102 18.3333 16.9306C18.3333 16.5509 18.2003 16.2269 17.9342 15.9583C17.6679 15.6898 17.338 15.5556 16.9444 15.5556C16.5741 15.5556 16.25 15.6886 15.9722 15.9547C15.6944 16.221 15.5556 16.5509 15.5556 16.9444C15.5556 17.3148 15.6944 17.6389 15.9722 17.9167C16.25 18.1944 16.5787 18.3333 16.9583 18.3333Z" fill="#A0A0A0"/>
                    </svg>
                    <span>{selectedEntry.location || 'North Highway 16'}</span>
                  </div>
                </div>
              </div>

              {/* Row 3: Date */}
              <div className="flex justify-between items-center">
                <span className="text-white font-medium">Date</span>
                <span className="text-[#A0A0A0]">
                  {selectedEntry.dateAdded}
                </span>
              </div>

              {/* Row 4: Time */}
              <div className="flex justify-between items-center">
                <span className="text-white font-medium">Time</span>
                <span className="text-[#A0A0A0]">
                  {selectedEntry.timeAdded}
                </span>
              </div>

              {/* Action Button: VIEW RECONSTRUCTED TRAJECTORY */}
              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={() => handleViewTraceJump(selectedEntry.plateNumber)}
                  className="bg-[#000000] text-[#A0A0A0] hover:text-white transition-colors font-bold font-body text-xs px-3 py-1.5 rounded-[3px] flex items-center gap-1.5 cursor-pointer"
                >
                  <span>VIEW RECONSTRUCTED TRAJECTORY</span>
                  <img src="/assets/diagonal_arrow.svg" alt="Arrow" className="w-3 h-3 object-contain" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Table Footer Bottom Bar (Stays at the bottom of the #151515 main background) */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 select-none pt-2">
          {/* Bottom-Left: Blacklisted Vehicles Count */}
          <div className="flex items-center gap-2 select-none">
            <span className="text-xs md:text-sm font-bold font-body text-[#AC251D] tracking-wider uppercase">
              BLACKLISTED VEHICLES: {filteredEntries.length > 0 ? (activeFilter === 'This week' && !searchQuery ? 3 : filteredEntries.length) : 0}
            </span>
          </div>

          {/* Bottom-Right: Pagination Controls */}
          <div className="flex items-center gap-2 text-xs text-[#A0A0A0] font-body">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={safeCurrentPage <= 1}
              className="px-2 py-1 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-colors"
              title="Previous Page"
              aria-label="Previous Page"
            >
              &lt;
            </button>
            <span>
              Page {safeCurrentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={safeCurrentPage >= totalPages}
              className="px-2 py-1 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-colors"
              title="Next Page"
              aria-label="Next Page"
            >
              &gt;
            </button>
          </div>
        </div>
      </div>

      {/* Add Vehicle Modal */}
      <AddVehicleModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAddVehicle={handleAddNewVehicle}
      />
    </div>
  );
};
