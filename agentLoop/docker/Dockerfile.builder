FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Node.js 20.x LTS (required for Vite and modern tooling)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    build-essential \
    wget \
    unzip \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install MongoDB Community Edition (Ubuntu 22.04 compatible)
RUN curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor \
    && echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list \
    && apt-get update \
    && apt-get install -y mongodb-org \
    && rm -rf /var/lib/apt/lists/*

# Create MongoDB data and log directories and set permissions
RUN mkdir -p /data/db /var/log/mongodb && \
    chown -R mongodb:mongodb /data/db /var/log/mongodb

# Configure MongoDB to bind to 0.0.0.0 (accessible from host)
RUN echo "net:\n  bindIp: 0.0.0.0" >> /etc/mongod.conf

# Install Cursor CLI
RUN curl https://cursor.com/install -fsS | bash

# Ensure local bin is in PATH
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

CMD ["tail", "-f", "/dev/null"]

