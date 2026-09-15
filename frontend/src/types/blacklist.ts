/**
 * TRACE Blacklist Data Interfaces
 * Compatible with Backend Schema v1.0 (blacklist_entries) and UI/UX Brief v1.0
 */

export interface BlacklistEntry {
  id: string;
  plateNumber: string;
  reason: string;
  dateAdded: string;
  timeAdded: string;
  lastFound: string;
  cameraName?: string;
  location?: string;
  addedBy?: string;
  active?: boolean;
}

export interface BlacklistFilterOptions {
  searchQuery: string;
  activeFilter: string | null;
}
