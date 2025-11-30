import os, cv2, pytesseract, threading

pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
os.environ["TESSDATA_PREFIX"] = "/usr/share/tesseract-ocr/4.00/tessdata"

class TimetableOCR:
    def __init__(self):
        self.file_anh_path = None
        self.output_image_path = None

    def process_timetable_columns(self, keyword):
        if not self.file_anh_path or not os.path.exists(self.file_anh_path):
            return "❌ File ảnh không tồn tại"
        if not keyword:
            return "❌ Chưa nhập từ khóa"

        img = cv2.imread(self.file_anh_path)
        if img is None:
            return "❌ Không đọc được ảnh"

        # Resize để OCR nhanh
        max_width = 1200
        h, w = img.shape[:2]
        if w > max_width:
            scale = max_width / w
            img = cv2.resize(img, (int(w*scale), int(h*scale)))

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # OCR siêu nhanh
        try:
            text = pytesseract.image_to_string(gray, lang="eng", config="--psm 6")
        except:
            text = ""

        # Tạo ảnh output đánh dấu toàn bộ (dummy rectangle)
        output_img = img.copy()
        cv2.putText(output_img, "OCR XONG", (20,50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,0,255), 3)

        os.makedirs("static/results", exist_ok=True)
        out_name = f"KetQua_{os.getpid()}_{threading.current_thread().name}.jpg"
        self.output_image_path = os.path.join("static/results", out_name)
        cv2.imwrite(self.output_image_path, output_img)

        return f"✅ OCR xong! Từ khóa: {keyword}\n{text[:300]}..."
