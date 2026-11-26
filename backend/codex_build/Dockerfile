FROM python:3.10-slim

WORKDIR /app

# Install heavy OCR dependencies first so changes to core dependencies reuse this layer
COPY requirements-ocr.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements-ocr.txt && \
    pip3 uninstall -y opencv-python opencv-python-headless opencv-contrib-python && \
    pip3 install opencv-python-headless==4.9.0.80

COPY requirements-base.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements-base.txt

COPY . .

EXPOSE 8000

CMD ["python3", "api.py"]