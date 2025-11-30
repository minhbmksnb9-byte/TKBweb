# web_server.py
from flask import Flask, request, render_template_string, send_from_directory
import os, threading, time
from ocr_app import TimetableOCR

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
RESULT_FOLDER = "static/results"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# =====================================
#   TỰ ĐỘNG XÓA FILE CỨ SAU 5 PHÚT
# =====================================
def auto_clean_folders():
    while True:
        time.sleep(300)  # 5 phút
        for folder in [UPLOAD_FOLDER, RESULT_FOLDER]:
            for file in os.listdir(folder):
                try:
                    os.remove(os.path.join(folder, file))
                    print("Đã xoá:", file)
                except:
                    pass

threading.Thread(target=auto_clean_folders, daemon=True).start()


# =====================================
#                HTML PAGE
# =====================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>OCR Timetable Web</title>
    <style>
        body {
            font-family: Arial;
            background: #f1f3f6;
            display: flex;
            justify-content: center;
            padding-top: 40px;
        }
        .container { width: 650px; }
        .box {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 3px 12px rgba(0,0,0,0.1);
            margin-top: 25px;
        }
        button {
            margin-top: 15px;
            padding: 12px 20px;
            width: 100%;
            border: none;
            background: #007bff;
            color: white;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: 0.2s;
        }
        button:hover { background: #005ad1; }
        img {
            border-radius: 12px;
            margin-top: 15px;
            border: 1px solid #ccc;
        }
        .result-text {
            background: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 10px;
            border-radius: 6px;
        }
        a.download {
            display: inline-block;
            margin-top: 12px;
            padding: 10px 16px;
            background: #28a745;
            color: white;
            border-radius: 8px;
            text-decoration: none;
        }

        /* Loading overlay */
        #loadingOverlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.45);
            backdrop-filter: blur(3px);
            z-index: 9999;
            justify-content: center;
            align-items: center;
            color: white;
            font-size: 28px;
            font-weight: bold;
        }
        .spinner {
            margin-right: 15px;
            width: 28px;
            height: 28px;
            border: 4px solid #fff;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 0.9s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>

    <script>
        function showLoading() {
            document.getElementById("loadingOverlay").style.display = "flex";
        }
    </script>

</head>
<body>

<!-- LOADING OVERLAY -->
<div id="loadingOverlay">
    <div class="spinner"></div> Đang xử lý...
</div>

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
    <img src="{{ output }}" width="100%">
    <br>
    <a class="download" href="{{ output }}" download>Tải ảnh kết quả</a>

    <!-- COUNTDOWN -->
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

            document.getElementById("timeLeft").textContent =
                String(m).padStart(2,'0') + ":" + String(s).padStart(2,'0');

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


# =====================================
#                 ROUTER
# =====================================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":

        img_file = request.files["image"]
        keyword = request.form["keyword"]

        save_path = os.path.join(UPLOAD_FOLDER, img_file.filename)
        img_file.save(save_path)

        engine = TimetableOCR()
        engine.file_anh_path = save_path

        result = engine.process_timetable_columns(keyword)

        output = None
        if engine.output_image_path:
            name = os.path.basename(engine.output_image_path)
            new_path = os.path.join(RESULT_FOLDER, name)
            os.rename(engine.output_image_path, new_path)
            output = f"/static/results/{name}"

        # thời gian xoá file (5 phút)
        expire_time = int(time.time()) + 300

        return render_template_string(
            HTML_PAGE,
            result=result,
            output=output,
            expire_time=expire_time
        )

    return render_template_string(HTML_PAGE, result=None)


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
