# HomeLab MiniCloud - Pulumi Setup Guide

This README provides step-by-step instructions for setting up a **mini cloud environment** using **Pulumi** and **Docker** with MinIO. 

## 📌 Prerequisites
Ensure the following dependencies are installed:

```bash
sudo apt update && sudo apt install -y \
  docker.io \
  python3.10 \
  python3.10-venv \
  curl \
  unzip
```

### Install Pulumi
```bash
curl -fsSL https://get.pulumi.com | sh
export PATH=$PATH:$HOME/.pulumi/bin
```
To persist Pulumi in your shell, add this to `~/.bashrc` or `~/.zshrc`:
```bash
echo 'export PATH=$HOME/.pulumi/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

## 🚀 Setup Instructions
### 1️⃣ Create Project Directory
```bash
mkdir -p ~/Home-Lab/Pulumi/homelab-minicloud
cd ~/Home-Lab/Pulumi/homelab-minicloud
```

### 2️⃣ Initialize Pulumi Project
```bash
pulumi new python -y
```
This creates a new Pulumi project with Python as the language.

### 3️⃣ Install Dependencies
```bash
cd infra
pip install -r requirements.txt
```
If using a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4️⃣ Install Pulumi Docker Provider
```bash
pip install pulumi_docker
```

### 5️⃣ Define MinIO Infrastructure
Edit `infra/__main__.py` and add:

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

### 6️⃣ Deploy MinIO
```bash
cd infra
pulumi up
```
This will:
- Preview the deployment
- Ask for confirmation
- Deploy MinIO in a Docker container

To verify, run:
```bash
docker ps
```
Expected output:
```bash
CONTAINER ID   IMAGE       COMMAND     STATUS    PORTS           NAMES
xxxxxxxxxxxx   minio/minio "..."       Up       0.0.0.0:9000->9000/tcp   minio
```

### 7️⃣ Access MinIO
Visit: [http://localhost:9000](http://localhost:9000)

Credentials:
- **Username:** `minioadmin`
- **Password:** `minioadmin`

## 🛠 Troubleshooting
### Issue: `ModuleNotFoundError: No module named 'pulumi_docker'`
#### Solution:
1. Ensure you are inside the `infra` directory.
2. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```
3. Reinstall Pulumi Docker provider:
   ```bash
   pip install pulumi_docker
   ```
4. Verify installation:
   ```bash
   pip list | grep pulumi_docker
   ```
5. Try running `pulumi up` again.

### Issue: Pulumi asks for a passphrase
Pulumi encrypts secrets. If prompted:
```bash
Enter your passphrase to unlock config/secrets:
```
You can set an environment variable to avoid re-entering:
```bash
export PULUMI_CONFIG_PASSPHRASE="your-passphrase"
```

### Cleanup Resources
To destroy the infrastructure:
```bash
pulumi destroy
```


# Setting Up NGINX and Static Site

## 1. Generate a Self-Signed Certificate with SAN

### Create an OpenSSL config file (cert.conf):
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

### Generate the certificate and key:
```bash
openssl req -x509 -nodes -days 365 \  
  -newkey rsa:2048 \  
  -keyout minio.key \  
  -out minio.crt \  
  -config cert.conf
```

This generates:
- `minio.crt` (certificate)
- `minio.key` (private key)

## 2. Update NGINX Container to Use the New Certificate

Replace the old `minio.crt` and `minio.key` in:
```bash
/home/arjun/Home-Lab/Pulumi/homelab-minicloud/infra/nginx/ssl/
```
Then re-run `pulumi up` to restart the stack with the SAN-enabled certificate.

## 3. Handling Self-Signed Certificate Issues

### Option 1: Use `--insecure` Flag (Not Recommended for Production)
Update your script in `ci/upload-to-minio.sh` :
```bash
#!/bin/bash

set -e

mc alias set local https://minio.local minioadmin minioadmin --insecure
mc mb local/static-site --insecure || true
mc anonymous set download local/static-site --insecure
mc cp --recursive ../static-site/ local/static-site --insecure

echo "✅ Static site uploaded to MinIO!"
```

### Option 2: Trust the Self-Signed Certificate (Recommended)

#### Ubuntu/Debian:
```bash
sudo cp minio.crt /usr/local/share/ca-certificates/minio.crt
sudo update-ca-certificates
```

#### RedHat-based:
```bash
sudo cp minio.crt /etc/pki/ca-trust/source/anchors/minio.crt
sudo update-ca-trust extract
```
Restart your terminal and try the script **without** `--insecure`.

## 4. Serve Static Site Automatically

### Using `mc`:
```bash
mc alias set local https://minio.local
mc anonymous set download local/static-site
mc website set local/static-site --index index.html --error index.html
```
Now access your site at:
```bash
https://minio.local/static-site/
```

## 5. Setting Up NGINX as a Reverse Proxy

### Option 1: Subpath Routing (`/static` and `/`)
Edit NGINX config:
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
- Static site: `https://minio.local/static/`
- MinIO Console: `https://minio.local/`

### Option 2: Subdomain Split (`static.local` & `minio.local`)
Update `/etc/hosts`:
```bash
127.0.0.1 minio.local static.local
```
Edit NGINX config:
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
- Static site: `https://static.local`
- MinIO Console: `https://minio.local`

## 6. Reload NGINX
```bash
sudo nginx -t  # Check config
sudo systemctl reload nginx
```

Now your static site and MinIO console are correctly routed!



 
 

---
This guide ensures a smooth setup for deploying MinIO using Pulumi. 🚀

