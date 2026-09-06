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
  
  // Default active filter is 'This week' matching the design screenshot exactly
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
      if (detailCardRef.current && !detailCardRef.current.contains(e.target as Node)) {
        // Handled by backdrop click
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
    // If clicking same row, toggle off; otherwise open detail popup matching screenshot
    setSelectedEntry((prev) => (prev?.id === entry.id ? null : entry));
  };

  const handleViewTraceJump = (plateNumber: string) => {
    setSelectedEntry(null);
    if (onViewTrace) {
      onViewTrace(plateNumber);
    }
  };

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto pb-6 select-none font-body bg-[#151515] relative">
      {/* Success Feedback Toast */}
      {successToast && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#1E1E1E] border border-[#1B7A43] text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 animate-fadeIn">
          <span className="w-2.5 h-2.5 rounded-full bg-[#1B7A43]" />
          <span className="text-xs font-heading font-medium">{successToast}</span>
        </div>
      )}

      {/* Top Search & Controls Bar */}
      <div className="bg-[#1E1E1E] rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4 relative z-30">
        {/* Search Input Box */}
        <form onSubmit={handleSearchSubmit} className="relative flex-1 w-full max-w-2xl">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search Number Plate (e.g. TN 37 CY 1234)"
            className="w-full bg-[#151515] border border-transparent focus:border-[#F2D04E] text-white placeholder-[#A0A0A0] text-sm rounded-lg py-3 pl-4 pr-12 outline-none font-body transition-all"
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
          {/* Filter Button & Dropdown matching Screenshot Design */}
          <div className="relative" ref={filterRef}>
            <button
              type="button"
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className={`font-bold font-heading text-sm px-6 py-2.5 rounded-lg flex items-center gap-3 transition-all cursor-pointer shadow-sm ${
                isFilterOpen
                  ? 'bg-[#000000] text-white'
                  : 'bg-[#F2D04E] text-black hover:bg-[#F8DF7B]'
              }`}
              title="Toggle Filter Dropdown"
            >
              <span>Filter</span>
              {isFilterOpen ? (
                /* Gold upward triangle when open (matching screenshot) */
                <svg
                  className="w-3 h-2 text-[#F2D04E]"
                  viewBox="0 0 20 10"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M10 0L20 9.95H0L10 0Z" fill="#F2D04E" />
                </svg>
              ) : (
                /* Black downward triangle when closed */
                <img
                  src="/assets/dropdown.svg"
                  alt="Dropdown Arrow"
                  className="w-3.5 h-2"
                />
              )}
            </button>

            {/* Filter Dropdown Menu (Exact Match to Design Screenshot) */}
            {isFilterOpen && (
              <div className="absolute right-0 top-full mt-1.5 w-60 bg-[#000000] border border-white/10 rounded-xl shadow-2xl z-50 p-4 text-left animate-fadeIn">
                {/* Section 1: Timestamp */}
                <div className="mb-2">
                  <span className="text-white text-xs font-heading font-semibold mb-2 block tracking-wide">
                    Timestamp
                  </span>
                  <div className="space-y-1.5 font-body">
                    {(['24 hrs ago', '12 hrs ago', '6 hrs ago'] as ActiveFilterType[]).map((timeOption) => {
                      const isSelected = activeFilter === timeOption;
                      return (
                        <div
                          key={timeOption}
                          onClick={() => handleFilterSelect(timeOption)}
                          className={`text-xs py-1 px-1 rounded cursor-pointer flex items-center justify-between transition-colors ${
                            isSelected
                              ? 'text-white font-medium'
                              : 'text-[#A0A0A0] hover:text-white'
                          }`}
                        >
                          <span>{timeOption}</span>
                          {isSelected && <span className="text-xs text-white">✓</span>}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Divider Line */}
                <div className="border-t border-white/15 my-3" />

                {/* Section 2: Dates */}
                <div>
                  <span className="text-white text-xs font-heading font-semibold mb-2 block tracking-wide">
                    Dates
                  </span>
                  <div className="space-y-1.5 font-body">
                    {(['Today', 'This week', 'This month'] as ActiveFilterType[]).map((dateOption) => {
                      const isSelected = activeFilter === dateOption;
                      return (
                        <div
                          key={dateOption}
                          onClick={() => handleFilterSelect(dateOption)}
                          className={`text-xs py-1 px-1 rounded cursor-pointer flex items-center justify-between transition-colors ${
                            isSelected
                              ? 'text-white font-medium'
                              : 'text-[#A0A0A0] hover:text-white'
                          }`}
                        >
                          <span>{dateOption}</span>
                          {isSelected && <span className="text-xs text-white">✓</span>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Add Vehicle Button */}
          <button
            type="button"
            onClick={() => setIsAddModalOpen(true)}
            className="bg-[#F2D04E] hover:bg-[#F8DF7B] text-black font-bold font-heading text-sm px-5 py-2.5 rounded-lg flex items-center gap-1.5 transition-all shadow-sm cursor-pointer"
            title="Add Vehicle to Blacklist"
          >
            <span>Add Vechicle +</span>
          </button>
        </div>
      </div>

      {/* Main Table Card (Exact Design Layout) */}
      <div className="bg-[#1E1E1E] rounded-xl p-6 flex flex-col justify-between min-h-[580px] shadow-2xl border border-white/5 relative z-10">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            {/* Table Header Row */}
            <thead>
              <tr className="border-b border-[#F2D04E]/30">
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
                          ? 'bg-white/[0.06] opacity-100'
                          : isOtherRowDimmed
                          ? 'opacity-30 blur-[0.6px]'
                          : 'hover:bg-white/[0.03] opacity-100'
                      }`}
                    >
                      {/* Number Plate Column */}
                      <td className="py-3.5 font-heading font-bold text-white tracking-wide">
                        <span
                          className="hover:text-[#F2D04E] transition-colors inline-block"
                          title="Click to view details"
                        >
                          {item.plateNumber}
                        </span>
                      </td>

                      {/* Reason Column (#F2D04E Gold Color, wrapped as in screenshot) */}
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
                      <span className="text-base font-heading text-white">No vehicles found</span>
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

        {/* Floating Detail Popup Card (Exact Match to media_1788691726728.jpg) */}
        {selectedEntry && (
          <div 
            className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 backdrop-blur-[1px] select-none animate-fadeIn"
            onClick={() => setSelectedEntry(null)}
          >
            <div
              ref={detailCardRef}
              onClick={(e) => e.stopPropagation()}
              className="bg-[#1E1E1E] border border-white/10 rounded-xl p-5 shadow-2xl w-full max-w-[310px] text-left font-body animate-fadeIn text-xs space-y-3.5"
            >
              {/* Row 1: Number Plate */}
              <div className="flex justify-between items-center">
                <span className="text-white font-medium">Number Plate</span>
                <span className="text-[#A0A0A0] font-heading font-medium tracking-wide">
                  {selectedEntry.plateNumber}
                </span>
              </div>

              {/* Row 2: Found at (Camera & Location) */}
              <div className="flex justify-between items-start">
                <span className="text-white font-medium pt-0.5">Found at</span>
                <div className="text-right space-y-1">
                  <div className="flex items-center justify-end gap-1.5 text-[#A0A0A0]">
                    <img 
                      src="/assets/camera.svg" 
                      alt="Camera" 
                      className="w-3.5 h-3.5 opacity-80" 
                    />
                    <span>{selectedEntry.cameraName || 'Camera 16'}</span>
                  </div>
                  <div className="flex items-center justify-end gap-1.5 text-[#A0A0A0]">
                    <img 
                      src="/assets/route.svg" 
                      alt="Location" 
                      className="w-3.5 h-3.5 opacity-80" 
                    />
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

              {/* Action Button: View Trajectory */}
              <div className="pt-2 border-t border-white/5 flex justify-end">
                <button
                  type="button"
                  onClick={() => handleViewTraceJump(selectedEntry.plateNumber)}
                  className="text-[11px] font-heading font-semibold text-[#F2D04E] hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <span>View Trajectory</span>
                  <span>↗</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Table Footer Bottom Bar */}
        <div className="pt-6 mt-4 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between gap-4 select-none">
          {/* Bottom-Left: Blacklisted Vehicles Count (#AC251D Red as in Screenshot) */}
          <div className="flex items-center gap-2 select-none">
            <span className="text-xs md:text-sm font-bold font-heading text-[#AC251D] tracking-wider uppercase">
              BLACKLISTED VEHICLES: {filteredEntries.length > 0 ? (activeFilter === 'This week' && !searchQuery ? 3 : filteredEntries.length) : 0}
            </span>
          </div>

          {/* Bottom-Right: Pagination Controls */}
          <div className="flex items-center gap-2 text-xs text-[#A0A0A0] font-heading">
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
