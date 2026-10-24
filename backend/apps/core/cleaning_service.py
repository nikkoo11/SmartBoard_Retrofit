import os
import time
import cv2
import numpy as np


def _read_image(input_path):
    image = cv2.imread(input_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('Could not read image: %s' % input_path)
    return image


def _resize(image):
    height, width = image.shape[:2]
    if width > 1600:
        scale = 1600.0 / width
        image = cv2.resize(image, (1600, int(height * scale)), interpolation=cv2.INTER_AREA)
    return image


def find_and_warp_document(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    image_area = image.shape[0] * image.shape[1]
    best = None
    had_four = False
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            had_four = True
            area = cv2.contourArea(approx)
            if area >= 0.25 * image_area:
                if best is None or area > cv2.contourArea(best):
                    best = approx
    if best is None:
        if had_four:
            return image, False, 'largest 4-corner contour too small'
        return image, False, 'no 4-corner contour found'
    pts = best.reshape(4, 2).astype(np.float32)
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))
    if maxWidth < 10 or maxHeight < 10:
        return image, False, 'warp size too small'
    dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped, True, 'cropped'


def _to_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _estimate_background(gray):
    k = max(3, gray.shape[1] // 20)
    if k % 2 == 0:
        k += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    bg = cv2.GaussianBlur(bg, (0, 0), sigmaX=k / 2.0)
    return bg


def _remove_lighting(gray):
    bg = _estimate_background(gray)
    bg = bg.astype(np.float32) + 1.0
    normalized = (gray.astype(np.float32) / bg * 255.0)
    return np.clip(normalized, 0, 255).astype(np.uint8)


def _white_point(gray):
    threshold = np.percentile(gray, 85)
    out = gray.astype(np.float32)
    out[out >= threshold] = 255.0
    return np.clip(out, 0, 255).astype(np.uint8)


def _gamma(gray, gamma=0.9):
    inv = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv) * 255 for i in range(256)], dtype=np.uint8)
    return cv2.LUT(gray, table)


def _unsharp_mask(gray):
    blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)
    out = cv2.addWeighted(gray, 1.4, blurred, -0.4, 0)
    return np.clip(out, 0, 255).astype(np.uint8)


def _darken_strokes(gray, strength):
    strength = max(0.0, min(1.0, float(strength)))
    if strength <= 0.0:
        return gray
    inv_gamma = 1.0 + strength * 0.6
    gray = _gamma(gray, 1.0 / inv_gamma)
    kernel = np.ones((2, 2), np.uint8)
    eroded = cv2.erode(gray, kernel, iterations=1)
    gray = cv2.addWeighted(gray, 1.0 - strength, eroded, strength, 0)
    return gray


def _adaptive_threshold(gray):
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )


def clean_gentle(input_path, output_path=None, strength=0.5):
    # Same as clean_board_image but returns image array? For OCR variants, work in memory.
    image = _read_image(input_path)
    image = _resize(image)
    image, _, _ = find_and_warp_document(image)
    gray = _to_grayscale(image)
    gray = _remove_lighting(gray)
    gray = _darken_strokes(gray, strength)
    gray = _white_point(gray)
    gray = _gamma(gray, 0.9)
    gray = _unsharp_mask(gray)
    if output_path:
        cv2.imwrite(output_path, gray)
    return gray


def clean_strong(input_path, output_path=None):
    gray = clean_gentle(input_path)
    # stronger: otsu threshold
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if output_path:
        cv2.imwrite(output_path, th)
    return th


def clean_for_ocr(input_path, output_path=None):
    image = _read_image(input_path)
    image = _resize(image)
    image, _, _ = find_and_warp_document(image)
    gray = _to_grayscale(image)
    gray = _remove_lighting(gray)
    th = _adaptive_threshold(gray)
    if output_path:
        cv2.imwrite(output_path, th)
    return th


def clean_board_image(input_path, output_path=None, strength=0.5):
    image = _read_image(input_path)
    image = _resize(image)
    image, cropped, crop_note = find_and_warp_document(image)
    gray = _to_grayscale(image)
    gray = _remove_lighting(gray)
    gray = _darken_strokes(gray, strength)
    gray = _white_point(gray)
    gray = _gamma(gray, 0.9)
    gray = _unsharp_mask(gray)
    if output_path:
        ok = cv2.imwrite(output_path, gray)
        if not ok:
            raise ValueError('Could not write cleaned image: %s' % output_path)
    return {'cropped': bool(cropped), 'crop_note': crop_note}