# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Create a non-root user for security
RUN groupadd --gid 1001 auberge \
 && useradd --uid 1001 --gid auberge --shell /bin/bash --create-home auberge

WORKDIR /app

# Install Python dependencies first (layer-cache friendly)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY aubergeRP/ ./aubergeRP/
COPY frontend/ ./frontend/

# Data directory lives on a volume — create the mount point
RUN mkdir -p /data && chown auberge:auberge /data

# Switch to the non-root user
USER auberge

ENV AUBERGE_DATA_DIR=/data

EXPOSE 8000

CMD ["uvicorn", "aubergeRP.main:app", "--host", "0.0.0.0", "--port", "8000"]
