"""Find normalized PDF text-layer rectangles for extracted invoice values."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
import re


FIELD_HINTS = {
    "totalamountdue": ("total including tax", "amount due", "total due", "invoice total"),
    "taxamount": ("total vat", "vat amount", "tax amount", "total tax"),
    "subtotalamount": ("total excluding tax", "subtotal", "net amount"),
    "invoicenumber": ("invoice number", "invoice no", "invoice #"),
    "invoicedate": ("invoice date", "date of invoice"),
}

_CURRENCY = "$€£¥"
_NUMBER_RE = re.compile(r"^[+-]?\s*[$€£¥]?\s*[\d,]+(?:\.\d+)?\s*%?$")
_NON_TEXT_RE = re.compile(r"[\s,\u00a0$€£¥]")


def normalize_match_text(value):
    """Remove display-only separators while preserving decimal/sign boundaries."""
    text = str(value or "").strip().replace("\u2212", "-").replace("\u2013", "-")
    text = _NON_TEXT_RE.sub("", text).casefold()
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    return text


def value_variants(value):
    """Return likely printed forms, with longer/more-specific forms first."""
    if value is None or isinstance(value, bool):
        return []

    original = str(value).strip()
    if not original:
        return []
    variants = {original}

    if _NUMBER_RE.fullmatch(original):
        numeric = original.strip().rstrip("%").replace(",", "")
        numeric = re.sub(r"^([$€£¥]\s*)", "", numeric)
        try:
            number = Decimal(numeric)
            negative = number < 0
            absolute = abs(number)
            original_scale = max(0, -number.as_tuple().exponent)
            scales = sorted({0, 2, 3, 6, original_scale}, reverse=True)
            for scale in scales:
                if scale > 6:
                    continue
                plain = f"{absolute:.{scale}f}"
                integer, dot, fraction = plain.partition(".")
                grouped = f"{int(integer):,}" + (f".{fraction}" if dot else "")
                sign = "-" if negative else ""
                forms = (plain, grouped)
                for form in forms:
                    variants.add(f"{sign}{form}")
                    variants.add(f"({form})" if negative else form)
                    for currency in _CURRENCY:
                        variants.add(f"{sign}{currency}{form}")
                        if not negative:
                            variants.add(f"{currency}{form}")
                            variants.add(f"{form}{currency}")
                        else:
                            variants.add(f"({currency}{form})")
        except (InvalidOperation, ValueError, OverflowError):
            pass

    try:
        date_value = datetime.strptime(original, "%Y-%m-%d")
    except ValueError:
        date_value = None
    if date_value:
        variants.update({
            date_value.strftime("%d-%b-%Y").upper(),
            date_value.strftime("%d %b %Y").upper(),
            date_value.strftime("%d/%m/%Y"),
            date_value.strftime("%m/%d/%Y"),
            date_value.strftime("%d-%m-%Y"),
            date_value.strftime("%Y/%m/%d"),
            date_value.strftime("%d %B %Y").upper(),
        })

    return sorted(
        (item for item in variants if item),
        key=lambda item: (len(normalize_match_text(item)), len(item)),
        reverse=True,
    )


def match_value_in_text(text, value):
    """Match a complete normalized value, never a numeric substring."""
    normalized_text = normalize_match_text(text)
    if not normalized_text:
        return None
    for variant in value_variants(value):
        needle = normalize_match_text(variant)
        if not needle:
            continue
        start = 0
        while True:
            index = normalized_text.find(needle, start)
            if index < 0:
                break
            end = index + len(needle)
            before_ok = index == 0 or not (
                normalized_text[index - 1].isdigit()
                and needle[0].isdigit()
            )
            after_ok = end == len(normalized_text) or not (
                normalized_text[end].isdigit()
                and needle[-1].isdigit()
            )
            if before_ok and after_ok:
                return variant
            start = index + 1
    return None


def _field_hints(path):
    leaf = re.sub(r"[^a-z0-9]", "", path.rsplit(".", 1)[-1].casefold())
    return FIELD_HINTS.get(leaf, (leaf.replace("_", " "),))


def _page_words(page):
    try:
        words = page.get_text("words")
    except (RuntimeError, ValueError) as error:
        print(f"[Evidence] Text-layer read failed for page {page.number + 1}: {error}")
        return _find_locations_with_ocr_fallback(page)
    if words:
        return words
    return _find_locations_with_ocr_fallback(page)


def _find_locations_with_ocr_fallback(page):
    """Use PyMuPDF's optional Tesseract OCR when the page has no text layer."""
    try:
        text_page = page.get_textpage_ocr(language="eng", dpi=200, full=True)
        words = page.get_text("words", textpage=text_page)
        if words:
            return words
    except (RuntimeError, OSError, ValueError) as error:
        print(f"[Evidence] OCR fallback unavailable for page {page.number + 1}: {error}")
    return []


