# HomeLab MiniCloud

![HomeLab MiniCloud](https://source.unsplash.com/random/1200x400/?server,cloud)

> A comprehensive guide to setting up your own mini cloud environment using Pulumi and Docker with MinIO object storage.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Setting Up Pulumi](#setting-up-pulumi)
  - [Project Setup](#project-setup)
  - [MinIO Deployment](#minio-deployment)
- [NGINX Configuration](#nginx-configuration)
  - [SSL Certificate Generation](#ssl-certificate-generation)
  - [Reverse Proxy Setup](#reverse-proxy-setup)
- [Static Site Deployment](#static-site-deployment)
  - [Uploading to MinIO](#uploading-to-minio)
  - [Website Configuration](#website-configuration)
- [Troubleshooting](#troubleshooting)
- [Cleanup](#cleanup)

## 📑 Overview

HomeLab MiniCloud provides a local, containerized environment that mimics cloud services. This project uses:

- **Pulumi**: Infrastructure as Code (IaC) tool to define and deploy infrastructure
- **Docker**: For containerization of services
- **MinIO**: S3-compatible object storage
- **NGINX**: As a reverse proxy with SSL support

## 🔧 Prerequisites

Ensure you have the following installed on your system:

```bash
sudo apt update && sudo apt install -y \
  docker.io \
  python3.10 \
  python3.10-venv \
  curl \
  unzip
```

## 🚀 Installation

### Setting Up Pulumi

1. Install Pulumi:

```bash
curl -fsSL https://get.pulumi.com | sh
export PATH=$PATH:$HOME/.pulumi/bin
```

2. Add Pulumi to your shell configuration:

```bash
echo 'export PATH=$HOME/.pulumi/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### Project Setup

1. Create the project directory:

```bash
mkdir -p ~/Home-Lab/Pulumi/homelab-minicloud
cd ~/Home-Lab/Pulumi/homelab-minicloud
```

2. Initialize a Pulumi project:

```bash
pulumi new python -y
```

3. Install dependencies:

```bash
cd infra
pip install -r requirements.txt
```

4. Or use a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

5. Install Pulumi Docker provider:

```bash
pip install pulumi_docker
```

### MinIO Deployment

1. Edit `infra/__main__.py` with the following code:

```python
"""A Python Pulumi program"""

import pulumi
import pulumi_docker as docker

# MinIO credentials
minio_access_key = "minioadmin"
minio_secret_key = "minioadmin"

# Create a shared Docker network
network = docker.Network("homelab-network", name="homelab-network")

# Pull MinIO image
minio_image = docker.RemoteImage("minio-image",
    name="minio/minio:latest",
    keep_locally=True
)

# Run MinIO container
minio_container = docker.Container("minio-container",
    image=minio_image.repo_digest,
    name="minio",
    ports=[
        docker.ContainerPortArgs(internal=9000, external=9000),
        docker.ContainerPortArgs(internal=9001, external=9001),
    ],
    envs=[
        f"MINIO_ROOT_USER={minio_access_key}",
        f"MINIO_ROOT_PASSWORD={minio_secret_key}"
    ],
    command=["server", "/data", "--console-address", ":9001"],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/home/arjun//minio/data",
            container_path="/data",
        )
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
)

pulumi.export("minio_container_name", minio_container.name)
```

2. Deploy MinIO:

```bash
cd infra
pulumi up
```

3. Verify deployment:

```bash
docker ps
```

Expected output:
```
CONTAINER ID   IMAGE       COMMAND     STATUS    PORTS           NAMES
xxxxxxxxxxxx   minio/minio "..."       Up       0.0.0.0:9000->9000/tcp   minio
```

4. Access MinIO:
   - URL: [http://localhost:9001](http://localhost:9001)
   - Username: `minioadmin`
   - Password: `minioadmin`

## 🔒 NGINX Configuration

### SSL Certificate Generation

1. Create an OpenSSL config file (`cert.conf`):

```ini
[req]
default_bits       = 2048
distinguished_name = req_distinguished_name
req_extensions     = req_ext
x509_extensions    = v3_ca
prompt             = no

[req_distinguished_name]
C  = IN
ST = Karnataka
L  = Bangalore
O  = HomeLab
OU = IT
CN = minio.local

[req_ext]
subjectAltName = @alt_names

[v3_ca]
subjectAltName = @alt_names
basicConstraints = critical, CA:true

[alt_names]
DNS.1 = minio.local
```

2. Generate the certificate and key:

```bash
openssl req -x509 -nodes -days 365 \  
  -newkey rsa:2048 \  
  -keyout minio.key \  
  -out minio.crt \  
  -config cert.conf
```

### Reverse Proxy Setup

#### Option 1: Subpath Routing

Configure NGINX to serve both MinIO console and static site under different paths:

```nginx
server {
    listen 443 ssl;
    server_name minio.local;

    ssl_certificate     /etc/nginx/ssl/minio.crt;
    ssl_certificate_key /etc/nginx/ssl/minio.key;

    # MinIO Console
    location / {
        proxy_pass http://minio:9001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static Site
    location /static/ {
        proxy_pass http://minio:9000/static-site/;
        proxy_ssl_verify off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Access:
- MinIO Console: `https://minio.local/`
- Static Site: `https://minio.local/static/`

#### Option 2: Subdomain Split

1. Update `/etc/hosts`:

```
127.0.0.1 minio.local static.local
```

2. Configure NGINX with separate server blocks:

```nginx
# Static site on static.local
server {
    listen 443 ssl;
    server_name static.local;

    ssl_certificate     /etc/nginx/ssl/minio.crt;
    ssl_certificate_key /etc/nginx/ssl/minio.key;

    location / {
        proxy_pass http://minio:9000/static-site/;
        proxy_ssl_verify off;
    }
}

# MinIO Console on minio.local
server {
    listen 443 ssl;
    server_name minio.local;

    ssl_certificate     /etc/nginx/ssl/minio.crt;
    ssl_certificate_key /etc/nginx/ssl/minio.key;

    location / {
        proxy_pass http://minio:9001/;
    }
}
```

Access:
- MinIO Console: `https://minio.local/`
- Static Site: `https://static.local/`

3. Reload NGINX configuration:

```bash
sudo nginx -t  # Check config
sudo systemctl reload nginx
```

## 🌐 Static Site Deployment

### Uploading to MinIO

Create a script (`ci/upload-to-minio.sh`):

```bash
#!/bin/bash

set -e

mc alias set local https://minio.local minioadmin minioadmin --insecure
mc mb local/static-site --insecure || true
mc anonymous set download local/static-site --insecure
mc cp --recursive ../static-site/ local/static-site --insecure

echo "✅ Static site uploaded to MinIO!"
```

### Handling Self-Signed Certificates

#### Option 1: Use `--insecure` Flag (Development Only)
The script above uses the `--insecure` flag to bypass certificate validation.

#### Option 2: Trust the Self-Signed Certificate (Recommended)

For Ubuntu/Debian:
```bash
sudo cp minio.crt /usr/local/share/ca-certificates/minio.crt
sudo update-ca-certificates
```

For RedHat-based systems:
```bash
sudo cp minio.crt /etc/pki/ca-trust/source/anchors/minio.crt
sudo update-ca-trust extract
```

### Website Configuration

Configure MinIO for website hosting:

```bash
mc alias set local https://minio.local
mc anonymous set download local/static-site
mc website set local/static-site --index index.html --error index.html
```

## 🔍 Troubleshooting

### Issue: Missing Pulumi Docker Module

If you see: `ModuleNotFoundError: No module named 'pulumi_docker'`

Solution:
1. Ensure you're in the `infra` directory
2. Activate the virtual environment: `source venv/bin/activate`
3. Reinstall the Pulumi Docker provider: `pip install pulumi_docker`
4. Verify installation: `pip list | grep pulumi_docker`
5. Try running `pulumi up` again

### Issue: Pulumi Passphrase Prompt

If Pulumi continually asks for a passphrase:

```bash
export PULUMI_CONFIG_PASSPHRASE="your-passphrase"
```

## 🧹 Cleanup

To destroy all resources created by Pulumi:

```bash
pulumi destroy
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.