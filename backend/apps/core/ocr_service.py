import os
import time

import cv2
import numpy as np
import pytesseract
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))


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


GEMINI_PROMPT = 'Copy ONLY the text written on the whiteboard, exactly as written. Do not add labels, notes, explanations or corrections. Write math in simple one-line form using ASCII notation where practical: use "->" for arrows, "^" for exponents, "_" for subscripts, and "sqrt()" for square roots. Keep variable names and symbols as they appear. If something is unreadable, write [unclear].'


def run_gemini_ocr(image_path, model='gemini-3.8-flash'):
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY is not set.')
    if not image_path or not os.path.exists(image_path):
        raise RuntimeError('Image file not found: %s' % image_path)
    try:
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
    except OSError as exc:
        raise RuntimeError('Could not read image: %s' % exc)
    if not image_bytes:
        raise RuntimeError('Image file is empty.')
    import mimetypes
    mime_type = mimetypes.guess_type(image_path)[0] or 'image/png'
    if not mime_type.startswith('image/'):
        raise RuntimeError('Unsupported image type: %s' % mime_type)
    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        raise RuntimeError('google-genai SDK is not available: %s' % exc)
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                GEMINI_PROMPT,
            ],
            config=types.GenerateContentConfig(automatic_continuation=False),
        )
    except Exception as exc:
        raise RuntimeError('Gemini OCR failed: %s' % exc)
    text = getattr(response, 'text', None)
    if not text:
        try:
            text = response.candidates[0].content.parts[0].text
        except Exception:
            text = ''
    text = (text or '').strip()
    if not text:
        raise RuntimeError('Gemini returned an empty response.')
    return {'text': text, 'engine': 'gemini', 'model': model}