def _line_candidates(words, variants):
    grouped = {}
    for word in words:
        if len(word) < 8:
            continue
        x0, y0, x1, y1, text, block_no, line_no, word_no = word[:8]
        grouped.setdefault(block_no, {}).setdefault(line_no, []).append(
            (word_no, (x0, y0, x1, y1), str(text), (block_no, line_no))
        )

    normalized_variants = {
        normalize_match_text(variant): variant
        for variant in variants
        if normalize_match_text(variant)
    }
    candidates = []
    lines = []
    for block_lines in grouped.values():
        sequence = []
        for items in block_lines.values():
            items.sort(key=lambda item: item[0])
            lines.append(items)
            sequence.extend(items)
        for start in range(len(sequence)):
            for end in range(start + 1, min(len(sequence), start + 30) + 1):
                selected = sequence[start:end]
                text = " ".join(item[2] for item in selected)
                normalized = normalize_match_text(text)
                variant = normalized_variants.get(normalized)
                if not variant:
                    continue
                line_rects = {}
                for item in selected:
                    line_rects.setdefault(item[3], []).append(item[1])
                rects = [
                    (
                        min(rect[0] for rect in row_rects),
                        min(rect[1] for rect in row_rects),
                        max(rect[2] for rect in row_rects),
                        max(rect[3] for rect in row_rects),
                    )
                    for row_rects in line_rects.values()
                ]
                candidates.append({
                    "text": text,
                    "variant": variant,
                    "rects": rects,
                    "rect": (
                        min(rect[0] for rect in rects),
                        min(rect[1] for rect in rects),
                        max(rect[2] for rect in rects),
                        max(rect[3] for rect in rects),
                    ),
                    "line_y": min(rect[1] for rect in rects),
                    "line_x": min(rect[0] for rect in rects),
                })
    return candidates, lines


def _nearby_label_score(candidate, lines, hints):
    rect = candidate["rect"]
    score = 0
    for line in lines:
        if not line:
            continue
        line_y = min(item[1][1] for item in line)
        left_text = " ".join(item[2] for item in line if item[1][2] <= rect[0] + 2).casefold()
        line_text = " ".join(item[2] for item in line).casefold()
        is_left = abs(line_y - candidate["line_y"]) < 4 and bool(left_text)
        is_above = 0 <= candidate["line_y"] - line_y <= 55
        if not (is_left or is_above):
            continue
        for hint in hints:
            normalized_hint = normalize_match_text(hint)
            source_text = left_text if is_left else line_text
            if normalized_hint and normalized_hint in normalize_match_text(source_text):
                score = max(score, 4 if is_left else 3)
    return score


def _rects_overlap(first, second):
    ax0, ay0, ax1, ay1 = first
    bx0, by0, bx1, by1 = second
    intersection = max(0, min(ax1, bx1) - max(ax0, bx0)) * max(0, min(ay1, by1) - max(ay0, by0))
    smaller_area = min((ax1 - ax0) * (ay1 - ay0), (bx1 - bx0) * (by1 - by0))
    return smaller_area > 0 and intersection / smaller_area > 0.5


