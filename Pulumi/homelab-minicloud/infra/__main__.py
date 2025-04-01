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

# Pull NGINX image
nginx_image = docker.RemoteImage("nginx-image",
    name="nginx:latest",
    keep_locally=True
)

# Run NGINX container
nginx_container = docker.Container("nginx-container",
    image=nginx_image.repo_digest,
    name="nginx",
    ports=[
        docker.ContainerPortArgs(internal=443, external=443),
    ],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/home/arjun/Home-Lab/Pulumi/homelab-minicloud/infra/nginx/default.conf",
            container_path="/etc/nginx/conf.d/default.conf",
        ),
        docker.ContainerVolumeArgs(
            host_path="/home/arjun/Home-Lab/Pulumi/homelab-minicloud/infra/nginx/ssl/minio.crt",
            container_path="/etc/nginx/ssl/minio.crt",
        ),
        docker.ContainerVolumeArgs(
            host_path="/home/arjun/Home-Lab/Pulumi/homelab-minicloud/infra/nginx/ssl/minio.key",
            container_path="/etc/nginx/ssl/minio.key",
        )
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
)

pulumi.export("nginx_container_name", nginx_container.name)
