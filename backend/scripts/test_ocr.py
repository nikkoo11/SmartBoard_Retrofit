import os
import sys
import csv
import time
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from apps.core.ocr_service import run_ocr
from apps.core.cleaning_service import clean_gentle, clean_strong, clean_for_ocr


def levenshtein(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def normalize(s):
    return ' '.join(s.lower().split())


def main():
    if len(sys.argv) < 2:
        print('Usage: test_ocr.py <image> [groundtruth.txt] [output_dir]')
        sys.exit(1)
    image_path = sys.argv[1]
    gt_path = sys.argv[2] if len(sys.argv) > 2 and os.path.isfile(sys.argv[2]) else None
    output_dir = sys.argv[3] if len(sys.argv) > 3 else 'ocr_out'
    os.makedirs(output_dir, exist_ok=True)

    gt = None
    if gt_path:
        with open(gt_path, 'r', encoding='utf-8') as f:
            gt = normalize(f.read())

    variants = {
        'original': lambda: cv2.imread(image_path, cv2.IMREAD_GRAYSCALE),
        'gentle': lambda: clean_gentle(image_path),
        'strong': lambda: clean_strong(image_path),
        'threshold': lambda: clean_for_ocr(image_path),
    }

    rows = []
    for vname, fn in variants.items():
        img = fn()
        for psm in (6, 11):
            res = run_ocr(img, psm=psm)
            text = res['text']
            cer = None
            if gt is not None:
                cer = levenshtein(normalize(text), gt) / max(len(gt), 1)
            out_file = os.path.join(output_dir, '%s_psm%d.txt' % (vname, psm))
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(text)
            rows.append({
                'variant': vname,
                'psm': psm,
                'ms': res['ms'],
                'confidence': res['confidence'],
                'chars': len(text),
                'cer': cer,
            })
            print('%-10s psm=%d  ms=%d  conf=%s  chars=%d  cer=%s' % (
                vname, psm, res['ms'],
                (round(res['confidence'], 1) if res['confidence'] is not None else None),
                len(text),
                (round(cer, 4) if cer is not None else None),
            ))

    with open(os.path.join(output_dir, 'results.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['variant', 'psm', 'ms', 'confidence', 'chars', 'cer'])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
'@