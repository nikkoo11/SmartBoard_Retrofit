import logging
import mimetypes
import os
import re
import time

import cv2
import numpy as np
import pytesseract
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

logger = logging.getLogger(__name__)


def _sanitize_error(msg: str, key: str = None) -> str:
    """Strip API keys and sensitive tokens from error strings before logging/responding."""
    if not msg:
        return 'Unknown error'
    if key and key in msg:
        msg = msg.replace(key, '[REDACTED]')
    msg = re.sub(r'key=[A-Za-z0-9_-]{20,}', 'key=[REDACTED]', msg)
    msg = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED]', msg)
    return msg


def run_ocr(image, psm=6, min_conf=0, filter='line'):
    tesseract_cmd = os.environ.get('TESSERACT_CMD')
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    start = time.time()
    words_dropped = 0
    lines_kept = 0
    lines_dropped = 0
    try:
        data = pytesseract.image_to_data(image, lang='eng', config='--oem 1 --psm %d' % psm, output_type=pytesseract.Output.DICT)
        # group by line: (block_num, par_num, line_num), ignoring conf -1 / empty text
        lines = {}
        order = []
        for i in range(len(data.get('text', []))):
            txt = (data['text'][i] or '').strip()
            try:
                conf = float(data['conf'][i])
            except (ValueError, TypeError):
                conf = -1.0
            if not txt or conf < 0:
                continue
            key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
            if key not in lines:
                lines[key] = []
                order.append(key)
            lines[key].append((txt, conf))
        kept_lines = []
        kept_confidences = []
        for key in order:
            words = lines[key]
            if filter == 'word':
                # word-level filtering, but preserve line structure
                kept_words = []
                for (t, c) in words:
                    if c < min_conf:
                        words_dropped += 1
                        continue
                    kept_words.append(t)
                    kept_confidences.append(c)
                if not kept_words:
                    lines_dropped += 1
                    continue
                lines_kept += 1
                kept_lines.append(' '.join(kept_words))
            else:
                # line-level filtering
                confs = [c for (t, c) in words]
                mean_conf = (sum(confs) / len(confs)) if confs else 0.0
                alnum_count = sum(1 for (t, c) in words if any(ch.isalnum() for ch in t))
                total_chars = sum(len(t) for (t, c) in words)
                alnum_ratio = (alnum_count / total_chars) if total_chars else 0.0
                drop = False
                if mean_conf < min_conf:
                    drop = True
                elif alnum_ratio < 0.5:
                    drop = True
                elif alnum_count < 3 and mean_conf < 60:
                    drop = True
                if drop:
                    lines_dropped += 1
                    words_dropped += len(words)
                    continue
                lines_kept += 1
                kept_confidences.extend(confs)
                kept_lines.append(' '.join(t for (t, c) in words))
        text = '\n'.join(kept_lines)
    except pytesseract.pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError('Tesseract not found: %s' % exc)
    except Exception as exc:
        raise RuntimeError('OCR failed: %s' % exc)
    # confidence computed from the words that were kept
    avg_conf = (sum(kept_confidences) / len(kept_confidences)) if kept_confidences else None
    ms = int((time.time() - start) * 1000)
    return {
        'text': text,
        'confidence': avg_conf,
        'ms': ms,
        'words_dropped': words_dropped,
        'lines_kept': lines_kept,
        'lines_dropped': lines_dropped,
    }


GEMINI_PROMPT = (
    'Transcribe EXACTLY what is written on the whiteboard, character for character. '
    'Do not add, remove, reorder, simplify, or correct anything. Do not explain, label, '
    'or comment on the content. Do not fill in missing or smudged parts. '
    'Preserve the original order of equations and block-diagram elements, including '
    'the direction of every arrow. '
    'Use ASCII notation: "->" for arrows, "^" for superscripts, "_" for subscripts, '
    '"sqrt()" for square roots. Write subscripts immediately after the variable with '
    'no space (e.g., x[n], x_1, y_k). Write superscripts directly after the base or '
    'exponent (e.g., x^2, e^jw). Keep every variable name, symbol, and number exactly '
    'as written; do not normalize or rewrite them. '
    'If a symbol, number, subscript, superscript, or arrow is unreadable or ambiguous, '
    'write [unclear] and do not guess. Never replace an unclear mark with a plausible '
    'character. Output only the transcribed text, one line per equation or element, '
    'with no extra commentary.'
)


