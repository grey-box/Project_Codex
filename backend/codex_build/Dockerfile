FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install requests

COPY . .

EXPOSE 8000

CMD ["python3", "api.py"]