import cv2
import numpy as np
from pyzbar.pyzbar import decode

def scan_qr_from_bytes(image_bytes: bytes) -> str:
    try:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # 1. Pyzbar
        decoded = decode(img)
        if decoded: return decoded[0].data.decode('utf-8')

        # 2. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        decoded = decode(gray)
        if decoded: return decoded[0].data.decode('utf-8')

        # 3 Binarization
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        decoded = decode(thresh)
        if decoded: return decoded[0].data.decode('utf-8')

        # OpenCV
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img)
        if data: return data
    except Exception:
        pass

    return ""