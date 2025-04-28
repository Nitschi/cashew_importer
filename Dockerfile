FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY src/ /app/src/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the application
ENTRYPOINT ["python", "src/main.py"]
