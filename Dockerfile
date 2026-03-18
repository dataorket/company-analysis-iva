FROM python:3.13-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir cryptography

# Copy application code
COPY app/ app/
COPY static/ static/
COPY ingest.py .
COPY data/ data/
COPY chroma_db/ chroma_db/

# Suppress tokenizer parallelism warnings
ENV TOKENIZERS_PARALLELISM=false
ENV PYTHONUNBUFFERED=1

# Default port (Render uses $PORT env var, HuggingFace uses 7860)
ENV PORT=7860
EXPOSE 7860

# Run the app — uses $PORT from environment
CMD python -m app.main
