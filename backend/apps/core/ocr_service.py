import os
import time

import cv2
import numpy as np
import pytesseract
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))


def run_ocr(image, psm=6):
    tesseract_cmd = os.environ.get('TESSERACT_CMD')
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    start = time.time()
    try:
        text = pytesseract.image_to_string(image, lang='eng', config='--oem 1 --psm %d' % psm)
    except pytesseract.pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError('Tesseract not found: %s' % exc)
    except Exception as exc:
        raise RuntimeError('OCR failed: %s' % exc)
    # confidence
    try:
        data = pytesseract.image_to_data(image, lang='eng', config='--oem 1 --psm %d' % psm, output_type=pytesseract.Output.DICT)
    except Exception:
        data = None
    confidences = []
    if data is not None:
        for conf in data.get('conf', []):
            try:
                c = float(conf)
            except (ValueError, TypeError):
                continue
            if c >= 0:
                confidences.append(c)
    avg_conf = (sum(confidences) / len(confidences)) if confidences else None
    cleaned = '\n'.join(line for line in text.splitlines() if line.strip() != '')
    # collapse extra blank lines already removed; keep single spaces? keep as is
    elapsed_ms = int((time.time() - start) * 1000)
    return {'text': cleaned, 'confidence': avg_conf, 'ms': elapsed_ms}