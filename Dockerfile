# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Create a non-root user for security
RUN groupadd --gid 1001 auberge \
 && useradd --uid 1001 --gid auberge --shell /bin/bash --create-home auberge

WORKDIR /app

# Install Python dependencies first (layer-cache friendly)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Data directory lives on a volume — create the mount point
# Source (aubergeRP/ frontend/) is bind-mounted at runtime; see docker/docker-compose.yml
RUN mkdir -p /data && chown auberge:auberge /data

# Switch to the non-root user
USER auberge

ENV AUBERGE_DATA_DIR=/data

EXPOSE 8123

CMD ["uvicorn", "aubergeRP.main:app", "--host", "0.0.0.0", "--port", "8123"]
