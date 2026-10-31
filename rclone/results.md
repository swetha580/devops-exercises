# Rclone Experimental Results & Demonstration Answers

This report documents the experimental observations, transfer metrics, failure recoveries, and answers to the demonstration questions for Exercise 2.

---

## 1. Experimental Results & Observations

| Experiment | Parameters / Flags | Measured Outcome | Observations |
| :--- | :--- | :--- | :--- |
| **Local Copy & Check** | `rclone copy`, `rclone check` | 6 matching files, 0 differences | Rclone matched all local files based on size and timestamp. |
| **Local Move** | `rclone move` | Source file deleted, dest file created | File was moved atomically; source file was removed upon verification. |
| **100 MB S3 Upload** | `--progress --config /dev/null` | 100 MB in 1.4s (92.8 MB/s) | MinIO handled the upload over local loopback at high throughput. |
| **1 GB Throttled Upload** | `--bwlimit 25M --transfers 4` | 1 GB in 46.6s (22.2 MB/s) | Bandwidth was capped accurately without exceeding the 25 MB/s threshold. |
| **Interrupted Transfer** | Interrupted at 19% (192 MB), resumed | Resumed and finished in 11.6s (90.1 MB/s) | Rclone validated data integrity and uploaded the object without corrupting storage. |
| **Sync Safety (`--dry-run`)** | `--dry-run -v` | Logged: `legacy_certificate.pdf: Skipped delete` | Identified and logged destructive deletions without touching destination data. |
| **Data Integrity Check** | `rclone check` | 2 differences found, 1 matching file | Detected missing file in destination and unexpected extra file in source. |
| **Automation Script** | `./transfer.sh <src> <dst> sync` | Exit code 0, logged to `transfer.log` | Automated dry-run verification ran before syncing, ensuring safe execution. |

---

## 2. Answers to Demonstration Questions

### Q1: What happens when `rclone copy` is executed twice with the same source and destination?
- **Answer:** It does **nothing on the second run** (0 files transferred, 0 bytes moved).
- **Explanation:** By default, Rclone compares file sizes and modification timestamps (`mtime`). Because destination files already match the source attributes, Rclone skips transferring them.

### Q2: What happens if a file exists at the destination but not at the source when `rclone sync` runs?
- **Answer:** **The file is permanently deleted from the destination.**
- **Explanation:** `rclone sync` enforces that the destination is strictly identical to the source. If an asset is missing at the source, `sync` assumes it was deleted and removes it from the destination.
- **Safety Best Practice:** Always run with `--dry-run` or use `--backup-dir <path>` to archive deleted files into a rollback directory.

### Q3: How does rclone determine whether a file needs to be transferred?
- **Answer:**
  1. **Default Mode (Local/Filesystem):** Compares **Modification Timestamp (`mtime`)** and **File Size**.
  2. **Object Storage Mode (S3/MinIO):** Compares **File Size** and **MD5/ETag Hash**.
  3. **Custom Flags:** `--checksum` forces MD5/SHA1 hash verification; `--size-only` checks only file sizes.

### Q4: Can rclone transfer data directly between two S3 providers without downloading it to the local machine?
- **Answer:**
  - **Between two different S3 providers (e.g., AWS S3 to MinIO/Cloudflare R2):** **No.** The data must stream through the machine running Rclone. However, Rclone streams it directly through memory without buffering to the local hard disk.
  - **Within the same S3 provider/bucket:** **Yes.** Rclone uses the S3 `CopyObject` API call for native server-side copying, requiring zero local network throughput.

### Q5: What happens when a network connection is interrupted halfway through a 1 GB upload?
- **Answer:**
  - Files larger than the chunk size (default 5 MB) are uploaded via **S3 Multipart Upload**.
  - During the failure, Rclone invokes low-level retries (`--low-level-retries 10`).
  - If the process terminates, incomplete multipart parts remain on the bucket until aborted or cleaned by lifecycle policies.
  - On restarting `rclone copy`, Rclone checks if the final object exists; if incomplete, it restarts the transfer and replaces the object atomically upon completion.

### Q6: How would you securely execute rclone from a Celery worker without maintaining an `rclone.conf` file?
- **Answer:** Through **Environment Variables** injected into the Celery worker process:
  ```python
  import os, subprocess

  env = os.environ.copy()
  env["RCLONE_CONFIG_S3REMOTE_TYPE"] = "s3"
  env["RCLONE_CONFIG_S3REMOTE_PROVIDER"] = "Minio"
  env["RCLONE_CONFIG_S3REMOTE_ENDPOINT"] = "[http://127.0.0.1:9000](http://127.0.0.1:9000)"
  env["RCLONE_CONFIG_S3REMOTE_ACCESS_KEY_ID"] = settings.AWS_ACCESS_KEY_ID
  env["RCLONE_CONFIG_S3REMOTE_SECRET_ACCESS_KEY"] = settings.AWS_SECRET_ACCESS_KEY

  # Execute without touching disk storage
  subprocess.run(
      ["rclone", "copy", local_file_path, "S3REMOTE:testpress-bucket/assets/", "--config", "/dev/null"],
      env=env,
      check=True
  )
