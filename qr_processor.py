"""QR Code processing logic: PDF extraction, decoding, and generation.

Adapted from main.py for headless/web use (no tkinter dependency).
"""

import io
import re

import cv2
import fitz  # PyMuPDF
import numpy as np
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode


def extract_images_from_pdf(pdf_bytes):
    """Render PDF pages to PIL images at 2x scale for reliable QR detection."""
    images = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            images.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
    finally:
        doc.close()
    return images


def _create_image_variants(gray):
    variants = {'original': gray}
    variants['adaptive_thresh'] = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    _, variants['otsu'] = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    variants['clahe'] = clahe.apply(gray)
    variants['inverted'] = cv2.bitwise_not(gray)
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    variants['sharpened'] = cv2.filter2D(gray, -1, kernel)
    return variants


def find_utf8_qr_code(image):
    """Return ST00012 UTF-8 QR text from a PIL image, or None."""
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    variants = _create_image_variants(gray)

    qr_detector = cv2.QRCodeDetector()
    for variant_img in variants.values():
        retval, decoded_info, _points, _ = qr_detector.detectAndDecodeMulti(variant_img)
        if retval and decoded_info:
            for data in decoded_info:
                if data and 'ST00012' in data[:20]:
                    return data

    for variant_img in variants.values():
        variant_bgr = (
            cv2.cvtColor(variant_img, cv2.COLOR_GRAY2BGR)
            if len(variant_img.shape) == 2
            else variant_img
        )
        for obj in pyzbar_decode(variant_bgr):
            if obj.type != 'QRCODE':
                continue
            try:
                data = obj.data.decode('utf-8')
            except UnicodeDecodeError:
                continue
            if 'ST00012' in data[:20]:
                return data

    return None


def find_qr_in_pdf(pdf_bytes):
    """Scan all pages, return the first ST00012 UTF-8 QR text found, or None."""
    for img in extract_images_from_pdf(pdf_bytes):
        data = find_utf8_qr_code(img)
        if data:
            return data
    return None


def extract_purpose(text):
    match = re.search(r'Purpose=([^|]*)', text)
    return match.group(1) if match else None


def update_purpose(text, new_purpose):
    return re.sub(r'Purpose=[^|]*', f'Purpose={new_purpose}', text)


def generate_qr_png(text, box_size=10, border=4):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()
