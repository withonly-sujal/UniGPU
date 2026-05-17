FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create uploads directory
RUN mkdir -p uploads

EXPOSE 8000

# Start Uvicorn on Railway's dynamic PORT (fallback to 8000 for local/dev)
# --proxy-headers: trust X-Forwarded-For / X-Forwarded-Proto from reverse proxies
# --workers 2: two async workers (safe for a 1-2 vCPU VPS)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --proxy-headers --forwarded-allow-ips '*'"]
