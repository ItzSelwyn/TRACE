"""Layer 1 — Perception Module: Controlled Synthetic Demo Fallback Engine.

Provides strictly isolated, deterministic demo fallback plates for moving vehicles
and low-resolution CCTV streams where plates remain physically unreadable.
"""

from __future__ import annotations

import hashlib
import logging
import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("trace.perception.demo_fallback")


@dataclass
class DemoFallbackConfig:
    """Runtime configuration for controlled synthetic demo fallback plates."""
    enabled: bool = False
    fallback_rate: float = 0.30
    min_track_frames: int = 8
    default_state: str = "TN"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "fallback_rate": round(self.fallback_rate, 2),
            "min_track_frames": self.min_track_frames,
            "default_state": self.default_state,
        }


# Global singleton instance for runtime dynamic configuration via Admin API
_FALLBACK_CONFIG = DemoFallbackConfig()


def get_fallback_config() -> DemoFallbackConfig:
    return _FALLBACK_CONFIG


def update_fallback_config(
    enabled: Optional[bool] = None,
    fallback_rate: Optional[float] = None,
    min_track_frames: Optional[int] = None,
    default_state: Optional[str] = None,
) -> DemoFallbackConfig:
    """Update fallback configuration dynamically from Admin Panel."""
    global _FALLBACK_CONFIG
    if enabled is not None:
        _FALLBACK_CONFIG.enabled = bool(enabled)
    if fallback_rate is not None:
        _FALLBACK_CONFIG.fallback_rate = max(0.0, min(1.0, float(fallback_rate)))
    if min_track_frames is not None:
        _FALLBACK_CONFIG.min_track_frames = max(3, int(min_track_frames))
    if default_state is not None:
        _FALLBACK_CONFIG.default_state = str(default_state).upper().strip()

    logger.info(f"[OCR CONFIG] Updated Demo Fallback Config: {_FALLBACK_CONFIG.to_dict()}")
    return _FALLBACK_CONFIG


class DeterministicDemoPlateGenerator:
    """Generates stable, plausible Indian license plates seeded deterministically per track."""

    # Realistic RTO and series pools for Tamil Nadu (CBE region) and general India
    TN_RTOS = ["37", "38", "66", "76", "99", "09", "11", "22", "45", "63", "07"]
    GEN_RTOS = ["01", "02", "05", "07", "09", "10", "12", "14", "20", "33"]
    SERIES_POOLS = ["AB", "AC", "AD", "BC", "BT", "BV", "CY", "CZ", "DA", "DF", "V", "B", "E", "H", "K"]

    def __init__(self):
        # Cache of generated synthetic plates: key (dataset:cam:track_id) -> plate_text
        self._cache: Dict[str, str] = {}

    def clear_dataset(self) -> None:
        """Purge all synthetic plates when switching datasets or stopping playback."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"[OCR DEMO FALLBACK] Cleared {count} cached synthetic track plates.")

    def clear_track(self, dataset: str, camera_id: str, track_id: str) -> None:
        key = f"{dataset}:{camera_id}:{track_id}"
        self._cache.pop(key, None)

    def is_track_eligible(
        self,
        dataset: str,
        camera_id: str,
        track_id: str,
        track_frames: int,
        ocr_attempts: int,
        has_plate_evidence: bool,
        current_status: str,
    ) -> Tuple[bool, str]:
        """Verify strict eligibility criteria for synthetic demo fallback."""
        config = get_fallback_config()
        if not config.enabled:
            return False, "demo_fallback_disabled"

        if current_status in ["READ", "INFERRED"]:
            return False, "already_read_or_inferred"

        if not has_plate_evidence:
            return False, "no_plate_evidence"

        if track_frames < config.min_track_frames:
            return False, f"track_too_young_{track_frames}_lt_{config.min_track_frames}"

        if ocr_attempts < 2 and track_frames < (config.min_track_frames * 2):
            return False, "insufficient_ocr_attempts"

        # Deterministic sampling based on track identifier hash
        seed_key = f"{dataset}:{camera_id}:{track_id}"
        hash_digest = hashlib.md5(seed_key.encode("utf-8")).hexdigest()
        sample_val = (int(hash_digest[:8], 16) % 10000) / 10000.0

        if sample_val > config.fallback_rate:
            return False, f"rate_limit_sampled_out_{sample_val:.3f}_gt_{config.fallback_rate:.2f}"

        return True, "eligible"

    def generate_plate(
        self,
        dataset: str,
        camera_id: str,
        track_id: str,
        partial_text: Optional[str] = None,
    ) -> str:
        """Generate or retrieve cached deterministic synthetic plate for this track."""
        key = f"{dataset}:{camera_id}:{track_id}"
        if key in self._cache:
            return self._cache[key]

        config = get_fallback_config()
        seed_key = f"{dataset}:{camera_id}:{track_id}"
        seed_int = int(hashlib.md5(seed_key.encode("utf-8")).hexdigest()[:8], 16)
        rng = random.Random(seed_int)

        state_prefix = "TN" if dataset.upper() == "CBE" else config.default_state

        # If partial OCR exists with known state or characters, preserve them
        if partial_text and len(partial_text) >= 4:
            s = str(partial_text).upper()
            # If starts with 2 letters, preserve state prefix
            if re.match(r"^[A-Z]{2}", s):
                st = s[:2]
            else:
                st = state_prefix

            # Extract any recognizable digits or series
            clean_digits = re.findall(r"\d+", s)
            existing_num = clean_digits[-1] if clean_digits else ""
            if len(existing_num) == 4:
                num_str = existing_num
            elif len(existing_num) > 0 and len(existing_num) < 4:
                num_str = existing_num.ljust(4, str(rng.randint(1, 9)))
            else:
                num_str = f"{rng.randint(1000, 9999)}"

            rto = rng.choice(self.TN_RTOS if st == "TN" else self.GEN_RTOS)
            series = rng.choice(self.SERIES_POOLS)
            generated = f"{st}{rto}{series}{num_str}"
        else:
            # Generate clean plausible Indian plate
            st = state_prefix
            rto = rng.choice(self.TN_RTOS if st == "TN" else self.GEN_RTOS)
            series = rng.choice(self.SERIES_POOLS)
            num_val = rng.randint(1024, 9899)
            generated = f"{st}{rto}{series}{num_val}"

        self._cache[key] = generated
        return generated


# Singleton instance
_GENERATOR_INSTANCE = DeterministicDemoPlateGenerator()


def get_demo_generator() -> DeterministicDemoPlateGenerator:
    return _GENERATOR_INSTANCE
