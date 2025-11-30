# =========================================================
# GIAI ĐOẠN 1: TESSERACT BUILDER (Tối giản nhất)
# =========================================================
FROM ubuntu:22.04 AS tesseract-builder

# Tách biệt cài đặt: Cài đặt Tesseract trước
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-vie \
    tesseract-ocr-eng \
 && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Cài đặt các dependencies của OpenCV (CẦN thiết cho việc COPY sang Stage 2)
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libsm6 \
    libxext6 \
    libxrender1 \
 && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Kiểm tra (Debug)
RUN which tesseract
RUN tesseract --version 


# =========================================================
# GIAI ĐOẠN 2: FINAL PYTHON RUNTIME
# =========================================================
FROM python:3.12 

# BƯỚC 1: CÀI ĐẶT CÁC THƯ VIỆN CẦN THIẾT CHO OPENCV TRÊN PYTHON
# ... (Giữ nguyên các lệnh apt-get install ở đây) ...

# BƯỚC 2: SỬA LỖI COPY VÀ CẤU HÌNH TESSERACT
WORKDIR /usr/bin
# 1. Sao chép binary Tesseract
COPY --from=tesseract-builder /usr/bin/tesseract .

# 2. Sửa lỗi COPY: Sao chép toàn bộ các thư viện dùng chung từ Giai đoạn 1 sang Giai đoạn 2
# Sao chép libtesseract và libleptonica (sử dụng ký tự đại diện *.so*)
COPY --from=tesseract-builder /usr/lib/x86_64-linux-gnu/libtesseract*.so* /usr/lib/x86_64-linux-gnu/
COPY --from=tesseract-builder /usr/lib/x86_64-linux-gnu/libleptonica*.so* /usr/lib/x86_64-linux-gnu/

# 3. Sao chép dữ liệu ngôn ngữ
COPY --from=tesseract-builder /usr/share/tesseract-ocr/ /usr/share/tesseract-ocr/

# BƯỚC 3: CẤU HÌNH MÔI TRƯỜNG
ENV TESSDATA_PREFIX /usr/share/tesseract-ocr/4.00/tessdata
RUN ldconfig # Bắt buộc để hệ thống tìm thấy các file .so vừa được copy

# BƯỚC 4: CÀI ĐẶT CODE VÀ THƯ VIỆN PYTHON
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# BƯỚC 5: CHẠY DỊCH VỤ WEB
ENV PORT 10000
CMD ["gunicorn", "--workers=4", "--bind", "0.0.0.0:$PORT", "web_server:app"]
