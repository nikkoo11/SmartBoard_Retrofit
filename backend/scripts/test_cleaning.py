import os
import sys
import time
import glob
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from apps.core.cleaning_service import clean_board_image


def main():
    if len(sys.argv) < 2:
        print('Usage: python test_cleaning.py <input_folder> [output_folder]')
        sys.exit(1)
    input_folder = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_folder, 'cleaned_out')
    os.makedirs(output_folder, exist_ok=True)
    exts = ('*.jpg', '*.jpeg', '*.png', '*.webp')
    files = []
    for e in exts:
        files.extend(glob.glob(os.path.join(input_folder, e)))
    strengths = (0.0, 0.5, 1.0)
    for f in sorted(files):
        name = os.path.splitext(os.path.basename(f))[0]
        orig = cv2.imread(f)
        for strength in strengths:
            out = os.path.join(output_folder, '%s_strength_%.1f_cleaned.png' % (name, strength))
            start = time.time()
            result = clean_board_image(f, out, strength=strength)
            elapsed = (time.time() - start) * 1000
            cleaned = cv2.imread(out, cv2.IMREAD_GRAYSCALE)
            if cleaned is not None:
                cleaned_bgr = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)
                h = max(orig.shape[0], cleaned_bgr.shape[0])
                if orig.shape[0] != h:
                    orig_r = cv2.resize(orig, (int(orig.shape[1] * h / orig.shape[0]), h))
                else:
                    orig_r = orig
                if cleaned_bgr.shape[0] != h:
                    cleaned_bgr = cv2.resize(cleaned_bgr, (int(cleaned_bgr.shape[1] * h / cleaned_bgr.shape[0]), h))
                compare = np.hstack([orig_r, cleaned_bgr])
                cv2.imwrite(os.path.join(output_folder, '%s_strength_%.1f_compare.png' % (name, strength)), compare)
            print('%s strength=%.1f: %.0f ms cropped=%s note=%s' % (os.path.basename(f), strength, elapsed, result.get('cropped'), result.get('crop_note')))


if __name__ == '__main__':
    main()
