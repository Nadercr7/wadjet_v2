# --- Build stage: TailwindCSS v4 ---
FROM node:22-alpine AS css-builder
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY app/static/css/input.css app/static/css/
COPY app/templates/ app/templates/
RUN npx @tailwindcss/cli -i app/static/css/input.css -o app/static/dist/styles.css --minify

# --- Runtime stage ---
FROM python:3.13-slim
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r wadjet && useradd -r -g wadjet -d /app -s /sbin/nologin wadjet

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app/ app/

# CSS build output from first stage
COPY --from=css-builder /build/app/static/dist/styles.css app/static/dist/styles.css

# Static assets (JS, fonts, images)
COPY app/static/js/ app/static/js/
COPY app/static/fonts/ app/static/fonts/
COPY app/static/images/ app/static/images/

# ML models (uint8 ONNX + metadata only; .dockerignore excludes full-precision)
COPY models/ models/

# Runtime data (embeddings, metadata, text, translation; .dockerignore excludes training datasets)
COPY data/ data/

# Ensure cache directories are writable by non-root user
RUN mkdir -p app/static/cache/audio app/static/cache/images data \
    && chown -R wadjet:wadjet app/static/cache data

USER wadjet

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
