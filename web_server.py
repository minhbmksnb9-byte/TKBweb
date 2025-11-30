from flask import Flask, request, render_template_string, send_from_directory
import os, threading, time
from ocr_app import TimetableOCR

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
RESULT_FOLDER = "static/results"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# ================================
#   TỰ ĐỘNG XÓA FILE CỨ SAU 5 PHÚT
# ================================
def auto_clean_folders():
    while True:
        time.sleep(300)  # 5 phút
        for folder in [UPLOAD_FOLDER, RESULT_FOLDER]:
            for file in os.listdir(folder):
                try:
                    os.remove(os.path.join(folder, file))
                except:
                    pass

threading.Thread(target=auto_clean_folders, daemon=True).start()

# ================================
# HTML PAGE
# ================================
HTML_PAGE = """ ... """  # Giữ nguyên HTML như bạn đã viết

# ================================
# ROUTER
# ================================
@app.route("/", methods=["GET","POST"])
def index():
    if request.method=="POST":
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

        expire_time = int(time.time()) + 300
        return render_template_string(HTML_PAGE, result=result, output=output, expire_time=expire_time)

    return render_template_string(HTML_PAGE, result=None)

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

if __name__=="__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
