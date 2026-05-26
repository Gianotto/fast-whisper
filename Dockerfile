FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY whisper_service/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt

ARG WHISPER_MODEL=base
RUN python -c "import whisper; whisper.load_model('${WHISPER_MODEL}')"

COPY whisper_service/ ./whisper_service/

EXPOSE 8001

CMD ["uvicorn", "whisper_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
