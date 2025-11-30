# ================================
# Base Image
# ================================
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# ================================
# Install Python + Pip
# ================================
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv python3-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ================================
# Install Tesseract + Languages
# ================================
RUN apt-get update && \
    apt-get install -y \
        tesseract-ocr \
        tesseract-ocr-vie \
        tesseract-ocr-eng && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ================================
# Dependencies for OpenCV
# ================================
RUN apt-get update && \
    apt-get install -y \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libjpeg-dev \
        zlib1g-dev \
        libpng-dev \
        libtiff5 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ================================
# Working directory
# ================================
WORKDIR /app

# ================================
# Install Python requirements
# ================================
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# ================================
# Copy source code
# ================================
COPY . .

# ================================
# Tesseract path
# ================================
ENV TESSDATA_PREFIX="/usr/share/tesseract-ocr/4.00/tessdata"

# ================================
# Port for Render
# ================================
ENV PORT=10000
EXPOSE 10000

# ================================
# Run Gunicorn
# ================================
CMD ["gunicorn", "--workers=1", "--timeout=120", "--bind=0.0.0.0:10000", "web_server:app"]
