# Automated Server Provisioning with Cloud-Init

## Overview
This repository contains the complete configuration, verification, and documentation for automating the end-to-end provisioning of an Ubuntu 24.04 Linux server using cloud-init and QEMU, without manual SSH intervention or paid cloud infrastructure.

## Requirements & Implementation
- Environment: Ubuntu 24.04 LTS Server provisioned locally via QEMU with KVM hardware acceleration.
- Packages: docker.io, git, curl, ffmpeg.
- User: Non-root user testpress with passwordless sudo and docker group membership.
- Directory: /opt/testpress created with /opt/testpress/app.env.
- Application: Dockerized HTTP service listening on port 8080, returning 'Hello from Testpress!'.
- Process Management: Managed by systemd (testpress-app.service) with auto-restart on boot and crash recovery (Restart=always).

## Instructions to Reproduce
1. Install prerequisites:
   sudo apt update && sudo apt install -y qemu-system-x86 qemu-utils cloud-image-utils wget
   sudo chmod 666 /dev/kvm && sudo usermod -aG kvm $USER

2. Download image & create seed disk:
   wget -O ubuntu-24.04.img https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
   qemu-img resize ubuntu-24.04.img 10G
   cloud-localds seed.img cloud-init.yaml meta-data

3. Launch QEMU VM:
   qemu-system-x86_64 -m 2048 -smp 2 -enable-kvm -cpu host \
     -drive file=ubuntu-24.04.img,format=qcow2 -drive file=seed.img,format=raw \
     -netdev user,id=net0,hostfwd=tcp::8080-:8080,hostfwd=tcp::2222-:22 \
     -device virtio-net-pci,netdev=net0 -display none -daemonize

## Verification & Outputs
1. HTTP Endpoint:
   curl -i http://localhost:8080
   Output: HTTP/1.1 200 OK, Hello from Testpress!

2. System Verification:
   ssh -p 2222 testpress@localhost "cat /opt/testpress/app.env && docker ps && id"
   Output: user in docker/sudo, testpress-http healthy, app.env present.

3. Reboot Resilience:
   ssh -p 2222 testpress@localhost "sudo reboot"
   curl http://localhost:8080 automatically resumes after boot.

## Cloud-Init Execution Stages
1. Generator / Local: Detects local datasource (NoCloud seed.img). (Every boot)
2. Network (Init): Processes meta-data/user-data, sets hostname, creates users. (First boot only)
3. Config: Disk mounts, partitioning, module configuration. (First boot only)
4. Final: Installs packages, writes files, runs runcmd. (First boot only)

Idempotency: Cloud-init tracks instance-id in /var/lib/cloud/instance/. On reboot, if instance-id matches previous-instance-id, all first-boot stages are skipped.
