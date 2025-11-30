from PIL import Image, ImageOps, ImageFilter, ImageDraw
import pytesseract
import os
import uuid
import re

class LightweightOCR:
    def __init__(self, results_dir="static/results"):
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
        data = pytesseract.image_to_data(img, lang=lang, config="--psm 6", output_type=pytesseract.Output.DICT)
        n_boxes = len(data.get('text', []))
        draw = ImageDraw.Draw(img.convert("RGB"))
        found = 0
        grouped_boxes = []
        for i in range(n_boxes):
            txt = data['text'][i]
            conf = int(data['conf'][i]) if str(data['conf'][i]).lstrip('-').isdigit() else -1
            if not txt or conf < conf_threshold:
                continue
            if self._is_token_match(txt, keyword):
                x, y, w_box, h_box = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                grouped_boxes.append((x, y, x + w_box, y + h_box))
                found += 1
        if grouped_boxes:
            merged = []
            grouped_boxes.sort()
            cur = list(grouped_boxes[0])
            for b in grouped_boxes[1:]:
                if b[0] <= cur[2] + 10 and b[1] <= cur[3] + 10:
                    cur[2] = max(cur[2], b[2])
                    cur[3] = max(cur[3], b[3])
                else:
                    merged.append(tuple(cur))
                    cur = list(b)
            merged.append(tuple(cur))
            out_img = img.convert("RGB")
            draw = ImageDraw.Draw(out_img)
            wscale = max(1, int(max(1, out_img.size[0] / 400)))
            for box in merged:
                draw.rectangle(box, outline=(255,0,0), width=wscale)
            name = f"Result_{uuid.uuid4().hex}.jpg"
            out_path = os.path.join(self.results_dir, name)
            out_img.save(out_path, quality=85)
            self.output_image_path = out_path
        else:
            name = f"Result_{uuid.uuid4().hex}.jpg"
            out_path = os.path.join(self.results_dir, name)
            img.convert("RGB").save(out_path, quality=85)
            self.output_image_path = out_path
        return f"Tìm xong! Tổng số ô khớp: {found}"
