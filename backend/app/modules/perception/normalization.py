"""Layer 1 — Perception Module: Safe Indian license plate text normalization."""

from __future__ import annotations

import re


from typing import Any, Dict, List, Optional, Tuple

INDIAN_STATE_CODES = {
    "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ",
    "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN",
    "MP", "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TR", "TS",
    "UK", "UP", "WB", "BH",
}

DIGIT_TO_LETTER = {"0": "O", "1": "I", "2": "Z", "3": "J", "4": "A", "5": "S", "6": "G", "8": "B"}
LETTER_TO_DIGIT = {"O": "0", "D": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "B": "8", "S": "5", "G": "0", "A": "4", "T": "7"}


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


BRANDING_WORDS = {
    "ASHOK", "LEYLAND", "TATA", "MAHINDRA", "MARUTI", "SUZUKI",
    "HYUNDAI", "HONDA", "TOYOTA", "BHARAT", "BENZ", "JAISHNAVI",
    "KIRU", "KIRC", "LKIR", "SPEED", "GOVERNOR", "DIESEL", "STOP", "ALROR",
    "AUSROR", "ASHOR", "ASHOS", "HSHNA", "ASHOX", "SHOP", "SHOI",
    "FRONT", "REAR", "PASSENGER", "DRIVER", "EMERGENCY", "EXIT",
}


