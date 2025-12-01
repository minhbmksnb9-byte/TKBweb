# ocr_app.py (Đã chỉnh sửa)

import os
import re
import threading
import time
import cv2
import numpy as np

# --- PaddleOCR ---
from paddleocr import PaddleOCR

# 🚀 KHỞI TẠO PADDLEOCR MỘT LẦN (GLOBAL) 🚀
# Điều này giúp tránh việc tải lại model trong mỗi request của Flask/Gunicorn
GLOBAL_OCR_ENGINE = PaddleOCR(
    use_angle_cls=False,
    lang='en',          # có thể đổi thành 'vi' nếu bạn cần tiếng Việt
    show_log=False,
    rec_algorithm='CRNN',
    det=False,          # Không cần detect vùng - mình tự cắt ROI
    # BẮT BUỘC SỬ DỤNG CPU trên hầu hết các môi trường deploy miễn phí/shared
    # Thay đổi 'use_gpu=False' thành 'use_gpu=False' nếu bạn chắc chắn không dùng GPU
    use_gpu=False 
)


class TimetableOCR:
    def __init__(self):
        self.file_anh_path = None
        self.output_image_path = None
        
        # ⚠️ SỬ DỤNG INSTANCE OCR ĐÃ KHỞI TẠO GLOBAL ⚠️
        self.ocr = GLOBAL_OCR_ENGINE

    # ... (Các hàm clean_and_normalize, is_match, detect_main_columns giữ nguyên) ...
    # ... (Bạn có thể bỏ qua phần này trong file của mình) ...

    # Làm sạch text
    def clean_and_normalize(self, text):
        text = text.upper()
        # ... (giữ nguyên logic) ...
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

    # Kiểm tra khớp từ khóa (y như bản cũ)
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
            if h > H * 0.35 and w < W * 0.2:
                x_centers.append(x + w // 2)

        x_centers = sorted(set(x_centers))
        if not x_centers:
            mid = W // 2
            return [0, mid, W]

        bounds = [0] + x_centers + [W]
        bounds = sorted(list(dict.fromkeys(bounds)))

        min_width = W * 0.1
        filtered = [bounds[0]]
        for i in range(1, len(bounds)-1):
            if bounds[i+1] - bounds[i] >= min_width:
                filtered.append(bounds[i])
        filtered.append(bounds[-1])
        return sorted(list(dict.fromkeys(filtered)))

    # Hàm xử lý chính (giữ nguyên logic)
    def process_timetable_columns(self, keyword):
        if not self.file_anh_path or not os.path.exists(self.file_anh_path):
            return "Lỗi: File ảnh không tồn tại!"

        if not keyword:
            return "Lỗi: Chưa nhập từ khóa!"

        img = cv2.imread(self.file_anh_path)
        if img is None:
            return "Lỗi: Không đọc được ảnh!"

        SCALE = 2
        img_big = cv2.resize(img, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)
        # ⚠️ CHUYỂN ROI SANG BGR TRƯỚC KHI TRUYỀN VÀO PADDLEOCR ⚠️
        # PaddleOCR hỗ trợ đọc trực tiếp từ numpy array (BGR/RGB)
        # Tuy nhiên, ảnh xám (gray) thường cho kết quả kém hơn. 
        # Chúng ta sẽ dùng ảnh BGR/RGB gốc (img_big) cho phần OCR, 
        # nhưng vẫn giữ `gray` cho phần phát hiện cột/dòng.
        
        # Ta dùng `img_big` (BGR) cho phần OCR thay vì `gray`
        W, H = img_big.shape[1], img_big.shape[0]

        gray = cv2.cvtColor(img_big, cv2.COLOR_BGR2GRAY)
        
        bin_inv = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV,
            15, 5
        )

        col_bounds = self.detect_main_columns(bin_inv, W, H)

        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (W // 40, 1))
        h_lines = cv2.dilate(cv2.erode(bin_inv, h_kernel, 1), h_kernel, 1)

        cnts, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        y_coords = [cv2.boundingRect(c)[1] for c in cnts if cv2.boundingRect(c)[2] > W * 0.35]
        y_coords.sort()

        rows = []
        for i in range(len(y_coords) - 1):
            if y_coords[i+1] - y_coords[i] > 15 * SCALE:
                rows.append((y_coords[i], y_coords[i+1]))

        found = 0
        result_img = img_big.copy()

        # ------------------------
        #        THAY THẾ OCR
        # ------------------------
        def paddle_ocr_text(roi):
            if roi.size == 0:
                return ""
            # PaddleOCR cần BGR/RGB. Ta đã chuyển sang BGR ở dưới.
            result = self.ocr.ocr(roi, det=False) 
            if result and len(result) > 0 and result[0] is not None and len(result[0]) > 0:
                # PaddleOCR trả về [ [[(box)], (text, score)], ... ]
                # Ta cần lấy text từ phần tử đầu tiên: result[0][0][1][0] 
                # (đã sửa do cấu trúc output của PaddleOCR)
                # Tuy nhiên, trong context này (det=False), output có thể là:
                # [ ([ [box_info] ], (text, score)) ]
                # Output thực tế của `ocr(..., det=False)` là list các (text, score)
                # Dựa vào cách bạn code ban đầu: result[0][0], ta giả định nó là text.
                # Cấu trúc output của PaddleOCR khi `det=False` là: `[[text, score], ...]`
                return result[0][0] # Lấy text của kết quả đầu tiên
            return ""

        # Quét từng ô trong bảng
        for (y1, y2) in rows:
            for i in range(len(col_bounds) - 1):
                x1, x2 = col_bounds[i], col_bounds[i+1]

                # ⚠️ CẮT ROI TỪ ẢNH MÀU GỐC (img_big) hoặc (ảnh xám `gray`)
                # Nếu PaddleOCR của bạn hoạt động tốt với ảnh xám, dùng `gray`.
                # Nếu không, dùng `img_big`. Thường dùng ảnh màu (BGR) tốt hơn.
                # Ta dùng `img_big` ở đây.
                roi = img_big[y1+4:y2-4, x1+4:x2-4] 

                try:
                    text = paddle_ocr_text(roi)
                except Exception as e:
                    # In lỗi để debug nếu cần
                    # print(f"OCR Error: {e}")
                    text = ""

                if self.is_match(text, keyword):
                    found += 1
                    cv2.rectangle(result_img, (x1, y1), (x2, y2), (0, 0, 255), 10)

        final_img = cv2.resize(result_img, (img.shape[1], img.shape[0]))

        # ⚠️ CẢI THIỆN TÊN FILE CHO WEBSERVER: Đảm bảo chỉ dùng tên file, không dùng os.getcwd()
        # Trong môi trường Docker/Gunicorn, os.getcwd() có thể không phải nơi mong muốn.
        # Ta sẽ chuyển logic quản lý đường dẫn file kết quả sang web_server.py
        
        # ⚠️ TẠM THỜI GIỮ LẠI LOGIC CŨ NHƯNG CẢNH BÁO
        # Tuy nhiên, `web_server.py` đã tạo `RESULT_FOLDER` an toàn. 
        # Ta sẽ dùng thư mục tạm (temp directory) hoặc lưu file kết quả ở `/tmp`
        # và để `web_server.py` chịu trách nhiệm di chuyển nó.

        # Thay vì os.getcwd(), lưu vào thư mục TẠM /tmp hoặc một thư mục cố định
        temp_dir = "/tmp" 
        out_name = f"KetQua_{int(time.time())}_{threading.current_thread().name}.jpg"
        self.output_image_path = os.path.join(temp_dir, out_name) 
        
        # Đảm bảo thư mục tồn tại
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        cv2.imwrite(self.output_image_path, final_img)

        return f"Tìm kiếm xong! Tổng số ô khớp: {found}"
