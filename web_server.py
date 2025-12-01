# web_server.py (Đã chỉnh sửa)
from flask import Flask, request, render_template_string, send_from_directory
import os, threading, time, shutil
import tempfile # Thêm thư viện tempfile
from ocr_app import TimetableOCR

app = Flask(__name__, static_folder="static") # Chỉ định rõ thư mục static

# ============================
# ĐƯỜNG DẪN AN TOÀN
# ============================
# Đảm bảo đường dẫn tuyệt đối cho môi trường Gunicorn
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# ⚠️ Nên dùng thư mục CHẮC CHẮN có quyền ghi, không phải thư mục ứng dụng
# Tuy nhiên, ta vẫn giữ nguyên để phù hợp với Dockerfile
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")
RESULT_FOLDER = os.path.join(STATIC_DIR, "results")

# Tạo thư mục nếu chưa có
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# ============================
# TỰ ĐỘNG XOÁ FILE SAU 5 PHÚT
# ============================
# Giữ nguyên logic này, nhưng nên dùng cron job bên ngoài nếu deploy lớn
def auto_clean_folders():
    while True:
        # ⚠️ Nên tăng thời gian chờ lên 3600 (1 tiếng) hoặc hơn để giảm tải
        time.sleep(300) 
        for folder in [UPLOAD_FOLDER, RESULT_FOLDER]:
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    fp = os.path.join(folder, f)
                    # Kiểm tra thời gian tạo file nếu cần, ở đây ta xoá tất cả
                    # ⚠️ Cần kiểm tra file nào quá cũ (> 5 phút) để tránh xoá nhầm file đang dùng
                    # Hiện tại logic cũ vẫn xoá tất cả sau 5 phút ngủ. Ta giữ nguyên
                    try:
                        # Thêm kiểm tra thời gian để an toàn hơn
                        if os.path.getmtime(fp) < time.time() - 300: # Xóa file cũ hơn 5 phút
                            os.remove(fp)
                    except:
                        pass

threading.Thread(target=auto_clean_folders, daemon=True).start()

# ... (HTML_PAGE giữ nguyên) ...

# ⚠️ BẠN CẦN ĐẢM BẢO HTML_PAGE ĐƯỢC ĐỊNH NGHĨA HOÀN CHỈNH Ở ĐÂY
# ============================
#  HTML PAGE (GIỮ NGUYÊN)
# ============================
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
        button { margin-top: 15px; padding: 12px 20px; width: 100%; border: none; background: #007bff; color: white; border-radius: 8px; font-size: 16px; cursor: pointer; }
        button:hover { background: #005ad1; }
        img { border-radius: 12px; margin-top: 15px; border: 1px solid #ccc; max-width: 100%; }
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
<div id="loadingOverlay"><div class="spinner"></div> Đang xử lý...</div>
<div class="container">
<h2>📘 Tìm Kiếm Thời Khóa Biểu</h2>
<div class="box">
    <form action="/" method="post" enctype="multipart/form-data" onsubmit="showLoading()">
        <label>Chọn ảnh:</label><br>
        <input type="file" name="image" required><br><br>
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
    <img src="{{ output }}">
    <br>
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
            if (sec <= 0) {
                document.getElementById("countdown").textContent = "⏳ File đã bị xoá tự động.";
                clearInterval(timer);
            }
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


# ============================
# ROUTES
# ============================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":

        # --- xử lý file ảnh ---
        if 'image' not in request.files:
            return render_template_string(HTML_PAGE, result="Chưa chọn file")

        img_file = request.files["image"]
        if img_file.filename == "":
            return render_template_string(HTML_PAGE, result="Tên file trống")

        keyword = request.form.get("keyword", "")
        
        # ⚠️ TẠO TÊN FILE DUY NHẤT VÀ LƯU VÀO FOLDER UPLOAD
        # Dùng tên file + timestamp + thread name để đảm bảo unique
        unique_filename = f"{int(time.time())}_{threading.current_thread().name}_{img_file.filename}"
        save_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        try:
            img_file.save(save_path)
        except Exception as e:
            # Lỗi quyền hoặc đường dẫn
            return render_template_string(HTML_PAGE, result=f"Lỗi lưu file: {e}")

        # --- chạy OCR ---
        engine = TimetableOCR()
        engine.file_anh_path = save_path

        result = engine.process_timetable_columns(keyword)

        # --- xuất ảnh kết quả ---
        output = None
        if engine.output_image_path and os.path.exists(engine.output_image_path):
            
            # Tên file đã được tạo unique trong ocr_app.py
            name = os.path.basename(engine.output_image_path) 
            new_path = os.path.join(RESULT_FOLDER, name)
            
            # Di chuyển file từ /tmp sang thư mục static/results
            try:
                shutil.move(engine.output_image_path, new_path)
            except Exception as e:
                # Lỗi di chuyển (ví dụ: quyền truy cập)
                return render_template_string(HTML_PAGE, result=f"Lỗi di chuyển file kết quả: {e}")

            output = f"/static/results/{name}"
            # Xóa file ảnh gốc sau khi xử lý (không bắt buộc nhưng nên làm)
            try:
                os.remove(save_path)
            except:
                pass 

        expire_time = int(time.time()) + 300 # 5 phút
        
        # ⚠️ Xóa file kết quả ngay nếu không tìm thấy (giúp dọn dẹp)
        if output is None and engine.output_image_path and os.path.exists(engine.output_image_path):
            try:
                 os.remove(engine.output_image_path) # Xóa file tạm /tmp
            except:
                pass


        return render_template_string(
            HTML_PAGE,
            result=result,
            output=output,
            expire_time=expire_time
        )

    return render_template_string(HTML_PAGE, result=None)

# ============================
# STATIC (Giữ nguyên, Flask sẽ tự map `static` nếu dùng `static_folder="static"`)
# ============================
@app.route("/static/<path:path>")
def static_files(path):
    # Dùng send_from_directory với đường dẫn tuyệt đối an toàn hơn
    return send_from_directory(STATIC_DIR, path)

# ============================
# MAIN
# ============================
if __name__ == "__main__":
    # ⚠️ Đổi cổng mặc định 5000 thành 10000 để khớp với Dockerfile
    app.run(debug=True, port=10000)