def _gemini_timeout_ms() -> int:
    """Resolve the Gemini request timeout in milliseconds.

    Reads GEMINI_OCR_TIMEOUT_MS from the environment. Falls back to a
    30 s default so a slow or hung model cannot block a request thread
    indefinitely. The value is clamped to a sane range to guard against
    misconfiguration.
    """
    raw = os.environ.get('GEMINI_OCR_TIMEOUT_MS', '30000')
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 30000
    if value <= 0:
        value = 30000
    return min(value, 600000)


def _is_timeout(exc: Exception) -> bool:
    """Return True when the exception indicates an HTTP request timeout.

    The google-genai SDK surfaces timeouts through httpx (or httpx2)
    and occasionally through its own APIError wrapper. We detect them by
    class name so we do not depend on private SDK attributes.
    """
    name = type(exc).__name__
    if name in ('TimeoutException', 'ConnectTimeout', 'ReadTimeout',
                'WriteTimeout', 'PoolTimeout'):
        return True
    try:
        import httpx
        if isinstance(exc, httpx.TimeoutException):
            return True
    except Exception:
        pass
    try:
        import httpx2
        if isinstance(exc, httpx2.TimeoutException):
            return True
    except Exception:
        pass
    return False


def run_gemini_ocr(image_path, model='gemini-2.0-flash'):
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY is not configured in backend environment.')
    if not image_path or not os.path.exists(image_path):
        raise FileNotFoundError('Image file not found: %s' % image_path)
    try:
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
    except OSError as exc:
        raise RuntimeError('Could not read image: %s' % exc)
    if not image_bytes:
        raise ValueError('Image file is empty.')

    mime_type = mimetypes.guess_type(image_path)[0] or 'image/png'
    if not mime_type.startswith('image/'):
        raise ValueError('Unsupported image type: %s' % mime_type)

    try:
        from google import genai
        from google.genai import types, errors
    except Exception as exc:
        raise ImportError('google-genai SDK is not available: %s' % exc)

    # Resolve candidate models in priority order
    env_model = os.environ.get('GEMINI_OCR_MODEL')
    candidate_models = []
    if env_model:
        candidate_models.append(env_model)
    if model and model not in candidate_models:
        candidate_models.append(model)
    for fallback in ['gemini-3.1-flash-lite', 'gemini-3.5-flash']:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=_gemini_timeout_ms())
    )

    last_error = None
    response = None
    chosen_model = None

    for cand_model in candidate_models:
        try:
            logger.info("Attempting Gemini OCR with model: %s", cand_model)
            response = client.models.generate_content(
                model=cand_model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    GEMINI_PROMPT,
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    automatic_continuation=False
                ),
            )
            chosen_model = cand_model
            break
        except (errors.ClientError, errors.ServerError) as exc:
            sanitized = _sanitize_error(str(exc), api_key)
            last_error = sanitized
            logger.warning("Gemini model '%s' failed: %s", cand_model, sanitized)
            continue
        except Exception as exc:
            sanitized = _sanitize_error(str(exc), api_key)
            last_error = sanitized
            # Surface timeouts distinctly so callers can distinguish a
            # hung request from a model/availability failure.
            if _is_timeout(exc):
                last_error = 'Gemini request timed out after %d ms.' % _gemini_timeout_ms()
            logger.warning("Gemini model '%s' failed with error: %s", cand_model, sanitized)
            continue

    if response is None:
        raise RuntimeError('Gemini OCR request failed: %s' % (last_error or 'No response'))

    text = getattr(response, 'text', None)
    if not text:
        try:
            text = response.candidates[0].content.parts[0].text
        except Exception:
            text = ''
    text = (text or '').strip()
    if not text:
        raise RuntimeError('Gemini returned an empty response.')

    return {'text': text, 'engine': 'gemini', 'model': chosen_model or model}