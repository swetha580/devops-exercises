# Rclone Commands Used & Explanations

## 1. Local Operations
- `rclone lsf source_dir/`: Lists files and directories in standard format.
- `rclone ls source_dir/`: Lists all files recursively with their sizes.
- `rclone copy source_dir/ dest_dir/`: Copies missing/modified files; preserves extra destination files.
- `rclone check source_dir/ dest_dir/`: Checks data integrity using hashes and sizes without transferring.
- `rclone move source_dir/temp_move.txt dest_dir/`: Copies file to destination and deletes it from source.

## 2. Configuration-Free S3 (MinIO) Operations
- Ephemeral remote setup using environment variables:
  `RCLONE_CONFIG_LOCALMINIO_TYPE=s3`, `RCLONE_CONFIG_LOCALMINIO_PROVIDER=Minio`, `RCLONE_CONFIG_LOCALMINIO_ENDPOINT=http://127.0.0.1:9000`, `RCLONE_CONFIG_LOCALMINIO_ACCESS_KEY_ID=minioadmin`, `RCLONE_CONFIG_LOCALMINIO_SECRET_ACCESS_KEY=minioadminpassword`.
- `rclone mkdir LOCALMINIO:testpress-bucket --config /dev/null`: Creates an S3 bucket without rclone.conf.
- `rclone copy source_dir/docs LOCALMINIO:testpress-bucket/docs --config /dev/null`: Uploads files to S3.
- `rclone copy source_dir/assets/testfile_100mb.dat LOCALMINIO:testpress-bucket/assets/ --progress --config /dev/null`: Uploads 100 MB test file.
- `rclone ls LOCALMINIO:testpress-bucket/ --config /dev/null`: Lists objects in S3 bucket.
- `rclone copy LOCALMINIO:testpress-bucket/docs ./downloaded_docs --config /dev/null`: Downloads objects from S3.
- `rclone copy LOCALMINIO:testpress-bucket LOCALMINIO:testpress-backup --config /dev/null`: Copies directly between S3 buckets.
- `rclone deletefile LOCALMINIO:testpress-bucket/docs/summary.pdf --config /dev/null`: Deletes an object from S3.

## 3. Transfer Reliability & Safety
- `rclone copy source_dir/videos/lecture_recording_1gb.bin LOCALMINIO:testpress-bucket/videos/ --transfers 4 --bwlimit 25M --retries 3 --stats 1s --config /dev/null`: Uploads 1 GB file with 25 MB/s bandwidth cap and 4 concurrent transfers.
- `rclone sync source_dir/docs LOCALMINIO:testpress-bucket/docs/ --dry-run -v --config /dev/null`: Simulates sync and warns about deleted files before applying changes.
- `./transfer.sh <source> <dest> [copy|sync]`: Reusable automation script supporting logging and dry-run safety.
