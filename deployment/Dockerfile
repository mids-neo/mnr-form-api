# Use Python 3.11 slim base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for PDF processing and OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgdal-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY deployment/requirements-minimal.txt .

# Install core Python dependencies first
RUN pip install --upgrade pip setuptools wheel

# Install essential dependencies
RUN pip install --no-cache-dir -r requirements-minimal.txt

# Install heavy dependencies separately with more resources
RUN pip install --no-cache-dir opencv-python-headless>=4.8.0

# Install optional dependencies that might fail
RUN pip install --no-cache-dir easyocr>=1.7.0 || echo "EasyOCR installation failed, continuing without it"
RUN pip install --no-cache-dir google-cloud-vision>=3.4.0 || echo "Google Cloud Vision installation failed, continuing without it"
RUN pip install --no-cache-dir boto3>=1.26.0 || echo "Boto3 installation failed, continuing without it"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/uploads data/outputs static/templates

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with the startup script
CMD ["python", "run_server.py"]