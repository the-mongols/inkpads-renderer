# InkPads Ecosystem: Technical Learnings & Evolution

This document serves as a synthesis of the knowledge, architectural decisions, and "eureka moments" captured during the development of the InkPads ecosystem (Webapp and Renderer).

## 1. Project Vision: "Sabermetrics for WoWs"
The core ambition behind InkPads is to provide a tournament-grade toolkit that moves beyond simple replay playback into data-driven tactical analysis.
- **The Heatmap Eureka Moment**: The long-term goal is to parse batches of `.wowsreplay` files to generate heatmaps of player pathing and positioning. This level of analysis (akin to Sabermetrics in Baseball) would fundamentally change the competitive landscape of World of Warships (Clan Battles, KOTS).
- **Dual-Perspective Sync**: A critical technical goal was achieving a "God's eye view" by synchronizing two replays from opposing perspectives of the same match.

## 2. InkPads-CB (The Webapp)
The webapp serves as the user's primary interface for data analysis and collaboration.

### UI/UX & Aesthetics
- **Submarine Terminal Aesthetic**: The design evokes a modern naval CIC/submarine terminal. Key elements:
    - **Sonar Sweep**: A radar-like animation on the login screen.
    - **Premium Themes**: High-contrast, sleek palettes like `matrix.css` (neon green) and `terminal.css` (muted olive).
    - **Compact Theme Picker**: A minimal "3-bubble" preview that expands on hover, maintaining a clean interface.
- **Onboarding & Help**:
    - **Auto-Intake (Token Scout Wizard)**: Crucial for user success. The UI was refined to a 750px width with centered tutorial videos for clarity.
    - **Context-Aware Help**: A dynamic system that swaps YouTube tutorial videos based on the user's current view (Login, Standard/Advanced/Battle Caller profiles, or Auto-Intake).

### Backend & Data (Cloudflare Workers + D1)
- **Data Collection**: The Wargaming API `ladder/battles` endpoint was optimized with `&limit=100` to fetch full history during sync.
- **Database Scaling**: D1 query limits were increased to 1000+ to support viewing full season records.
- **Security**: Admin login utilizes `INSERT OR REPLACE` to handle session persistence and prevent UNIQUE constraint lockouts.
- **Maintenance**: Strict management of `console.log` in Workers to avoid exceeding platform log limits.

## 3. InkPads-Render (The Renderer)
A high-performance Rust-based rendering engine.

### Architecture
- **Rendering Engine**: Built using Vulkan (WGPU) for hardware-accelerated video export.
- **Collaboration Protocol**: A custom protocol designed for real-time tactical planning and shared visualizations.
- **Resource Management**: Efficient handling of game-specific assets (3D models, textures) and map data.

## 4. Key Lessons Learned
1. **Onboarding is King**: The "Auto-Intake" button is the single point of failure for new users; its visibility and the accompanying tutorial are paramount.
2. **Dynamic Context Improves UX**: Help systems that "know" where the user is (via dynamic YouTube embedding) significantly reduce friction.
3. **Performance requires Guardrails**: Large data sets (like season-long clan battle histories) require careful DB indexing and query limit management from day one.
4. **Visual Identity Matters**: The "Submarine Terminal" vibe is a core part of the brand and should be carried through from the web UI to the renderer's GUI.

---
*This archive was created on 2026-04-27 as part of a codebase raze to prepare for the next evolution of InkPads.*
