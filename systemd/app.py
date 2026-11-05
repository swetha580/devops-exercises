#!/usr/bin/env python3
import os
import sys
import time
import signal
import resource

# Environment Variable Configurations
APP_ENV = os.getenv("APP_ENV", "production")
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "5"))
CRASH_AFTER_CYCLES = int(os.getenv("CRASH_AFTER_CYCLES", "0"))
CRASH_TRIGGER_FILE = os.getenv("CRASH_TRIGGER_FILE", "/tmp/crash_worker")
ALLOCATE_MEMORY_MB = int(os.getenv("ALLOCATE_MEMORY_MB", "0"))

running = True

def get_memory_usage_mb():
    # Resident Set Size (RSS) in MB
    usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return usage_kb / 1024.0

def signal_handler(signum, frame):
    global running
    sig_name = signal.Signals(signum).name
    print(f"\n[SHUTDOWN] Received signal {sig_name} ({signum}). Initiating graceful shutdown...", flush=True)
    time.sleep(1)
    print("[SHUTDOWN] Active tasks saved. Cleanup complete. Exiting cleanly (exit 0).", flush=True)
    running = False
    sys.exit(0)

# Register Signal Handlers for Graceful Shutdown
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def main():
    pid = os.getpid()
    print("==================================================", flush=True)
    print(f"[*] Testpress Background Worker Started", flush=True)
    print(f"[*] PID: {pid} | ENV: {APP_ENV}", flush=True)
    print(f"[*] Heartbeat Interval: {HEARTBEAT_INTERVAL}s", flush=True)
    print("==================================================", flush=True)

    # Memory allocation test (for Resource Limits experiment)
    if ALLOCATE_MEMORY_MB > 0:
        print(f"[MEMORY] Continuously allocating memory to exceed systemd MemoryMax (50M)...", flush=True)
        memory_hog = []
        while True:
            memory_hog.append(os.urandom(15 * 1024 * 1024))
            print(f"[MEMORY] Consumed: {get_memory_usage_mb():.2f} MB", flush=True)
            time.sleep(0.5)

    cycle = 0
    while running:
        cycle += 1
        mem_mb = get_memory_usage_mb()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now_str}] [HEARTBEAT] Cycle #{cycle} | Worker PID: {pid} | Memory: {mem_mb:.2f} MB | Status: HEALTHY", flush=True)

        # Trigger crash if configured to crash after N cycles
        if CRASH_AFTER_CYCLES > 0 and cycle >= CRASH_AFTER_CYCLES:
            print(f"[CRASH] Simulating unexpected failure after cycle {cycle}. Exiting with code 1!", file=sys.stderr, flush=True)
            sys.exit(1)

        # Trigger crash if trigger file exists
        if os.path.exists(CRASH_TRIGGER_FILE):
            print(f"[CRASH] Detected trigger file '{CRASH_TRIGGER_FILE}'. Crashing process immediately!", file=sys.stderr, flush=True)
            try:
                os.remove(CRASH_TRIGGER_FILE)
            except OSError:
                pass
            sys.exit(2)

        time.sleep(HEARTBEAT_INTERVAL)

if __name__ == "__main__":
    main()
