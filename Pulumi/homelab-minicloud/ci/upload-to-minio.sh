#!/bin/bash

set -e

# Point mc to MinIO (keep --insecure here)
mc alias set local https://minio.local minioadmin minioadmin --insecure

# Create the bucket (add --insecure to bypass cert check)
mc mb local/static-site --insecure || true

# Set public policy (add --insecure again)
mc anonymous set download local/static-site --insecure

# Upload static website files (add --insecure again)
mc cp --recursive ../static-site/ local/static-site --insecure

echo "✅ Static site uploaded to MinIO!"
