import os
import sys
import argparse
import time

# Disable oneDNN to avoid PIR/oneDNN conversion issues in this environment
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
try:
    import paddle

    paddle.set_flags({"FLAGS_use_mkldnn": False})
except Exception:
    pass

from paddleocr import PaddleOCR


def main():
    parser = argparse.ArgumentParser(description="PaddleOCR 3.7.0 test script")
    parser.add_argument("image_path", help="Path to image file")
    args = parser.parse_args()

    image_path = args.image_path
    if not os.path.exists(image_path):
        print(f"Error: file does not exist: {image_path}", file=sys.stderr)
        sys.exit(1)

    # Load PaddleOCR once with English; disable doc orientation/unwarping/textline orientation if supported
    ocr = PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )

    # Time only recognition step
    start = time.perf_counter()
    results = ocr.predict(image_path)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    # Extract texts and scores from result objects (PaddleOCR 3.7.0/PaddleX style)
    texts = []
    scores = []
    for res in results:
        # Try common attribute/access patterns
        if hasattr(res, "get") and "rec_texts" in res:
            rec_texts = res["rec_texts"]
            rec_scores = res.get("rec_scores", [])
        elif hasattr(res, "rec_texts"):
            rec_texts = getattr(res, "rec_texts")
            rec_scores = getattr(res, "rec_scores", [])
        elif isinstance(res, dict):
            rec_texts = res.get("rec_texts", [])
            rec_scores = res.get("rec_scores", [])
        else:
            rec_texts = []
            rec_scores = []
        if isinstance(rec_texts, (list, tuple)):
            texts.extend([str(t) for t in rec_texts])
        if isinstance(rec_scores, (list, tuple)):
            scores.extend([float(s) for s in rec_scores])

    # Print
    for t in texts:
        print(t)
    num_lines = len(texts)
    if scores:
        avg_conf = (sum(scores) / len(scores)) * 100.0
    else:
        avg_conf = 0.0
    print(f"lines: {num_lines}")
    print(f"avg_conf: {avg_conf:.2f}")
    print(f"ms: {elapsed_ms:.2f}")

    # Save output
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.basename(image_path)
    name_noext = os.path.splitext(base)[0]
    out_path = os.path.join(out_dir, f"{name_noext}_paddle.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        for t in texts:
            f.write(t + "\n")
        f.write(f"lines: {num_lines}\n")
        f.write(f"avg_conf: {avg_conf:.2f}\n")
        f.write(f"ms: {elapsed_ms:.2f}\n")


if __name__ == "__main__":
    main()
