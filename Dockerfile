# =========================================================
# GIAI ĐOẠN 1: TESSERACT BUILDER (DEBUG ON)
# Dùng image Debian ổn định để cài Tesseract
# =========================================================
FROM debian:bookworm-slim AS tesseract-builder

RUN echo "--- DEBUG: STAGE 1 STARTED: Installing Tesseract and dependencies ---"

# Cài đặt Tesseract và các gói ngôn ngữ + dependencies cần thiết cho Runtime
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-vie \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libsm6 \
    libxext6 \
    libxrender1 \
    libtesseract5 \
    libleptonica5 \
 && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# DEBUG CHECK 1: Xác nhận Tesseract có sẵn trong Builder Stage
RUN which tesseract
RUN tesseract --version 
RUN echo "--- DEBUG: STAGE 1 COMPLETED SUCCESSFULLY: Tesseract installed. ---"


# =========================================================
# GIAI ĐOẠN 2: FINAL PYTHON RUNTIME (DEBUG ON)
# =========================================================
FROM python:3.12 

RUN echo "--- DEBUG: STARTING STAGE 2 (PYTHON RUNTIME) ---"

# BƯỚC 1: COPY TESSERACT VÀ CÁC THƯ VIỆN CẦN THIẾT TỪ GIAI ĐOẠN 1
RUN echo "--- DEBUG: COPYING TESSERACT BINARY AND LIBRARIES NOW ---"
# Sao chép file thực thi Tesseract
COPY --from=tesseract-builder /usr/bin/tesseract /usr/bin/tesseract
# Sao chép các thư viện dùng chung mà Tesseract cần
COPY --from=tesseract-builder /usr/lib/x86_64-linux-gnu/libtesseract.so.5 /usr/lib/x86_64-linux-gnu/
COPY --from=tesseract-builder /usr/lib/x86_64-linux-gnu/libleptonica.so.5 /usr/lib/x86_64-linux-gnu/

# Sao chép dữ liệu ngôn ngữ
COPY --from=tesseract-builder /usr/share/tesseract-ocr/ /usr/share/tesseract-ocr/

# BƯỚC 2: CẤU HÌNH MÔI TRƯỜNG
ENV TESSDATA_PREFIX /usr/share/tesseract-ocr/4.00/tessdata
# Cập nhật dynamic linker cache
RUN ldconfig

# DEBUG CHECK 2: Xác nhận binary đã được copy vào môi trường cuối cùng
RUN echo "--- DEBUG: VERIFYING FINAL PATHS ---"
RUN ls -l /usr/bin/tesseract
RUN echo "TESSDATA_PREFIX is set to: $TESSDATA_PREFIX"

# BƯỚC 3: CÀI ĐẶT CODE VÀ THƯ VIỆN PYTHON
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# BƯỚC 4: CHẠY DỊCH VỤ WEB
ENV PORT 10000
CMD ["gunicorn", "--workers=4", "--bind", "0.0.0.0:$PORT", "web_server:app"]
