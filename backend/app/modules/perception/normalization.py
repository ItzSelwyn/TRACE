"""Layer 1 — Perception Module: Safe Indian license plate text normalization."""

from __future__ import annotations

import re


INDIAN_STATE_CODES = {
    "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ",
    "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN",
    "MP", "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TR", "TS",
    "UK", "UP", "WB", "BH",
}

DIGIT_TO_LETTER = {"0": "O", "1": "I", "2": "Z", "3": "J", "4": "A", "5": "S", "6": "G", "8": "B"}
LETTER_TO_DIGIT = {"O": "0", "D": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "B": "8", "S": "5", "G": "0"}


def normalize_plate_text(raw_text: str | None) -> str:
    """Normalize Indian license plate text with intelligent artifact stripping and formatting.
    
    Rules:
    - Convert letters to uppercase and strip non-alphanumeric characters.
    - Strip leading noise/artifacts/screws before recognized Indian state codes (e.g., 'ETN63...' -> 'TN63...').
    - Strip leading 'IND' watermark if present.
    - Format standard Indian plates: State(2 letters) + RTO(2 digits) + Series(1-3 letters) + Number(1-4 digits).
    - Correct positional character confusions (e.g., 8 -> B in series, O/G -> 0 in RTO).
    
    Example:
    'TN 37 CY 1234' -> 'TN37CY1234'
    'tn-09-ab-4567' -> 'TN09AB4567'
    'ETN638V7954'   -> 'TN63BV7954'
    'TNO7BT5778'    -> 'TN07BT5778'
    'TN 7 AP 0659'  -> 'TN07AP0659'
    """
    if not raw_text:
        return ""

    # Convert to uppercase and strip non-alphanumeric characters
    text = str(raw_text).upper().strip()
    text = re.sub(r"[^A-Z0-9]", "", text)
    if not text:
        return ""

    # 1. Strip leading 'IND' watermark badge if present
    if text.startswith("IND") and len(text) > 5:
        text = text[3:]

    # 2. Strip leading 1-2 noise/screw characters if plate starts with a recognized state code at offset 1 or 2
    if text[:2] not in INDIAN_STATE_CODES:
        for offset in (1, 2):
            if len(text) >= offset + 2 and text[offset:offset + 2] in INDIAN_STATE_CODES:
                text = text[offset:]
                break

    # Correct common OCR state code character confusions (e.g. 'IN', '1N', '7N' -> 'TN')
    state_confusions = {"IN": "TN", "1N": "TN", "7N": "TN", "0L": "DL", "OL": "DL", "K4": "KA"}
    if text[:2] in state_confusions:
        text = state_confusions[text[:2]] + text[2:]

    # 3. Structure Indian standard format: State(2) + RTO(1-2) + Series(1-3) + Number(4)
    m_std = re.match(r"^([A-Z]{2})([0-9ODQILZBSG]{1,2})([A-Z0-9]+?)([0-9ODQILZBSG]{4})$", text)
    if m_std and m_std.group(1) in INDIAN_STATE_CODES:
        st, rto, series, num = m_std.groups()
        # RTO must be 2 digits (e.g. 07, 63, 02)
        rto_clean = "".join(LETTER_TO_DIGIT.get(c, c) for c in rto)
        if len(rto_clean) == 1:
            rto_clean = "0" + rto_clean
        # Series must be letters (e.g. BV, AU, AP, AJ)
        series_clean = "".join(DIGIT_TO_LETTER.get(c, c) for c in series)
        # Number must be 4 digits (e.g. 7954, 0659, 4455)
        num_clean = "".join(LETTER_TO_DIGIT.get(c, c) for c in num)
        return f"{st}{rto_clean}{series_clean}{num_clean}"

    # Handle shorter numbers or vintage format (State + RTO + Series + 1-3 digits)
    m_short = re.match(r"^([A-Z]{2})([0-9A-Z]{1,2})([A-Z0-9]+?)([0-9A-Z]{1,3})$", text)
    if m_short and m_short.group(1) in INDIAN_STATE_CODES:
        st, rto, series, num = m_short.groups()
        rto_clean = "".join(LETTER_TO_DIGIT.get(c, c) for c in rto)
        if len(rto_clean) == 1:
            rto_clean = "0" + rto_clean
        series_clean = "".join(DIGIT_TO_LETTER.get(c, c) for c in series)
        num_clean = "".join(LETTER_TO_DIGIT.get(c, c) for c in num)
        return f"{st}{rto_clean}{series_clean}{num_clean}"

    return text


def compute_character_accuracy(predicted: str, ground_truth: str) -> float:
    """Compute character-level accuracy using Levenshtein edit distance ratio.
    
    Returns a float between 0.0 (completely dissimilar) and 1.0 (exact match).
    """
    p = normalize_plate_text(predicted)
    g = normalize_plate_text(ground_truth)

    if not p and not g:
        return 1.0
    if not p or not g:
        return 0.0
    if p == g:
        return 1.0

    # Levenshtein distance matrix
    m, n = len(p), len(g)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if p[i - 1] == g[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    dist = dp[m][n]
    max_len = max(m, n)
    return max(0.0, 1.0 - (dist / max_len))

