from flask import Flask, request, render_template_string, send_from_directory
import os
import time
import uuid
import re
from PIL import Image, ImageOps, ImageFilter, ImageDraw
import pytesseract
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
RESULT_FOLDER = "static/results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

def auto_clean_folders():
    while True:
        time.sleep(300)
        for folder in (UPLOAD_FOLDER, RESULT_FOLDER):
            for fname in os.listdir(folder):
                try:
                    path = os.path.join(folder, fname)
                    if os.path.isfile(path):
                        if time.time() - os.path.getmtime(path) > 300:
                            os.remove(path)
                except:
                    pass

import threading
threading.Thread(target=auto_clean_folders, daemon=True).start()

HTML_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>OCR Timetable Web</title>
    <style>
        body { font-family: Arial; background: #f1f3f6; display: flex; justify-content: center; padding-top: 40px; }
        .container { width: 650px; }
        .box { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 3px 12px rgba(0,0,0,0.1); margin-top: 25px; }
        button { margin-top: 15px; padding: 12px 20px; width: 100%; border: none; background: #007bff; color: white; border-radius: 8px; font-size: 16px; cursor: pointer; transition: 0.2s; }
        button:hover { background: #005ad1; }
        img { border-radius: 12px; margin-top: 15px; border: 1px solid #ccc; }
        .result-text { background: #f8f9fa; border-left: 4px solid #007bff; padding: 10px; border-radius: 6px; }
        a.download { display: inline-block; margin-top: 12px; padding: 10px 16px; background: #28a745; color: white; border-radius: 8px; text-decoration: none; }
        #loadingOverlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.45); backdrop-filter: blur(3px); z-index: 9999; justify-content: center; align-items: center; color: white; font-size: 28px; font-weight: bold; }
        .spinner { margin-right: 15px; width: 28px; height: 28px; border: 4px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 0.9s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
    <script>
        function showLoading() { document.getElementById("loadingOverlay").style.display = "flex"; }
    </script>
</head>
<body>
<div id="loadingOverlay">
    <div class="spinner"></div> Đang xử lý...
</div>
<div class="container">
<h2>📘 Tìm Kiếm Thời Khóa Biểu</h2>
<div class="box">
    <form action="/" method="post" enctype="multipart/form-data" onsubmit="showLoading()">
        <label>Chọn ảnh:</label><br>
        <input type="file" name="image" accept="image/*" required><br><br>
        <label>Từ khóa:</label><br>
        <input type="text" name="keyword" placeholder="VD: Toán, T5, Tiết 3..." required><br>
        <button type="submit">🔍 Bắt đầu xử lý</button>
    </form>
</div>
{% if result %}
<div class="box">
    <h3>Kết quả:</h3>
    <div class="result-text">{{ result }}</div>
    {% if output %}
    <img src="{{ output }}" width="100%"><br>
    <a class="download" href="{{ output }}" download>Tải ảnh kết quả</a>
    <div id="countdown" style="margin-top: 15px; font-weight: bold; color: #d9534f;">
        🕒 File sẽ tự động xoá trong: <span id="timeLeft">05:00</span>
    </div>
    <script>
        let expireAt = {{ expire_time }} * 1000;
        function updateCountdown() {
            let now = Date.now();
            let diff = Math.max(0, expireAt - now);
            let sec = Math.floor(diff / 1000);
            let m = Math.floor(sec / 60);
            let s = sec % 60;
            document.getElementById("timeLeft").textContent = String(m).padStart(2,'0') + ":" + String(s).padStart(2,'0');
            if (sec <= 0) { document.getElementById("countdown").textContent = "⏳ File đã bị xoá tự động."; clearInterval(timer); }
        }
        let timer = setInterval(updateCountdown, 1000);
        updateCountdown();
    </script>
    {% endif %}
</div>
{% endif %}
</div>
</body>
</html>
"""

class LightweightOCR:
    def __init__(self, results_dir=RESULT_FOLDER):
        self.results_dir = results_dir
        os.makedirs(self.results_dir, exist_ok=True)
        self.output_image_path = None
    def clean_and_normalize(self, text):
        if text is None:
            return ""
        text = str(text).upper()
        repl = {'L':'1','I':'1','|':' ','J':'1','O':'0','S':'5','Z':'2','B':'8',']':'1','[':'1','}':'1','{':'1'}
        for a,b in repl.items():
            text = text.replace(a,b)
        text = re.sub(r"[^A-Z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    def _is_token_match(self, token, keyword):
        t = self.clean_and_normalize(token)
        k = self.clean_and_normalize(keyword)
        if not k:
            return False
        if not any(ch.isdigit() for ch in k):
            return k in t.split()
        if t.startswith(k):
            return True
        if k.replace("A","4") == t or k.replace("4","A") == t:
            return True
        return False
    def process(self, file_path, keyword, lang="eng", max_width=1024, conf_threshold=40):
        if not file_path or not os.path.exists(file_path):
            return "Lỗi: File ảnh không tồn tại!"
        try:
            pytesseract.get_tesseract_version()
        except:
            return "Lỗi: Tesseract chưa cấu hình!"
        try:
            img = Image.open(file_path)
        except:
            return "Lỗi: Không đọc được ảnh!"
        w,h = img.size
        if w > max_width:
            ratio = max_width / w
            img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
        img = ImageOps.grayscale(img)
        img = ImageOps.autocontrast(img)
        img = img.filter(ImageFilter.MedianFilter(3))
        try:
            data = pytesseract.image_to_data(img, lang=lang, config="--psm 6", output_type=pytesseract.Output.DICT)
        except:
            return "Lỗi: OCR thất bại (pytesseract)."
        n_boxes = len(data.get('text', []))
        found = 0
        grouped_boxes = []
        for i in range(n_boxes):
            txt = data['text'][i]
            conf_raw = data.get('conf', [])[i] if 'conf' in data else '-1'
            try:
                conf = int(float(conf_raw))
            except:
                conf = -1
            if not txt or conf < conf_threshold:
                continue
            if self._is_token_match(txt, keyword):
                x, y, w_box, h_box = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                grouped_boxes.append((x, y, x + w_box, y + h_box))
                found += 1
        base_img = img.convert("RGB")
        if grouped_boxes:
            grouped_boxes.sort()
            merged = []
            cur = list(grouped_boxes[0])
            for b in grouped_boxes[1:]:
                if b[0] <= cur[2] + 10 and b[1] <= cur[3] + 10:
                    cur[2] = max(cur[2], b[2])
                    cur[3] = max(cur[3], b[3])
                else:
                    merged.append(tuple(cur))
                    cur = list(b)
            merged.append(tuple(cur))
            draw = ImageDraw.Draw(base_img)
            wscale = max(1, int(max(1, base_img.size[0] / 400)))
            for box in merged:
                draw.rectangle(box, outline=(255,0,0), width=wscale)
        name = f"Result_{uuid.uuid4().hex}.jpg"
        out_path = os.path.join(self.results_dir, name)
        try:
            base_img.save(out_path, quality=85)
        except:
            return "Lỗi: Không lưu được ảnh kết quả."
        self.output_image_path = out_path
        return f"Tìm xong! Tổng số ô khớp: {found}"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "image" not in request.files:
            return render_template_string(HTML_PAGE, result="Lỗi: Không tìm thấy file upload.", output=None)
        img_file = request.files["image"]
        keyword = (request.form.get("keyword") or "").strip()
        if not keyword:
            return render_template_string(HTML_PAGE, result="Lỗi: Chưa nhập từ khóa.", output=None)
        filename = secure_filename(img_file.filename)
        if filename == "":
            ext = ".jpg"
        else:
            ext = os.path.splitext(filename)[1] or ".jpg"
        unique_name = f"upload_{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(UPLOAD_FOLDER, unique_name)
        try:
            img_file.save(save_path)
        except:
            return render_template_string(HTML_PAGE, result="Lỗi: Không lưu được file upload.", output=None)
        engine = LightweightOCR()
        result = engine.process(save_path, keyword, lang="eng", max_width=1024, conf_threshold=40)
        output = None
        if engine.output_image_path and os.path.exists(engine.output_image_path):
            try:
                new_name = os.path.basename(engine.output_image_path)
                new_path = os.path.join(RESULT_FOLDER, new_name)
                if engine.output_image_path != new_path:
                    os.replace(engine.output_image_path, new_path)
                output = f"/static/results/{new_name}"
            except:
                output = None
        expire_time = int(time.time()) + 300
        return render_template_string(HTML_PAGE, result=result, output=output, expire_time=expire_time)
    return render_template_string(HTML_PAGE, result=None)

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
