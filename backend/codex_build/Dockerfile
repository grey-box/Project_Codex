FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install requests

RUN pip3 uninstall -y opencv-python opencv-python-headless opencv-contrib-python && \
    pip3 install opencv-python-headless

COPY . .

EXPOSE 8000

CMD ["python3", "api.py"]