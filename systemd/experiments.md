# Linux Process Management & systemd — Experiments Log

This document records the 10 hands-on experiments executed to investigate process lifecycle, signal handling, systemd service management, crash resilience, resource constraints, and reboot persistence.

---

## Experiment 1: Running Process Inspection

[evidence/01_running_process.png]

1. **Action**:
   Started `app.py` directly in the user session (`python3 app.py &`). Identified and inspected the process using `pgrep -fl app.py`, `ps aux | grep app.py`, and `pstree -p`.

2. **Expectation**:
   The process should be listed in the process table with a unique Process Identifier (PID), running in user space with its state reported as `S` (interruptible sleep).

3. **Observation**:
   `pgrep` and `ps` displayed the running process with its exact PID, user ownership (`swetha`), and CPU/memory footprint. `pstree` clearly mapped the parent-child hierarchy from `bash` to `python3`.

4. **Explanation**:
   Linux maintains a kernel process table exposing state information through `/proc`. Tools like `ps` read `/proc/<PID>/stat` and `/proc/<PID>/status` to report runtime metrics and relationship trees.

---

## Experiment 2: Graceful Shutdown (SIGTERM)

[evidence/02_graceful_shutdown.png]

1. **Action**:
   Sent signal 15 (SIGTERM) to the running process using `kill -15 <PID>` (or `kill <PID>`).

2. **Expectation**:
   The Python application should intercept `SIGTERM` via its registered signal handler, log a clean shutdown message, flush open buffers, and terminate with exit code `0`.

3. **Observation**:
   The application trapped the signal, logged:
   `[SIGNAL] Received SIGTERM (15). Performing graceful shutdown...`
   and exited cleanly without abrupt data loss.

4. **Explanation**:
   `SIGTERM` is the standard polite request for termination. Unlike uncatchable signals, it allows the process to execute custom cleanup handlers, close open sockets/files, and exit gracefully before termination.

---

## Experiment 3: Forced Termination (SIGKILL)

[evidence/03_forced_termination.png]

1. **Action**:
   Sent signal 9 (SIGKILL) to the running process using `kill -9 <PID>`.

2. **Expectation**:
   The process should terminate instantaneously without executing any shutdown handlers or logging an exit message.

3. **Observation**:
   The process was immediately evicted from the process table. No cleanup messages appeared in the logs, and the terminal output showed `Killed`.

4. **Explanation**:
   `SIGKILL` (signal 9) cannot be caught, handled, or ignored by user-space applications. The Linux kernel immediately reclaims the process's page tables and resources without giving the program an opportunity to run cleanup code.

---

## Experiment 4: systemd Service Unit Management

[evidence/04_systemd_service.png]

1. **Action**:
   Installed `testpress-worker.service` into `/etc/systemd/system/`, reloaded the daemon (`sudo systemctl daemon-reload`), and started the service (`sudo systemctl start testpress-worker.service`). Inspected runtime state using `systemctl status testpress-worker.service`.

2. **Expectation**:
   systemd should spawn the worker process under the designated non-root user (`swetha`), load environment variables from `testpress-worker.env`, and report state `Active: active (running)`.

3. **Observation**:
   The service initialized cleanly. `systemctl status` confirmed active running state, showing Main PID, cgroup placement, memory/CPU consumption, and recent journald logs.

4. **Explanation**:
   systemd parses unit files and uses the Linux `clone()` system call with cgroup constraints to launch services in isolation. It acts as PID 1, supervising process health and routing standard output/error to `systemd-journald`.

---

## Experiment 5: Automatic Restart after Unexpected Crash

[evidence/05_automatic_restart.png]

1. **Action**:
   Simulated an unexpected failure by abruptly killing the service's main PID using `sudo kill -9 <PID>`. Monitored service recovery via `systemctl status`.

2. **Expectation**:
   systemd should detect the non-zero/abrupt exit, observe `Restart=always` (or `on-failure`), wait `RestartSec=3s`, and automatically spawn a new process instance with a new PID.

3. **Observation**:
   The original process died. systemd logged `Main process exited, code=killed, status=9/KILL` and restarted the worker 3 seconds later under a fresh PID.

4. **Explanation**:
   systemd uses kernel process tracking and cgroup monitoring. When an unmanaged exit occurs, systemd evaluates the unit's restart policy, waits the defined `RestartSec` backoff, and re-executes `ExecStart`.

---

## Experiment 6: Crash Investigation via journalctl

[evidence/06_crash_investigation.png]

1. **Action**:
   Triggered an application crash using `touch /tmp/crash_worker`. Investigated the failure trail and restart sequence using `journalctl -u testpress-worker.service -n 25 --no-pager`.

