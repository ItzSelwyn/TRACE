"""Unit tests for sequence-aligned OCR consensus voting and Indian format correction."""

import pytest

from app.modules.perception.consensus_fusion import (
    TrackTemporalConsensus,
    needleman_wunsch_align,
)
from app.modules.perception.indian_format import (
    correct_indian_plate_format,
    sanitize_state_prefix,
)


def test_needleman_wunsch_alignment():
    seq_a = "TN76V1978"
    seq_b = "TN761978"  # missing 'V'

    al_a, al_b = needleman_wunsch_align(seq_a, seq_b)
    assert len(al_a) == len(al_b)
    assert "-" in al_b


def test_consensus_voting_resolves_ambiguous_characters():
    # Example from prompt:
    # TN76V1978 0.78
    # TN76V1S78 0.69
    # TN76V197B 0.64
    # Expected consensus: TN76V1978
    consensus = TrackTemporalConsensus(track_id="TRK-001", camera_id="c020")
    consensus.add_candidate(
        frame_id=10,
        raw_text="TN76V1978",
        normalized_text="TN76V1978",
        confidence=0.78,
        crop_quality_score=0.80,
    )
    consensus.add_candidate(
        frame_id=18,
        raw_text="TN76V1S78",
        normalized_text="TN76V1S78",
        confidence=0.69,
        crop_quality_score=0.70,
    )
    consensus.add_candidate(
        frame_id=25,
        raw_text="TN76V197B",
        normalized_text="TN76V197B",
        confidence=0.64,
        crop_quality_score=0.65,
    )

    res = consensus.compute_consensus()
    assert res["corrected_plate_text"] == "TN76V1978"
    assert res["plate_status"] in ["READ", "INFERRED"]
    assert res["is_synthetic"] is False


def test_indian_format_positional_correction():
    # 1. Screw noise prefix + digit in letter series: ETN638V7954 -> TN63BV7954
    res1 = correct_indian_plate_format("ETN638V7954", raw_confidence=0.85)
    assert res1.corrected_text == "TN63BV7954"
    assert res1.plate_status in ["READ", "INFERRED"]

    # 2. Letter 'O' in numeric RTO: TNO7BT5778 -> TN07BT5778
    res2 = correct_indian_plate_format("TNO7BT5778", raw_confidence=0.88)
    assert res2.corrected_text == "TN07BT5778"
    assert res2.plate_status in ["READ", "INFERRED"]

    # 3. Single-digit RTO padded: TN 7 AP 0659 -> TN07AP0659
    res3 = correct_indian_plate_format("TN 7 AP 0659", raw_confidence=0.86)
    assert res3.corrected_text == "TN07AP0659"

    # 4. Common OCR prefix confusion: 1N38AB4821 -> TN38AB4821
    res4 = correct_indian_plate_format("1N38AB4821", raw_confidence=0.85)
    assert res4.corrected_text == "TN38AB4821"

    # 5. BH-Series format: 22BH1234AA
    res5 = correct_indian_plate_format("22BH1234AA", raw_confidence=0.90)
    assert res5.corrected_text == "22BH1234AA"
    assert res5.matched_format == "BH_SERIES"
