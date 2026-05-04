# InkPads Ecosystem: Pitch Prototype & Vision Roadmap

This document defines the goals for the **3-Day Proof-of-Concept (PoC)**. This is a "Pitch Prototype" designed to demonstrate the vision of the InkPads ecosystem running locally on a development machine.

> **Current Phase**: Pitch Prototype / Proof-of-Concept.
> **Deployment Target**: Local machine (demo environment). Future state targets Wargaming VPS.

---

## 1. The Prototype Vision: "The Pitch"

The goal of this sprint is to create a working demonstration of "Sabermetrics for WoWs." It merges the established stats logic of InkPads-CB with the deep data extraction of InkPads-Renderer.

### Components for the Demo
1.  **INKPADS - CB (Reference UI)**:
    - The existing Cloudflare-hosted webapp serves as the visual and logic reference.
    - For the PoC, we will utilize its code/framework to build a **Local Prototype Dashboard**.
2.  **INKPADS - RENDERER (Local Engine)**:
    - Runs as a local binary on this machine.
    - Provides the MP4 video generation and the raw packet data for the demo.

---

## 2. Core Concepts: The "Eureka" Demo

The pitch centers on visualizing positional data on a grid to prove its value to broadcasters and analysts.

- **The Grid System**: Mapping game coordinates to the A-J / 1-10 system.
- **Heatmap Proof-of-Concept**: A visual demonstration of ship pathing (e.g., "Where does the DD go on Spawn X?") generated from actual replay data.
- **Holistic Analysis**: Showing a combined view of "Match Result" (Ladder Data) and "Match Flow" (Replay Positioning).

---

## 3. Local Orchestration (The "Glue")

Since we are not on a VPS, we need a local orchestrator to handle the demo flow:
- **Intake**: A local Discord bot or a simple file-watcher.
- **Process**: Automating the call to `minimap_renderer.exe` and a custom **Data Extractor** tool.
- **Output**: Serving the result to a local web UI or a Discord channel.

---

## 4. User Experience Tiers (PoC Scope)

### Tier 1: The Common User (Discord Bot Demo)
- **Goal**: Show a replay going in and a video coming out.
- **Demo**: A local Discord bot receives a file, triggers the renderer, and posts the MP4.

### Tier 2: The Tactical Analyst (Web Portal Demo)
- **Goal**: Show the "Submarine Terminal" UI hosting a replay with markup potential.
- **Demo**: A local web page (simulating the InkPads portal) that displays a rendered video and an overlay of extracted data/heatmaps.

---

## 5. Development Pillars (3-Day Sprint)

### Pillar A: Local Discord Bot & Orchestrator
- Scaffold a local bot to handle the intake loop.
- Focus on the "Happy Path": Replay → Render → Local Delivery.

### Pillar B: Local Prototype Dashboard
- Create a lightweight local web server (e.g., Node.js/Vite) using the InkPads-CB aesthetic.
- Embed the rendered video and demonstrate "markup" potential (static or interactive).

### Pillar C: Data Extraction & Grid Mapping
- Script the extraction of position data from a test replay.
- Map those coordinates to the map grid (A1, B5, etc.) to generate a PoC heatmap image.

---

## 6. Project Ground Rules

1.  **Local-First**: Optimize for execution on *this* machine. No external deployment required for the demo.
2.  **As-Is Video**: Use the standard renderer style for the video; focus branding on the **Web Wrapper**.
3.  **CPU First**: Reliable rendering is better than fast GPU rendering for a demo.
4.  **KISS**: Hardcode where necessary to prove the concept within the 3-day window.

---

## 7. Immediate Next Steps (PoC Focus)

- [ ] **Extraction**: Extract `(x, y, time)` from our test replay (`Salem_25_sea_hope.wowsreplay`).
- [ ] **Mapping**: Write a small script to translate those (x, y) coordinates to map grid squares.
- [ ] **Bot**: Scaffold a basic Discord bot to trigger the `minimap_renderer.exe` command.
- [ ] **Web**: Create a local `index.html` with the "Submarine Terminal" CSS to host the demo video.
