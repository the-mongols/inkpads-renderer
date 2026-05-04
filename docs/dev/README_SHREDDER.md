# Forensic Tactical Engine 2.0 (The Shredder)
## Proof of Concept: Trident Match (KITE vs HHGA)

The Shredder 2.0 is a high-fidelity telemetry analytics pipeline designed to reconstruct competitive match events into surgical tactical reports. It reconciles raw game-client assets with production-grade coordinate projection logic.

### 🛠 Core Architecture
- **ForensicEngine**: The primary orchestrator that dispatches telemetry packets from `replayshark` to specialized extractors.
- **WorldState**: The "Source of Truth" that maintains roster identities, map bounds, and ship species resolution.
- **ForensicAnalyst**: An intelligence layer that clusters ship movement into "Occupancy Pockets" (Anchors) using a dynamic dwell-time threshold.
- **ScoutingRenderer**: A high-resolution (2048x2048) rendering engine that overlays tactical heat, capture zones, and ship labels onto raw game assets.

### 📐 Mathematical Principles
#### 1. The Definitive Projection (Parity with Video Renderer)
The engine utilizes the **Native 760px Grid** transformation found in the Rust rendering pipeline:
- `X_pixel = ((World_X * (760 / Space_Size)) + 380) * (Output_Size / 760)`
- `Y_pixel = ((-World_Z * (760 / Space_Size)) + 380) * (Output_Size / 760)`
This ensures 100% pixel-perfect synchronization between ship telemetry and map geometry.

#### 2. Capture Zone Scaling
The engine translates "Normalized Local" coordinates (-500 to 500) from `InteractiveZone` packets into true **World Meters** using a map-specific scaling factor derived from the `space.settings` XML.

### 📡 Tactical Intelligence Features
- **Anchor Detection**: Automatically identifies where enemy ships "dwell" or "shimmy" during the Opening Gambit (0-7:00).
- **Ghost Intel**: Explicitly flags ships that remained unspotted during the analysis window as **[GHOST ALERT]**, turning a lack of data into a tactical warning.
- **Label De-confliction**: Automatically stacks ship names vertically when tactical blobs overlap to maintain legibility in high-density zones.
- **Edge-Awareness**: Intelligent label positioning that prevents clipping on the map borders.

### 🚀 Usage
1. **Extraction**: Run `test_v2_engine.py` to shred a `.wowsreplay` and generate the `forensic_audit_v2.json`.
2. **Rendering**: Run `generate_final_report.py` to produce the final labeled scouting report (`scouting_report_HHGA_Trident.png`).

---
*Checkpoint reached: 2026-04-30. PoC Verified on Trident Map (41_Conquest).*
