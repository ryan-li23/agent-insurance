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

# Streamlit
EXPOSE 8501
CMD ["sh", "-c", "streamlit run app.py --server.address 0.0.0.0 --server.port ${PORT:-8501} --server.enableWebsocketCompression=false --server.headless true"]