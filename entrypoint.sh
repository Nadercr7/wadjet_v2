#!/bin/sh
# Fix ownership of mounted storage volumes (HF Storage Buckets mount as root)
if [ -d "/data" ]; then
    chown -R wadjet:wadjet /data 2>/dev/null || true
fi

# Drop to non-root user and exec the server
exec su wadjet -s /bin/sh -c "exec uvicorn app.main:app --host 0.0.0.0 --port 7860"
