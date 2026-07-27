FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if any are needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy dataset and serialized model files to root (referenced relative to root)
COPY intent_classifier_v1.joblib .
COPY tfidf_vectorizer_v1.joblib .
COPY answers.json .

# Copy application layers
COPY backend/ backend/
COPY frontend/ frontend/

EXPOSE 8081

ENV PORT=8081
ENV FLASK_ENV=production

# Run with Gunicorn, setting the entry point to run:app (within backend module)
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 "backend.run:app"
