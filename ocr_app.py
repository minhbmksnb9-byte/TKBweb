# ocr_app.py
import os
import re
import threading
import time
import cv2
import pytesseract
import numpy as np

# --- CẤU HÌNH TESSERACT (Đã sửa cho Linux/Docker) ---
# Thường không cần set path cứng nếu tesseract đã được cài đặt đúng cách.

class TimetableOCR:
    def __init__(self):
        self.file_anh_path = None
        self.output_image_path = None

    # Làm sạch text
    def clean_and_normalize(self, text):
        text = text.upper()
        replacements = {
            'L': '1', 'I': '1', '|': ' ', 'J': '1',
            'O': '0', 'S': '5', 'Z': '2', 'B': '8',
            ']': '1', '[': '1', '}': '1', '{': '1'
        }
        for a, b in replacements.items():
            text = text.replace(a, b)

        text = re.sub(r"[^A-Z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    # Kiểm tra khớp từ khóa
    def is_match(self, row_text, keyword):
        clean_row = self.clean_and_normalize(row_text)
        clean_key = self.clean_and_normalize(keyword)

        if not any(c.isdigit() for c in clean_key):
            return clean_key in clean_row.split()

        tokens = clean_row.split()
        for idx, token in enumerate(tokens):
            if token.startswith(clean_key):
                return True
            if idx + 1 < len(tokens):
                if (token + tokens[idx+1]).startswith(clean_key):
                    return True
            if clean_key.replace("A", "4") == token or clean_key.replace("4", "A") == token:
                return True

        return False

    # Tìm cột chính
    def detect_main_columns(self, binary_img, W, H):
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(3, H // 40)))
        v_lines = cv2.dilate(cv2.erode(binary_img, v_kernel, 1), v_kernel, 1)

        cnts, _ = cv2.findContours(v_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        x_centers = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            # Giảm ngưỡng phát hiện đường dọc, giảm W * 0.4 xuống W * 0.35
            if h > H * 0.35 and w < W * 0.2:
                x_centers.append(x + w // 2)

        x_centers = sorted(set(x_centers))

        if not x_centers:
            mid = W // 2
            return [0, mid, W]

        bounds = [0] + x_centers + [W]
        bounds = sorted(list(dict.fromkeys(bounds)))

        # Giảm ngưỡng phát hiện cột tối thiểu
        min_width = W * 0.1
        filtered = [bounds[0]]

        for i in range(1, len(bounds)-1):
            if bounds[i+1] - bounds[i] >= min_width:
                filtered.append(bounds[i])

        filtered.append(bounds[-1])
        return sorted(list(dict.fromkeys(filtered)))

    # Hàm xử lý chính
    def process_timetable_columns(self, keyword):
        if not self.file_anh_path or not os.path.exists(self.file_anh_path):
            return "Lỗi: File ảnh không tồn tại!"

        if not keyword:
            return "Lỗi: Chưa nhập từ khóa!"

        img = cv2.imread(self.file_anh_path)
        if img is None:
            return "Lỗi: Không đọc được ảnh!"

        # 🚀 TỐI ƯU HÓA RAM CHÍNH: Giảm SCALE từ 3 xuống 2. 
        # Việc giảm SCALE giúp giảm 56% kích thước bộ nhớ so với SCALE 3 (2^2 vs 3^2).
        SCALE = 2 
        img_big = cv2.resize(img, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img_big, cv2.COLOR_BGR2GRAY)

        # Sử dụng kích thước ảnh lớn (đã phóng to)
        W, H = img_big.shape[1], img_big.shape[0]

        # Áp dụng ngưỡng trên ảnh xám
        bin_inv = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                         cv2.THRESH_BINARY_INV, 15, 5)

        # Tách cột
        col_bounds = self.detect_main_columns(bin_inv, W, H)

        # Tách hàng
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (W // 40, 1))
        h_lines = cv2.dilate(cv2.erode(bin_inv, h_kernel, 1), h_kernel, 1)

        cnts, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Giảm ngưỡng chiều rộng để phát hiện hàng: W * 0.4 xuống W * 0.35
        y_coords = [cv2.boundingRect(c)[1] for c in cnts if cv2.boundingRect(c)[2] > W * 0.35]
        y_coords.sort()

        rows = []
        # Điều chỉnh ngưỡng khoảng cách giữa các hàng để khớp với ảnh đã phóng to SCALE=2
        # 15 * SCALE = 30
        for i in range(len(y_coords) - 1):
            if y_coords[i+1] - y_coords[i] > 15 * SCALE:
                rows.append((y_coords[i], y_coords[i+1]))

        found = 0
        result_img = img_big.copy()

        # ⚙️ TỐI ƯU HÓA CPU (Tesseract): Sử dụng PSM 7 thay vì PSM 6.
        # PSM 7 (Treat the image as a single text line) thường nhanh hơn và chính xác hơn 
        # khi OCR các vùng nhỏ (ô trong bảng).
        custom_config = r'--oem 3 --psm 7' 

        for (y1, y2) in rows:
            for i in range(len(col_bounds) - 1):
                x1, x2 = col_bounds[i], col_bounds[i+1]

                # Cắt vùng ảnh xám (gray) thay vì ảnh nhị phân (bin_inv) để OCR
                roi = gray[y1+4:y2-4, x1+4:x2-4]
                if roi.size < 8:
                    continue

                try:
                    # Chú ý: Có thể tối ưu hơn nếu chỉ OCR ở cột đầu tiên
                    text = pytesseract.image_to_string(roi, lang="eng", config=custom_config)
                except:
                    text = ""

                if self.is_match(text, keyword):
                    found += 1
                    cv2.rectangle(result_img, (x1, y1), (x2, y2), (0, 0, 255), 10)

        # Resize lại đúng kích thước gốc
        final_img = cv2.resize(result_img, (img.shape[1], img.shape[0]))

        # Lưu file
        out_name = f"KetQua_{int(time.time())}_{threading.current_thread().name}.jpg"
        self.output_image_path = os.path.join(os.getcwd(), out_name)
        cv2.imwrite(self.output_image_path, final_img)

        return f"Tìm kiếm xong! Tổng số ô khớp: {found}"