2. **Expectation**:
   `journalctl` should preserve the complete diagnostic timeline, showing the crash trigger, error messages, exit status, and systemd's recovery actions.

3. **Observation**:
   Logs revealed:
   - Application detecting crash condition: `[CRASH] Trigger detected! Exiting with status 1...`
   - systemd logging failure: `testpress-worker.service: Main process exited, code=exited, status=1/FAILURE`
   - systemd scheduling recovery: `Scheduled restart job, restart counter is at X.`

4. **Explanation**:
   `systemd-journald` captures all standard output, standard error, and kernel lifecycle events for the unit slice, ensuring persistent, structured audit trails even when applications crash unexpectedly.

---

## Experiment 7: Invalid Configuration Diagnostic

[evidence/07_invalid_config.png]

1. **Action**:
   Configured a non-existent binary path in `ExecStart` (e.g. `/usr/bin/python3_nonexistent`), reloaded the daemon, and attempted to start the service.

2. **Expectation**:
   The service should fail to start immediately, reporting a startup failure with an informative exit code.

3. **Observation**:
   systemd reported `Active: failed (Result: exit-code)` with `status=203/EXEC`. `journalctl` explicitly stated:
   `Failed at step EXEC spawning /usr/bin/python3_nonexistent: No such file or directory`

4. **Explanation**:
   Exit code `203/EXEC` is systemd's internal diagnostic code indicating that the `execve()` system call failed because the executable binary path specified in `ExecStart` could not be located or executed.

---

## Experiment 8: Repeated Crash Rate Limiting

[evidence/08_repeated_crashes.png]

1. **Action**:
   Configured `CRASH_AFTER_CYCLES=1` in the environment file and observed systemd's behavior over successive restart cycles.

2. **Expectation**:
   After exceeding `StartLimitBurst=5` failures within `StartLimitIntervalSec=30s`, systemd should stop attempting restarts to protect host system stability.

3. **Observation**:
   systemd restarted the worker repeatedly until reaching the threshold, then entered a safety lock:
   `testpress-worker.service: Start request repeated too quickly.`
   `testpress-worker.service: Failed with result 'exit-code'.`
   `Failed to start Testpress Background Worker Service.`

4. **Explanation**:
   Restart loops consume substantial CPU, disk I/O, and log space. Systemd enforces rate limiting through `StartLimitIntervalSec` and `StartLimitBurst` to prevent a crashing service from causing a Denial-of-Service (DoS) condition on the host.

---

## Experiment 9: Resource Limits & OOM Killer

[evidence/09_resource_limits.png]

1. **Action**:
   Configured `MemoryMax=50M`, `MemorySwapMax=0`, and `CPUQuota=50%` in the service unit. Configured `ALLOCATE_MEMORY_MB=100` in `testpress-worker.env` to force the worker to request memory beyond the 50 MB cgroup threshold. Restarted the service.

2. **Expectation**:
   The process should allocate memory until reaching the 50 MB ceiling, at which point the Linux kernel cgroup memory controller should terminate the process via the Out-Of-Memory (OOM) killer.

3. **Observation**:
   After consuming ~54 MB, the process was immediately killed. `systemctl status` reported:
   `Active: failed (Result: oom-kill)`
   `Process: ... (code=killed, signal=KILL)`
   `journalctl` logged:
   `testpress-worker.service: A process of this unit has been killed by the OOM killer.`

4. **Explanation**:
   systemd configures Linux Control Groups (cgroups v2) to enforce resource boundaries. With `MemorySwapMax=0`, swap fallback is forbidden. The moment the process's resident set size (RSS) breaches `MemoryMax`, the kernel's cgroup memory controller dispatches an uncatchable `SIGKILL` directly to the offending process.

---

## Experiment 10: Reboot Persistence

[evidence/10_reboot_persistence.png]

1. **Action**:
   Verified that the service was enabled (`systemctl is-enabled` returned `enabled`). Shut down the Linux environment (`wsl.exe --shutdown`). Relaunched the environment, and verified system boot time (`uptime -s`) and service status without running manual start commands.

2. **Expectation**:
   Because the service has `WantedBy=multi-user.target` in its `[Install]` block and is enabled, systemd should automatically launch the service as part of the multi-user boot sequence.

3. **Observation**:
   The system booted at `00:14:25` (`uptime -s`). `systemctl status` showed that systemd launched `testpress-worker.service` 3 seconds later (`00:14:28`) under PID `229`, running healthy with ongoing heartbeat cycles.

4. **Explanation**:
   Running `systemctl enable` creates a symlink in `/etc/systemd/system/multi-user.target.wants/`. During boot, when systemd activates `multi-user.target`, it discovers the symlink and automatically spawns the unit, ensuring seamless reboot resilience without human intervention.
