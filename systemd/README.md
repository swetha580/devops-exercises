# Testpress Background Worker Service (systemd)

A production-grade Python background worker managed natively with Linux systemd and cgroups v2, designed for reliable execution, graceful signal handling, automated failure recovery, and strict resource bounding.

---

## Architecture & Features

* **Application (`app.py`)**:
  * Continuous background heartbeat loop (default 5-second interval).
  * Graceful shutdown on `SIGTERM` (15) and `SIGINT` (2).
  * Simulated crash triggers via cycle count (`CRASH_AFTER_CYCLES`) or trigger files (`CRASH_TRIGGER_FILE`).
  * Dynamic memory allocation test harness (`ALLOCATE_MEMORY_MB`).
* **Environment Configuration (`testpress-worker.env.example`)**:
  * Externalized runtime settings loaded securely via systemd `EnvironmentFile`.
* **systemd Service Unit (`testpress-worker.service`)**:
  * Runs under a dedicated, unprivileged non-root user (`swetha`).
  * Automated recovery via `Restart=always` and `RestartSec=3s`.
  * Crash loop rate limiting via `StartLimitIntervalSec=30s` and `StartLimitBurst=5`.
  * Hard resource constraints via cgroups v2 (`MemoryMax=50M`, `MemorySwapMax=0`, `CPUQuota=50%`).
  * Full boot persistence via `WantedBy=multi-user.target`.
  * Centralized structured logging to `systemd-journald`.

---

## Project Structure

```text
systemd/
├── app.py                      # Background worker application
├── testpress-worker.env.example# Environment configuration template
├── testpress-worker.service    # systemd unit definition
├── experiments.md              # Documentation of all 10 experiments
├── README.md                   # Setup and usage guide
└── evidence/                   # Practical execution evidence screenshots
    ├── 01_running_process.png
    ├── 02_graceful_shutdown.png
    ├── 03_forced_termination.png
    ├── 04_systemd_service.png
    ├── 05_automatic_restart.png
    ├── 06_crash_investigation.png
    ├── 07_invalid_config.png
    ├── 08_repeated_crashes.png
    ├── 09_resource_limits.png
    └── 10_reboot_persistence.png
```

---

## Setup & Deployment Instructions

### 1. Configure the Environment
Create your local environment file from the template:
```bash
cp testpress-worker.env.example testpress-worker.env
chmod 600 testpress-worker.env
```

### 2. Install and Enable the systemd Service
```bash
# Copy unit file to systemd directory
sudo cp testpress-worker.service /etc/systemd/system/testpress-worker.service

# Reload systemd manager configuration
sudo systemctl daemon-reload

# Enable service to start automatically on boot
sudo systemctl enable testpress-worker.service

# Start the service
sudo systemctl start testpress-worker.service
```

### 3. Service Management Commands
```bash
# Check service status
systemctl status testpress-worker.service

# View live application logs
journalctl -u testpress-worker.service -f

# View the last 30 log lines
journalctl -u testpress-worker.service -n 30 --no-pager

# Stop or restart the service
sudo systemctl stop testpress-worker.service
sudo systemctl restart testpress-worker.service
```

---

## Questions for the Demonstration

### 1. What is the difference between SIGTERM and SIGKILL?
* **SIGTERM (Signal 15)** is the standard polite termination signal. It can be caught, handled, or blocked by the application, allowing it to complete in-flight transactions, flush logs, and close connections before exiting.
* **SIGKILL (Signal 9)** is handled directly by the Linux kernel and cannot be caught, handled, or ignored. It terminates the process immediately without running any cleanup code.

### 2. Why doesn't nohup provide the same reliability as systemd?
`nohup` only prevents a process from receiving `SIGHUP` when the controlling terminal disconnects. It does not:
* Restart the process if it crashes or gets killed.
* Restart the process when the server reboots.
* Provide resource constraints (cgroups) or health monitoring.
* Provide centralized log management, status reporting, or dependency management.

### 3. What happens when a service crashes repeatedly?
When a service crashes repeatedly within a short window, systemd's rate limiting protects host resources:
* If restarts exceed `StartLimitBurst` within `StartLimitIntervalSec`, systemd enters a failed state (`Start request repeated too quickly`) and stops restarting the unit until an administrator investigates and resets it.

### 4. What is the difference between restarting a process and restarting a service?
* **Restarting a process** kills and relaunches a single PID in user space, often without cgroup isolation or supervision.
* **Restarting a service** instructs systemd (PID 1) to execute a structured lifecycle transition: sending stopping signals to the entire cgroup slice, cleaning up transient state, re-reading environment variables, and re-executing `ExecStart` under specified user and security boundaries.

### 5. What happens to child processes when a systemd service is stopped?
systemd places all processes spawned by a service into a dedicated cgroup slice. When the service stops, systemd sends `SIGTERM` (followed by `SIGKILL` if `TimeoutStopSec` is breached) to **all processes** within that cgroup, completely eliminating orphaned child processes and rogue daemons.

### 6. How would you ensure a Celery worker finishes its current task before shutting down?
Configure systemd with:
* `KillSignal=SIGTERM`: Celery traps `SIGTERM` as a "warm shutdown", waiting for active tasks to complete while refusing new tasks.
* `TimeoutStopSec=300`: Gives the Celery worker sufficient time (e.g., 5 minutes) to finish long-running tasks before systemd resorts to `SIGKILL`.
