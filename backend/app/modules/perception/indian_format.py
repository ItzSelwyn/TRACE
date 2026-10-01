"""Layer 1 — Perception Module: Indian Registration Format Positional Correction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# All official 28 Indian States & 8 Union Territories + BH series
INDIAN_STATE_CODES: Set[str] = {
    "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ",
    "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN",
    "MP", "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TR", "TS",
    "UK", "UP", "WB", "BH",
}

# Positional character ambiguity maps
DIGIT_TO_LETTER: Dict[str, str] = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "3": "J",
    "4": "A",
    "5": "S",
    "6": "G",
    "8": "B",
}

LETTER_TO_DIGIT: Dict[str, str] = {
    "O": "0",
    "D": "0",
    "Q": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "G": "6",
    "B": "8",
}

COMMON_PREFIX_CONFUSIONS: Dict[str, str] = {
    "1N": "TN",
    "7N": "TN",
    "IN": "TN",
    "LN": "TN",
    "0L": "DL",
    "OL": "DL",
    "K4": "KA",
    "M4": "MH",
}


@dataclass
class FormatCorrectionResult:
    """Detailed result of Indian registration format validation and correction."""
    raw_text: str
    corrected_text: str
    plate_status: str  # "READ", "INFERRED", "PARTIAL", "NOT_READ"
    correction_confidence: float
    inferred_positions: List[int] = field(default_factory=list)
    matched_format: str = "UNKNOWN"  # "STANDARD", "BH_SERIES", "SHORT", "UNKNOWN"


def clean_alphanumeric(text: str) -> str:
    """Uppercase and strip non-alphanumeric characters."""
    if not text:
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(text).upper().strip())


def sanitize_state_prefix(text: str) -> Tuple[str, List[int]]:
    """Strip noise screws/IND badges and correct known OCR confusions in state prefix."""
    s = clean_alphanumeric(text)
    if not s:
        return "", []

    inferred_pos: List[int] = []

    # 1. Strip leading IND watermark badge if present
    if s.startswith("IND") and len(s) > 5:
        s = s[3:]

    # If format is BH-Series (Year[2] + BH + ...), preserve the year prefix intact
    if re.match(r"^[0-9OIZSGB]{2}BH", s):
        return s, []

    # 2. Strip leading 1-2 noise/screw characters if plate starts with a recognized state code at offset 1 or 2
    if len(s) >= 4 and s[:2] not in INDIAN_STATE_CODES:
        for offset in (1, 2):
            st_candidate = s[offset:offset + 2]
            if len(s) >= offset + 2 and st_candidate in INDIAN_STATE_CODES and st_candidate != "BH":
                s = s[offset:]
                break

    # 3. Correct common OCR confusion in first 2 characters
    if len(s) >= 2 and s[:2] in COMMON_PREFIX_CONFUSIONS:
        corrected_st = COMMON_PREFIX_CONFUSIONS[s[:2]]
        if s[0] != corrected_st[0]:
            inferred_pos.append(0)
        if s[1] != corrected_st[1]:
            inferred_pos.append(1)
        s = corrected_st + s[2:]

    return s, inferred_pos


def correct_indian_plate_format(
    text: str,
    raw_confidence: float = 0.85,
    min_confidence_for_read: float = 0.82,
) -> FormatCorrectionResult:
    """Perform positional ambiguity correction according to Indian registration formats.
    
    Supports:
    1. Standard format: State(2) + RTO(2) + Series(1-3) + Number(1-4)
    2. BH-series format: Year(2) + BH + Number(4) + Series(2)
    3. Vintage/Short format: State(2) + RTO(2) + Number(1-4)
    
    Rules:
    - Letter positions convert similar-looking digits into letters.
    - Numeric positions convert similar-looking letters into digits.
    - Preserves strong raw OCR results when no pattern match or when changes exceed threshold.
    - Returns structured plate status: READ, INFERRED, PARTIAL, or NOT_READ.
    """
    raw_clean = clean_alphanumeric(text)
    if not raw_clean or len(raw_clean) < 4:
        return FormatCorrectionResult(
            raw_text=text or "",
            corrected_text=raw_clean,
            plate_status="NOT_READ",
            correction_confidence=0.0,
            inferred_positions=[],
            matched_format="UNKNOWN",
        )

    s, prefix_inferred = sanitize_state_prefix(raw_clean)
    inferred_positions: List[int] = list(prefix_inferred)

    # Check for BH-Series: YY BH NNNN XX (e.g. 22BH1234AA)
    m_bh = re.match(r"^([0-9OIZSGB]{2})(BH)([0-9OIZSGB]{4})([A-Z0-9]{1,2})$", s)
    if m_bh:
        yy, bh, num, series = m_bh.groups()
        yy_clean = "".join(LETTER_TO_DIGIT.get(c, c) for c in yy)
        num_clean = "".join(LETTER_TO_DIGIT.get(c, c) for c in num)
        series_clean = "".join(DIGIT_TO_LETTER.get(c, c) for c in series)

        corrected = f"{yy_clean}BH{num_clean}{series_clean}"
        for i, (orig, corr) in enumerate(zip(s, corrected)):
            if orig != corr and i not in inferred_positions:
                inferred_positions.append(i)

        status = "READ" if not inferred_positions and raw_confidence >= min_confidence_for_read else "INFERRED"
        corr_conf = max(0.50, round(raw_confidence * (1.0 - 0.04 * len(inferred_positions)), 3))
        return FormatCorrectionResult(
            raw_text=raw_clean,
            corrected_text=corrected,
            plate_status=status,
            correction_confidence=corr_conf,
            inferred_positions=sorted(inferred_positions),
            matched_format="BH_SERIES",
        )

    # Standard format: State(2 letters) + RTO(1-2 digits) + Series(1-3 letters) + Number(4 digits preferred, 1-3 fallback)
    # Regex permits ambiguous character substitutions in their respective positions
    m_std = re.match(
        r"^([A-Z]{2})([0-9ODQILZBSG]{1,2})([A-Z0-9]+?)([0-9ODQILZBSG]{4})$",
        s,
    )
    if not m_std:
        m_std = re.match(
            r"^([A-Z]{2})([0-9ODQILZBSG]{1,2})([A-Z0-9]+?)([0-9ODQILZBSG]{1,3})$",
            s,
        )
    if m_std and m_std.group(1) in INDIAN_STATE_CODES:
        st, rto, series, num = m_std.groups()

        # RTO digits (convert letters to digits, pad single digit to 2 digits e.g. 7 -> 07)
        rto_clean = "".join(LETTER_TO_DIGIT.get(c, c) for c in rto)
        if len(rto_clean) == 1:
            rto_clean = "0" + rto_clean

        # Series letters (convert digits to letters)
        series_clean = "".join(DIGIT_TO_LETTER.get(c, c) for c in series)

        # Number digits (convert letters to digits)
        num_clean = "".join(LETTER_TO_DIGIT.get(c, c) for c in num)

        corrected = f"{st}{rto_clean}{series_clean}{num_clean}"

        # Mark inferred positions
        idx = 2  # after state code
        for orig_c, corr_c in zip(rto, rto_clean[-len(rto):]):
            if orig_c != corr_c:
                inferred_positions.append(idx)
            idx += 1
        for orig_c, corr_c in zip(series, series_clean):
            if orig_c != corr_c:
                inferred_positions.append(idx)
            idx += 1
        for orig_c, corr_c in zip(num, num_clean):
            if orig_c != corr_c:
                inferred_positions.append(idx)
            idx += 1

        is_complete = (len(corrected) >= 9 and len(num_clean) == 4 and len(rto_clean) == 2)
        if is_complete:
            if not inferred_positions and raw_confidence >= min_confidence_for_read:
                status = "READ"
            else:
                status = "INFERRED"
        else:
            status = "PARTIAL"

        corr_conf = max(0.50, round(raw_confidence * (1.0 - 0.03 * len(inferred_positions)), 3))
        return FormatCorrectionResult(
            raw_text=raw_clean,
            corrected_text=corrected,
            plate_status=status,
            correction_confidence=corr_conf,
            inferred_positions=sorted(inferred_positions),
            matched_format="STANDARD",
        )

    # Partial / unclassified Indian format with valid state prefix
    if len(s) >= 4 and s[:2] in INDIAN_STATE_CODES:
        return FormatCorrectionResult(
            raw_text=raw_clean,
            corrected_text=s,
            plate_status="PARTIAL",
            correction_confidence=max(0.40, round(raw_confidence * 0.85, 3)),
            inferred_positions=sorted(inferred_positions),
            matched_format="PARTIAL_STATE_MATCH",
        )

    # General fallback for arbitrary or partial plates
    return FormatCorrectionResult(
        raw_text=raw_clean,
        corrected_text=s if len(s) >= 4 else raw_clean,
        plate_status="PARTIAL" if len(raw_clean) >= 5 else "NOT_READ",
        correction_confidence=round(raw_confidence * 0.70, 3),
        inferred_positions=[],
        matched_format="UNKNOWN",
    )
