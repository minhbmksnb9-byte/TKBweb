FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv \
        libgl1-mesa-glx libsm6 libxext6 libxrender1 libglib2.0-0 \
        tesseract-ocr tesseract-ocr-eng tesseract-ocr-vie \
        git curl wget ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p static/uploads static/results

ENV PORT=10000
EXPOSE 10000

CMD ["gunicorn", "--workers=1", "--threads=2", "--timeout=120", "--bind=0.0.0.0:10000", "web_server:app"]
