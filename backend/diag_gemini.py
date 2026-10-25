"""
SmartBoard Retrofit — Diagnostic script for Gemini OCR.
Safely checks configuration, model availability, and OCR execution.
Never prints or exposes secret API keys.
"""

import os
import sys
import traceback
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

print("=== SmartBoard Gemini OCR Diagnostics ===")

# 1. Check API Key
api_key = os.environ.get('GEMINI_API_KEY', '').strip()
if not api_key:
    print("[ERROR] GEMINI_API_KEY is not set in backend/.env")
    sys.exit(1)
print(f"[OK] GEMINI_API_KEY is configured ({len(api_key)} chars).")

# 2. Check google-genai SDK
try:
    from google import genai
    from google.genai import types
    print("[OK] google-genai SDK is installed.")
except ImportError as exc:
    print(f"[ERROR] google-genai SDK import failed: {exc}")
    sys.exit(1)

# 3. Check ocr_service import
sys.path.insert(0, BASE_DIR)
try:
    from apps.core.ocr_service import run_gemini_ocr
    print("[OK] apps.core.ocr_service.run_gemini_ocr imported successfully.")
except Exception as exc:
    print(f"[ERROR] Failed to import run_gemini_ocr: {exc}")
    traceback.print_exc()
    sys.exit(1)

# 4. Optional test image
test_img = sys.argv[1] if len(sys.argv) > 1 else None
if not test_img:
    img_dir = os.path.join(BASE_DIR, 'media', 'board_images')
    if os.path.exists(img_dir):
        files = [os.path.join(img_dir, f) for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        if files:
            test_img = files[0]

if test_img and os.path.exists(test_img):
    print(f"[INFO] Testing OCR with sample image: {os.path.basename(test_img)}")
    try:
        res = run_gemini_ocr(test_img)
        print(f"[OK] Gemini OCR succeeded using model: {res.get('model')}")
        print(f"[OK] Extracted text length: {len(res.get('text', ''))} characters.")
    except Exception as exc:
        print(f"[ERROR] OCR call failed: {exc}")
        sys.exit(1)
else:
    print("[INFO] No test image found to test live extraction.")

print("=== Diagnostics completed successfully! ===")

