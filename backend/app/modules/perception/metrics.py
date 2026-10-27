"""Layer 1 — Perception Module: Lightweight Performance & Throughput Metrics Tracker.
=====================================================================================
Monitors and logs real-time pipeline performance metrics:
- YOLO: total video frames, inference frames, skipped frames, latency, approx FPS
- OCR: plates processed, attempts, short-circuits, fallback variants used, latency
- Re-ID: model calls, reused embeddings, latency
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict

logger = logging.getLogger("trace.perception.metrics")


class PipelinePerformanceMetrics:
    """Thread-safe telemetry accumulator for real-time video perception benchmarking."""

    def __init__(self, summary_interval_s: float = 5.0):
        self._lock = threading.RLock()
        self.summary_interval_s = summary_interval_s
        self.start_time = time.time()
        self.last_summary_time = time.time()

        # YOLO metrics
        self.total_video_frames: int = 0
        self.yolo_inference_frames: int = 0
        self.yolo_skipped_frames: int = 0
        self.yolo_total_time_ms: float = 0.0

        # OCR metrics
        self.ocr_plates_processed: int = 0
        self.ocr_attempts: int = 0
        self.ocr_short_circuits: int = 0
        self.ocr_fallbacks_used: int = 0
        self.ocr_total_time_ms: float = 0.0

        # Re-ID metrics
        self.reid_calls: int = 0
        self.reid_reused: int = 0
        self.reid_total_time_ms: float = 0.0

    def reset(self):
        """Reset counters for a new benchmark window."""
        with self._lock:
            self.start_time = time.time()
            self.last_summary_time = time.time()
            self.total_video_frames = 0
            self.yolo_inference_frames = 0
            self.yolo_skipped_frames = 0
            self.yolo_total_time_ms = 0.0
            self.ocr_plates_processed = 0
            self.ocr_attempts = 0
            self.ocr_short_circuits = 0
            self.ocr_fallbacks_used = 0
            self.ocr_total_time_ms = 0.0
            self.reid_calls = 0
            self.reid_reused = 0
            self.reid_total_time_ms = 0.0

    def record_video_frame(self, yolo_ran: bool, latency_ms: float = 0.0, **kwargs):
        """Record video frame processing and whether YOLO was executed or skipped."""
        lat = latency_ms or kwargs.get("yolo_latency_ms", 0.0)
        with self._lock:
            self.total_video_frames += 1
            if yolo_ran:
                self.yolo_inference_frames += 1
                self.yolo_total_time_ms += lat
            else:
                self.yolo_skipped_frames += 1

    def record_ocr_attempt(
        self,
        latency_ms: float,
        short_circuited: bool,
        fallbacks_count: int,
        plate_found: bool = True,
    ):
        """Record an OCR recognition event, tracking short-circuit and fallback counts."""
        with self._lock:
            self.ocr_attempts += 1
            self.ocr_total_time_ms += latency_ms
            if short_circuited:
                self.ocr_short_circuits += 1
            if fallbacks_count > 0:
                self.ocr_fallbacks_used += fallbacks_count
            if plate_found:
                self.ocr_plates_processed += 1

    def record_reid_call(self, latency_ms: float, reused: bool = False):
        """Record ResNet34 appearance embedding extraction or memory reuse."""
        with self._lock:
            if reused:
                self.reid_reused += 1
            else:
                self.reid_calls += 1
                self.reid_total_time_ms += latency_ms

    def get_stats(self) -> Dict[str, Any]:
        """Return a snapshot dictionary of current performance metrics."""
        with self._lock:
            now = time.time()
            elapsed_s = max(0.001, now - self.start_time)
            yolo_avg_ms = (
                (self.yolo_total_time_ms / self.yolo_inference_frames)
                if self.yolo_inference_frames > 0
                else 0.0
            )
            yolo_fps = (1000.0 / yolo_avg_ms) if yolo_avg_ms > 0 else 0.0
            video_fps = self.total_video_frames / elapsed_s
            ocr_avg_ms = (
                (self.ocr_total_time_ms / self.ocr_attempts)
                if self.ocr_attempts > 0
                else 0.0
            )
            reid_avg_ms = (
                (self.reid_total_time_ms / self.reid_calls)
                if self.reid_calls > 0
                else 0.0
            )
            return {
                "total_video_frames": self.total_video_frames,
                "yolo_inference_frames": self.yolo_inference_frames,
                "yolo_skipped_frames": self.yolo_skipped_frames,
                "yolo_avg_latency_ms": round(yolo_avg_ms, 2),
                "approx_yolo_fps": round(yolo_fps, 1),
                "video_playback_fps": round(video_fps, 1),
                "ocr_plates_processed": self.ocr_plates_processed,
                "ocr_attempts": self.ocr_attempts,
                "ocr_short_circuits": self.ocr_short_circuits,
                "ocr_fallbacks_used": self.ocr_fallbacks_used,
                "ocr_avg_latency_ms": round(ocr_avg_ms, 2),
                "reid_calls": self.reid_calls,
                "reid_reused": self.reid_reused,
                "reid_avg_latency_ms": round(reid_avg_ms, 2),
                "elapsed_seconds": round(elapsed_s, 2),
            }

    def get_summary(self) -> Dict[str, Any]:
        """Return structured summary report for benchmarking and external status APIs."""
        stats = self.get_stats()
        skip_pct = (
            (stats["yolo_skipped_frames"] / max(1, stats["total_video_frames"])) * 100.0
        )
        sc_pct = (
            (stats["ocr_short_circuits"] / max(1, stats["ocr_attempts"])) * 100.0
            if stats["ocr_attempts"] > 0
            else 0.0
        )
        reused_total = stats["reid_calls"] + stats["reid_reused"]
        reused_pct = (
            (stats["reid_reused"] / max(1, reused_total)) * 100.0
            if reused_total > 0
            else 0.0
        )
        return {
            "yolo": {
                "total_frames": stats["total_video_frames"],
                "yolo_frames": stats["yolo_inference_frames"],
                "skipped_frames": stats["yolo_skipped_frames"],
                "percent_yolo_run": f"{100.0 - skip_pct:.1f}%",
                "avg_yolo_latency_ms": stats["yolo_avg_latency_ms"],
                "approx_yolo_fps": stats["approx_yolo_fps"],
                "video_fps": stats["video_playback_fps"],
            },
            "ocr": {
                "total_attempts": stats["ocr_attempts"],
                "plates_found": stats["ocr_plates_processed"],
                "short_circuited_count": stats["ocr_short_circuits"],
                "short_circuit_pct": f"{sc_pct:.1f}%",
                "fallbacks_run": stats["ocr_fallbacks_used"],
                "avg_latency_ms": stats["ocr_avg_latency_ms"],
            },
            "reid": {
                "total_calls": stats["reid_calls"],
                "reused_count": stats["reid_reused"],
                "new_inferences": stats["reid_calls"],
                "reuse_ratio": f"{reused_pct:.1f}%",
                "avg_latency_ms": stats["reid_avg_latency_ms"],
            },
            "elapsed_seconds": stats["elapsed_seconds"],
        }

    def check_and_log_summary(self):
        """Emit periodic summary logs at designated intervals without spamming every frame."""
        now = time.time()
        if now - self.last_summary_time < self.summary_interval_s:
            return

        with self._lock:
            if now - self.last_summary_time < self.summary_interval_s:
                return
            self.last_summary_time = now

        stats = self.get_stats()
        skip_pct = (
            (stats["yolo_skipped_frames"] / max(1, stats["total_video_frames"]))
            * 100.0
        )
        sc_pct = (
            (stats["ocr_short_circuits"] / max(1, stats["ocr_attempts"])) * 100.0
            if stats["ocr_attempts"] > 0
            else 0.0
        )
        reused_total = stats["reid_calls"] + stats["reid_reused"]
        reused_pct = (
            (stats["reid_reused"] / max(1, reused_total)) * 100.0
            if reused_total > 0
            else 0.0
        )

        logger.info(
            f"[PERF] YOLO: {stats['yolo_inference_frames']}/{stats['total_video_frames']} frames "
            f"(skipped {stats['yolo_skipped_frames']} = {skip_pct:.1f}%) | "
            f"Latency: {stats['yolo_avg_latency_ms']:.1f}ms (~{stats['approx_yolo_fps']:.1f} FPS) | "
            f"Video: {stats['video_playback_fps']:.1f} FPS"
        )
        if stats["ocr_attempts"] > 0:
            logger.info(
                f"[PERF] OCR: {stats['ocr_attempts']} attempts | "
                f"Short-circuits: {stats['ocr_short_circuits']} ({sc_pct:.1f}%) | "
                f"Fallbacks: {stats['ocr_fallbacks_used']} | "
                f"Avg Latency: {stats['ocr_avg_latency_ms']:.1f}ms"
            )
        if reused_total > 0:
            logger.info(
                f"[PERF] Re-ID: {stats['reid_calls']} calls | "
                f"Reused: {stats['reid_reused']} ({reused_pct:.1f}%) | "
                f"Avg Latency: {stats['reid_avg_latency_ms']:.1f}ms"
            )


_PERF_METRICS_INSTANCE: PipelinePerformanceMetrics | None = None
_METRICS_LOCK = threading.Lock()


def get_performance_metrics() -> PipelinePerformanceMetrics:
    """Return singleton performance metrics instance."""
    global _PERF_METRICS_INSTANCE
    with _METRICS_LOCK:
        if _PERF_METRICS_INSTANCE is None:
            _PERF_METRICS_INSTANCE = PipelinePerformanceMetrics()
        return _PERF_METRICS_INSTANCE

