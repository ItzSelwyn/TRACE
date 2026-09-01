import React, { useState } from 'react';
import { TopSummaryStats } from '../../types/dashboard';

interface TopStatsHeaderProps {
  stats: TopSummaryStats;
  onSearch?: (plateQuery: string) => void;
}

export const TopStatsHeader: React.FC<TopStatsHeaderProps> = ({ stats, onSearch }) => {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch && searchQuery.trim()) {
      onSearch(searchQuery.trim());
    }
  };

  return (
    <div className="bg-[#1E1E1E] rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4 select-none">
      {/* Search Input Box */}
      <form onSubmit={handleSubmit} className="relative flex-1 w-full max-w-2xl">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search Number Plate (e.g. TN 37 CY 1234)"
          className="w-full bg-[#151515] focus:border-[#F2D04E] text-white placeholder-[#A0A0A0] text-sm rounded-lg py-3 pl-4 pr-12 outline-none transition-all font-body"
        />
        <button
          type="submit"
          className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:opacity-80 transition-opacity"
          title="Search Plate"
        >
          <img src="/assets/search.svg" alt="Search Icon" className="w-5 h-5 text-[#F2D04E]" />
        </button>
      </form>

      {/* Summary KPI Metrics */}
      <div className="flex items-center justify-between w-full md:w-auto gap-8 px-2">
        {/* Active Scans */}
        <div className="flex flex-col items-start md:items-center">
          <span className="text-[11px] font-bold tracking-wider text-[#A0A0A0] font-heading uppercase">
            ACTIVE SCANS
          </span>
          <span className="text-2xl font-semibold text-white font-body">
            {stats.activeScans}
          </span>
        </div>

        {/* Blacklists */}
        <div className="flex flex-col items-start md:items-center">
          <span className="text-[11px] font-bold tracking-wider text-[#A0A0A0] font-heading uppercase">
            BLACKLISTS
          </span>
          <span className="text-2xl font-semibold text-white font-body">
            {stats.blacklistsCount}
          </span>
        </div>

        {/* System Status */}
        <div className="flex flex-col items-start md:items-center">
          <span className="text-[11px] font-bold tracking-wider text-[#A0A0A0] font-heading uppercase">
            SYSTEM STATUS
          </span>
          <span className="text-2xl font-semibold text-white font-body">
            {stats.systemStatus}
          </span>
        </div>
      </div>
    </div>
  );
};
