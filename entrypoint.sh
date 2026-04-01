#!/bin/sh
# Fix ownership of mounted storage volumes (HF Storage Buckets mount as root)
# and set up cache symlink — all as root before dropping privileges.
if [ -d "/data" ] && [ -n "$PERSISTENT_DATA_DIR" ]; then
    mkdir -p /data/cache/audio /data/cache/images
    chown -R wadjet:wadjet /data

    # Copy pre-generated story images to persistent storage (skip existing)
    if [ -d "/app/app/static/cache/images" ]; then
        cp -n /app/app/static/cache/images/story_*.png /data/cache/images/ 2>/dev/null || true
    fi

    # Replace ephemeral cache dir with symlink to persistent volume
    if [ -d "/app/app/static/cache" ] && [ ! -L "/app/app/static/cache" ]; then
        rm -rf /app/app/static/cache
        ln -s /data/cache /app/app/static/cache
        chown -h wadjet:wadjet /app/app/static/cache
    fi
fi

# Drop to non-root user and exec the server
exec su wadjet -s /bin/sh -c "exec uvicorn app.main:app --host 0.0.0.0 --port 7860"