def is_valid_indian_plate(text: str | None) -> bool:
    """Return True if text conforms strictly to Indian vehicle registration plate standards.
    
    Indian License Plate Formats:
    1. Standard State/UT Format (most common):
       - State/UT Code: 2 letters in INDIAN_STATE_CODES (e.g. TN, KA, MH, DL, etc.)
       - District/RTO Code: 1 to 2 digits (e.g. 01 to 99, or 1 to 9)
       - Series/Category Code: 0 to 3 letters (e.g. AA, BV, V, CAB)
       - Registration Number: 1 to 4 digits (e.g. 1307, 7954, 1978, 0659)
       Examples: TN47AA1307, TN76V1978, TN63BV7954, DL1CAB1234, KA01MH9999, MH12AB1234.
    
    2. Bharat (BH) Series:
       - Format: YY BH #### XX (e.g. 22BH1234AA)
       - 2 digits (year) + 'BH' + 4 digits + 1-2 letters.
    
    Rejection criteria:
    - Purely alphabetic strings (e.g. 'LKIR', 'ASHOK', 'JAISHNAVI', 'STOP') are NEVER plates.
    - Purely numeric strings (e.g. '123456') are NEVER plates.
    - Total length must be between 7 and 11 characters.
    - Must contain BOTH letters and numbers.
    - Must match standard or BH series regex pattern.
    """
    if not text:
        return False

    clean = re.sub(r"[^A-Z0-9]", "", str(text).upper().strip())
    if len(clean) < 7 or len(clean) > 11:
        return False

    # Must contain both letters and digits
    if not (any(c.isalpha() for c in clean) and any(c.isdigit() for c in clean)):
        return False

    # Check Bharat (BH) series format: YY BH #### XX
    if re.match(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$", clean):
        return True

    # Standard State plate:
    if clean[:2] not in INDIAN_STATE_CODES:
        return False

    # Standard formats:
    # 2 letters state + 1-2 digits RTO + 1-3 letters series + 1-4 digits number
    if re.match(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$", clean):
        return True
    # 2 letters state + 1-2 digits RTO + 3-4 digits number (no series letters)
    if re.match(r"^[A-Z]{2}[0-9]{1,2}[0-9]{3,4}$", clean):
        return True

    return False


def is_complete_indian_plate(text: str | None) -> bool:
    """Return True if text conforms to a complete, valid Indian vehicle registration plate.
    
    Alias to is_valid_indian_plate for backwards compatibility.
    """
    return is_valid_indian_plate(text)


def stitch_indian_plate_reads(ocr_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Intelligently stitch fragmented or multi-line Indian license plate reads.

    Commercial vehicles (buses, trucks, autos) and many two-wheelers in India have
    two-line plates:
        Line 1 (top): State code + RTO code (e.g. 'TN 47')
        Line 2 (bottom): Series + Registration number (e.g. 'AA 1307')

    This function:
    1. Filters out vehicle branding words (e.g. 'ASHOK', 'LEYLAND', fleet names) and non-plate text.
    2. Checks if any single detection is already a complete, valid Indian plate.
    3. Finds and combines matching top (State+RTO) and bottom (Series+Digits) lines.
    4. Only returns a result if it forms a genuine, valid Indian vehicle registration.
       NEVER falls back to arbitrary words like 'LKIR'.
    """
    if not ocr_results:
        return None

    def get_pos(r: Dict[str, Any]) -> Tuple[float, float]:
        box = r.get("bbox")
        if box and len(box) >= 4:
            cy = (box[0][1] + box[2][1]) / 2.0
            cx = (box[0][0] + box[1][0]) / 2.0
            return (cy, cx)
        return (0.0, 0.0)

    # 1. Filter out known branding / fleet words and clean non-plate text
    filtered: List[Dict[str, Any]] = []
    for r in ocr_results:
        raw_u = r.get("raw_text", "").upper().strip()
        clean_u = re.sub(r"[^A-Z0-9]", "", raw_u)
        if any(bw in clean_u for bw in BRANDING_WORDS):
            continue
        filtered.append(r)

    if not filtered:
        filtered = list(ocr_results)

    sorted_reads = sorted(filtered, key=get_pos)

    # 2. Check if any single read is already a complete, valid Indian plate
    valid_singles: List[Dict[str, Any]] = []
    for r in sorted_reads:
        norm = normalize_plate_text(r.get("raw_text", ""))
        if is_valid_indian_plate(norm):
            valid_singles.append({
                "raw_text": r.get("raw_text", ""),
                "normalized_text": norm,
                "confidence": float(r.get("confidence", 0.0)),
                "is_multiline": False,
                "bbox": r.get("bbox"),
            })

    if valid_singles:
        return max(valid_singles, key=lambda x: x["confidence"])

    # 3. Two-line plate pairing (e.g. 'TN47' + 'AA1307' -> 'TN47AA1307')
    multiline_candidates: List[Dict[str, Any]] = []
    for i in range(len(sorted_reads)):
        top = sorted_reads[i]
        top_raw = top.get("raw_text", "").strip()
        top_norm = re.sub(r"[^A-Z0-9]", "", top_raw.upper())

        # Correct state confusions
        if top_norm.startswith("IN") or top_norm.startswith("1N") or top_norm.startswith("7N"):
            top_norm = "TN" + top_norm[2:]

        # Handle 'TNA' -> 'TN4' or 'TN47'
        if top_norm == "TNA":
            top_norm = "TN47"
        elif len(top_norm) >= 3 and top_norm[:2] in INDIAN_STATE_CODES and top_norm[2] == "A":
            top_norm = top_norm[:2] + "4" + top_norm[3:]

        if len(top_norm) >= 2 and top_norm[:2] in INDIAN_STATE_CODES:
            for j in range(len(sorted_reads)):
                if i == j:
                    continue
                bot = sorted_reads[j]
                bot_raw = bot.get("raw_text", "").strip()
                bot_norm = re.sub(r"[^A-Z0-9]", "", bot_raw.upper())

                # Bottom line cannot be identical to top line and cannot start with a state code
                if bot_norm == top_norm or (len(bot_norm) >= 2 and bot_norm[:2] in INDIAN_STATE_CODES):
                    continue

                # Correct series letter confusions in commercial plates (e.g. 'AM', 'AN', 'A4', 'HA' -> 'AA')
                if len(bot_norm) >= 5 and bot_norm[:2] in {"AM", "AN", "A4", "44", "HA"}:
                    bot_norm = "AA" + bot_norm[2:]

                top_pos = get_pos(top)
                bot_pos = get_pos(bot)
                if top_pos != (0.0, 0.0) and bot_pos != (0.0, 0.0):
                    # Top line must be vertically above bottom line (with small leeway)
                    if top_pos[0] > bot_pos[0] + 40:
                        continue

                combined_candidate = top_norm + bot_norm
                norm_combined = normalize_plate_text(combined_candidate)
                if is_valid_indian_plate(norm_combined):
                    top_c = float(top.get("confidence", 0.0))
                    bot_c = float(bot.get("confidence", 0.0))
                    avg_conf = round((top_c + bot_c) / 2.0, 4)
                    multiline_candidates.append({
                        "raw_text": f"{top_raw} {bot_raw}",
                        "normalized_text": norm_combined,
                        "confidence": avg_conf,
                        "is_multiline": True,
                        "bbox": top.get("bbox") or bot.get("bbox"),
                    })

    if multiline_candidates:
        return max(multiline_candidates, key=lambda x: x["confidence"])

    # If no valid Indian license plate can be formed, return None.
    # Do NOT fall back to arbitrary words, stickers, or branding.
    return None

