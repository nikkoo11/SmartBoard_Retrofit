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
    cleaned = '\n'.join(line for line in text.splitlines() if line.strip() != '')
    elapsed_ms = int((time.time() - start) * 1000)
    return {'text': cleaned, 'confidence': avg_conf, 'ms': elapsed_ms, 'words_dropped': words_dropped, 'lines_kept': lines_kept, 'lines_dropped': lines_dropped, 'filter': filter}