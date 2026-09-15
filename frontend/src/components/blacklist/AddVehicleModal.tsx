import React, { useState, useEffect } from 'react';
import { BlacklistEntry } from '../../types/blacklist';

interface AddVehicleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddVehicle: (entry: Omit<BlacklistEntry, 'id' | 'dateAdded' | 'timeAdded' | 'lastFound' | 'active'>) => void;
}

export const AddVehicleModal: React.FC<AddVehicleModalProps> = ({
  isOpen,
  onClose,
  onAddVehicle,
}) => {
  const [plateNumber, setPlateNumber] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanPlate = plateNumber.trim().toUpperCase();
    if (!cleanPlate) {
      setError('Please enter a number plate.');
      return;
    }

    const cleanReason = reason.trim() || 'Illegal transportation';

    onAddVehicle({
      plateNumber: cleanPlate,
      reason: cleanReason,
    });

    // Reset & close
    setPlateNumber('');
    setReason('');
    setError('');
    onClose();
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs select-none animate-fadeIn"
      onClick={onClose}
    >
      {/* Modal Container matching screenshot design */}
      <div 
        className="bg-[#1E1E1E] rounded-lg w-full max-w-[370px] p-5 relative transition-all text-left font-body"
        onClick={(e) => e.stopPropagation()}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-[#AC251D]/20 text-[#AC251D] text-xs px-3 py-1.5 rounded">
              {error}
            </div>
          )}

          {/* Number Plate Field */}
          <div>
            <label className="text-white text-xs font-medium mb-1.5 block">
              Number Plate
            </label>
            <input
              type="text"
              value={plateNumber}
              onChange={(e) => {
                setPlateNumber(e.target.value);
                if (error) setError('');
              }}
              placeholder="e.g. TN 37 CY 1234"
              className="w-full bg-[#000000] text-white placeholder-[#666666] text-xs rounded py-2 px-3 outline-none font-body uppercase transition-all"
              autoFocus
            />
          </div>

          {/* Reason Field (Textarea as shown in screenshot) */}
          <div>
            <label className="text-white text-xs font-medium mb-1.5 block">
              Reason
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Type a reason for adding this vehicle..."
              rows={4}
              className="w-full bg-[#000000] text-white placeholder-[#666666] text-xs rounded p-3 outline-none font-body resize-none transition-all h-28"
            />
          </div>

          {/* Bottom Right Add Vehicle Button */}
          <div className="flex justify-end pt-1">
            <button
              type="submit"
              className="bg-[#F2D04E] hover:bg-[#F8DF7B] text-black font-bold font-heading text-xs px-3.5 py-1.5 rounded transition-all cursor-pointer"
              title="Add Vehicle"
            >
              Add Vehicle
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
