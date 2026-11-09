FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
COPY tests/requirements-test.txt ./tests/requirements-test.txt
RUN pip3 install --no-cache-dir -r tests/requirements-test.txt

# paddleocr/paddlex pulls in opencv-contrib-python transitively, which needs
# libGL (not present in this slim image). Force back to the headless build,
# same fix the main api Dockerfile already applies.
RUN pip3 uninstall -y opencv-python opencv-python-headless opencv-contrib-python && \
    pip3 install opencv-python-headless

CMD ["pytest"]
