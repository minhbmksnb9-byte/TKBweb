# ================================
# BASE UBUNTU (ổn định nhất)
# ================================
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# ================================
# CÀI PYTHON + PIP + DEV TOOLS
# ================================
RUN apt-get update && \
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ================================
# CÀI TESSERACT + NGÔN NGỮ
# ================================
RUN apt-get update && \
    apt-get install -y \
        tesseract-ocr \
        tesseract-ocr-vie \
        tesseract-ocr-eng \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ================================
# CÀI ĐẶT DEPENDENCIES CHO OPENCV
# ================================
RUN apt-get update && \
    apt-get install -y \
        libgl1-mesa-glx \
        libsm6 \
        libxext6 \
        libxrender1 \
        libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ================================
# CẤU HÌNH WORKDIR
# ================================
WORKDIR /app

# ================================
# CÀI REQUIREMENTS
# ================================
COPY requirements.txt .

# Upgrade pip để tránh lỗi build opencv / pillow
RUN pip3 install --upgrade pip

RUN pip3 install --no-cache-dir -r requirements.txt

# ================================
# COPY CODE
# ================================
COPY . .

# ================================
# CONFIG TESSERACT
# ================================
ENV TESSDATA_PREFIX="/usr/share/tesseract-ocr/4.00/tessdata"

# ================================
# RENDER PORT
# ================================
ENV PORT=10000
EXPOSE 10000

# ================================
# RUN GUNICORN (FIX OOM)
# ================================
CMD ["gunicorn", "--workers=1", "--threads=1", "--timeout=180", "--bind=0.0.0.0:10000", "web_server:app"]
