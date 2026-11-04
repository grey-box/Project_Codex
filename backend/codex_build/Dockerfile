FROM python:3.10-slim

# 1. Install required system libraries for OpenCV & PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Copy ONLY requirements first to leverage Docker layer cache
COPY requirements.txt .

# 3. Install PyTorch CPU version explicitly with extra-index-url
RUN pip3 install --no-cache-dir torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip3 install --no-cache-dir -r requirements.txt

# 4. Copy the rest of your application code
COPY . .

# 5. Pre-download EasyOCR weights so container starts instantly
RUN python3 -c "import easyocr; reader = easyocr.Reader(['en'], gpu=False)"

EXPOSE 8000

CMD ["python3", "api.py"]