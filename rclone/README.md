# File Transfers and Storage Automation with Rclone

## Overview
This repository contains the complete configuration, verification, and automation scripts for managing high-reliability file transfers between local filesystems and S3-compatible object storage using **Rclone** and **MinIO**.

---

## Requirements & Implementation
- **Environment:** Local S3-compatible storage via Dockerized MinIO (`quay.io/minio/minio`).
- **Configuration-Free Execution:** All S3 operations execute without a persistent `rclone.conf` file, utilizing environment variables and `--config /dev/null`.
- **Large File Reliability:** Tested with 100 MB and 1 GB files, bandwidth limits (`--bwlimit 25M`), concurrency limits (`--transfers 4`), and interrupted transfer recovery.
- **Data Safety:** Tested `rclone check` integrity and `--dry-run` deletion detection to prevent data loss during synchronization.
- **Automation:** Reusable Bash automation script `transfer.sh` supporting `copy` and `sync`, logging, and exit code signaling.

---

## Quickstart & Reproduction

### 1. Start Local S3 Storage (MinIO)
```bash
docker compose up -d
docker ps | grep local-minio
