import cv2
import numpy as np


def _read_image(input_path):
    # Read the image from disk; OpenCV returns None if it cannot be decoded.
    image = cv2.imread(input_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('Could not read image: %s' % input_path)
    return image


def _resize(image):
    # Keep the width at most 1600 px to limit processing cost.
    height, width = image.shape[:2]
    if width > 1600:
        scale = 1600.0 / width
        image = cv2.resize(image, (1600, int(height * scale)), interpolation=cv2.INTER_AREA)
    return image


def _to_grayscale(image):
    # Convert to grayscale for further processing.
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _remove_lighting(gray):
    # Estimate the background with a large morphological close, then divide.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (31, 31))
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    background = np.where(background == 0, 1, background).astype(np.uint8)
    normalized = cv2.divide(gray, background, scale=255)
    return normalized


def _improve_contrast(gray):
    # CLAHE for local contrast enhancement.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _denoise(gray):
    # Light denoising that keeps thin marker strokes.
    return cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)


def _threshold(gray):
    # Adaptive threshold: dark writing on white background.
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )


def clean_board_image(input_path, output_path):
    image = _read_image(input_path)
    image = _resize(image)
    gray = _to_grayscale(image)
    gray = _remove_lighting(gray)
    gray = _improve_contrast(gray)
    gray = _denoise(gray)
    result = _threshold(gray)
    ok = cv2.imwrite(output_path, result)
    if not ok:
        raise ValueError('Could not write cleaned image: %s' % output_path)
    return output_path