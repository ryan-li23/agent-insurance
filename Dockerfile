# Dockerfile

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

# System deps for aiortc/pylibsrtp/opencv (adjust as needed)
# RUN apt-get update && apt-get install -y --no-install-recommends libsrtp2-1 libopus0 libvpx7 ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first for caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip 
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . /app

# FastAPI + Uvicorn
EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*", "--workers", "1"]
