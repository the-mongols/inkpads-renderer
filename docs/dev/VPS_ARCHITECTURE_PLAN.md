# VPS Architecture & Deployment Strategy: Forensic Tactical Engine

This document outlines the requirements and architectural changes necessary to transition the **Forensic Tactical Engine** from a "Local-First" development environment to a production-grade **Headless VPS** environment.

---

## 1. Data Minimization (The "Headless Asset" Problem)

### Current Assumption
The renderer expects a full World of Warships installation (`~100GB`) to access `GameParams.data`, maps, and ship silhouettes.

### VPS Optimization
- **Asset Stripping**: Identify and isolate the minimum required `.pkg` files (primarily maps, UI icons, and GameParams).
- **Portable Data Bundle**: Create a compact directory structure (`~500MB - 1GB`) that the renderer can use in place of a full game path.
- **Version Management**: Implement a system to swap GameParams versions dynamically based on the replay version.

---

## 2. Headless Encoding Strategy

### Current Assumption
Rendering relies on local GPU acceleration (NVENC/VAAPI) for high-speed video production.

### VPS Optimization
- **CPU Fallback**: Standard VPS instances lack dedicated GPUs. The FFmpeg pipeline must be tuned for high-efficiency CPU encoding.
- **FFmpeg Presets**: Utilize `libx264` with `fast` or `veryfast` presets to maintain acceptable render times (targeting < 2 minutes for a standard 20-minute match).
- **Resource Limits**: Implement CPU pinning or thread-limiting to prevent a single render process from starving the Discord bot's heartbeat.

---

## 3. Scalability & Concurrency (The Producer/Consumer Model)

### Current Assumption
The Discord bot spawns a subprocess and waits for completion. Multiple simultaneous requests will likely crash the system.

### VPS Optimization
- **Task Queuing**: Implement a "Producer/Consumer" architecture using **Redis** and **Celery** (or a simple internal queue).
- **Concurrency Control**: 
    - **Producer**: Discord Bot receives files and assigns a `JobID`.
    - **Consumer**: A pool of workers (size limited by VPS cores) picks up jobs sequentially.
- **Status Updates**: The bot should provide real-time feedback to the user (e.g., "Queue Position: 2").

---

## 4. Containerization (Docker)

### Current Assumption
Environment is managed manually (Python, Rust, FFmpeg, Fonts).

### VPS Optimization
- **Dockerization**: Wrap the entire stack into a Docker image.
    - **Base**: Ubuntu/Debian with FFmpeg and CJK fonts installed.
    - **Layer 1**: Compiled Rust `minimap-renderer` binary.
    - **Layer 2**: Python Discord bot and dependencies.
- **Environment Parity**: Ensures that coordinate mapping, font rendering, and video muxing are identical regardless of the underlying VPS provider.

---

## 5. Storage & Ephemeral Management

### Current Assumption
Replays and MP4s are stored in `temp/` indefinitely.

### VPS Optimization
- **Automatic Reaper**: Implement a TTL (Time-To-Live) for all files in the `temp/` and `output/` directories.
- **Cleanup Trigger**: 
    - Files are deleted immediately after successful Discord upload.
    - A fallback cron job clears any files older than 6 hours to prevent disk-fill.

---

## 6. Remote Monitoring & Observability

### VPS Optimization
- **Health Checks**: Implement a simple heartbeat or `/ping` command that checks the health of the renderer subprocess.
- **Logging**: Aggregate logs from the Rust binary and Python bot for remote debugging.
- **Error Reporting**: Send critical failure alerts (e.g., "GPU Error" or "OOM Kill") to a dedicated admin channel.
