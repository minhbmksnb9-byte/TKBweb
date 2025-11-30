# ======= Stage 1: Build Tesseract =======
FROM ubuntu:22.04 AS tesseract-builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-eng tesseract-ocr-vie \
        libtesseract-dev libleptonica-dev pkg-config \
        libpng-dev libjpeg-dev libtiff-dev zlib1g-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ======= Stage 2: Python Runtime =======
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# ======= Cài thư viện hệ thống cần thiết =======
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1-mesa-glx libsm6 libxext6 libxrender1 libglib2.0-0 \
        && apt-get clean && rm -rf /var/lib/apt/lists/*

# ======= Copy Tesseract từ stage 1 =======
COPY --from=tesseract-builder /usr/bin/tesseract /usr/bin/tesseract
COPY --from=tesseract-builder /usr/lib/x86_64-linux-gnu/libtesseract*.so* /usr/lib/x86_64-linux-gnu/
COPY --from=tesseract-builder /usr/lib/x86_64-linux-gnu/libleptonica*.so* /usr/lib/x86_64-linux-gnu/
COPY --from=tesseract-builder /usr/share/tesseract-ocr/ /usr/share/tesseract-ocr/

RUN ldconfig

# ======= Workdir và requirements =======
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# ======= Tạo folder uploads/results =======
RUN mkdir -p static/uploads static/results

# ======= Port Render =======
ENV PORT=10000
EXPOSE 10000

# ======= Run Gunicorn =======
CMD ["sh", "-c", "gunicorn --workers=1 --threads=2 --timeout=300 --bind 0.0.0.0:$PORT web_server:app"]
