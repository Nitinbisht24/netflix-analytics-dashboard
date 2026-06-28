# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# System deps for matplotlib/reportlab font handling (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build the analytics DB + recommender index at image build time so the
# container starts instantly (no cold-start delay on first request).
RUN python -c "from core import database, recommender; database.build_db(force=True); recommender.build()"

EXPOSE 5000
ENV PORT=5000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "120", "app:create_app()"]