def _flatten_fields(data, path=()):
    if isinstance(data, dict):
        canonical_aliases = {
            "header": "invoiceHeader",
            "invoice_header": "invoiceHeader",
            "shipmentDetail": "shipmentDetails",
            "shipment_details": "shipmentDetails",
            "shipments": "shipmentDetails",
            "shipment": "shipmentDetails",
            "charge_line_items": "chargeLineItems",
            "charges": "chargeLineItems",
            "lineItems": "chargeLineItems",
            "items": "chargeLineItems",
        }
        for key, value in data.items():
            if key in {"locations", "_evidenceLocations"}:
                continue
            canonical_key = canonical_aliases.get(key)
            if canonical_key and canonical_key in data:
                continue
            header = data.get("invoiceHeader")
            if not path and isinstance(header, dict) and key in header and header[key] == value:
                continue
            yield from _flatten_fields(value, path + (str(key),))
    elif isinstance(data, list):
        for index, item in enumerate(data):
            yield from _flatten_fields(item, path + (str(index),))
    elif data is not None and str(data).strip() and path:
        yield ".".join(path), data


def compute_pdf_locations(pdf_bytes, extracted_data, page_start=1, page_end=None):
    """Locate extracted scalar values and return document-relative page numbers."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
    except ImportError as error:
        print(f"[Evidence] PyMuPDF unavailable; no locations computed: {error}")
        return {}

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except (RuntimeError, ValueError) as error:
        print(f"[Evidence] Unable to read PDF for evidence locations: {error}")
        return {}

    try:
        fields = list(_flatten_fields(extracted_data))
        candidates = []
        try:
            page_start = max(1, int(page_start or 1))
            last_page = min(len(document), int(page_end or len(document)))
        except (TypeError, ValueError):
            print("[Evidence] Invalid invoice page range; searching the entire PDF")
            page_start = 1
            last_page = len(document)
        for page_number in range(page_start, last_page + 1):
            page = document[page_number - 1]
            words = _page_words(page)
            if not words:
                continue
            for field_path, value in fields:
                variants = value_variants(value)
                if not variants:
                    continue
                matches, lines = _line_candidates(words, variants)
                for match in matches:
                    candidates.append({
                        "field": field_path,
                        "page": page_number,
                        "rect": match["rect"],
                        "rects": match["rects"],
                        "score": _nearby_label_score(match, lines, _field_hints(field_path)),
                        "specificity": len(normalize_match_text(match["variant"])),
                        "page_width": float(page.rect.width),
                        "page_height": float(page.rect.height),
                    })

        candidates.sort(key=lambda item: (item["score"], item["specificity"]), reverse=True)
        locations = {}
        claimed = []
        for candidate in candidates:
            if candidate["field"] in locations:
                continue
            if any(
                candidate["page"] == claimed_page and _rects_overlap(candidate["rect"], claimed_rect)
                for claimed_page, claimed_rect in claimed
            ):
                continue
            locations[candidate["field"]] = {
                "page": candidate["page"],
                "rects": [[
                    max(0.0, min(1.0, rect[0] / candidate["page_width"])),
                    max(0.0, min(1.0, rect[1] / candidate["page_height"])),
                    max(0.0, min(1.0, rect[2] / candidate["page_width"])),
                    max(0.0, min(1.0, rect[3] / candidate["page_height"])),
                ] for rect in candidate["rects"]],
            }
            claimed.append((candidate["page"], candidate["rect"]))

        direct_charges = extracted_data.get("chargeLineItems") or extracted_data.get("charge_line_items") or []
        for index, charge in enumerate(direct_charges if isinstance(direct_charges, list) else []):
            if not isinstance(charge, dict):
                continue
            for key in charge:
                actual = f"chargeLineItems.{index}.{key}"
                alias = f"charges.{index}.{key}"
                if actual in locations:
                    locations[alias] = locations[actual]

        for field_path, _ in fields:
            if field_path not in locations:
                print(f"[Evidence] No text location found for field {field_path!r}")
        return locations
    except (RuntimeError, ValueError, IndexError) as error:
        print(f"[Evidence] Location computation failed: {error}")
        return {}
    finally:
        document.close()
