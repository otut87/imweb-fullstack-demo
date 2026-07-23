FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# DB는 볼륨(/data)에 — 컨테이너 재배포에도 주문/토큰 유지
ENV DB_PATH=/data/enchante_erp.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
