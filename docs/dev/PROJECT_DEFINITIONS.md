# Project Definition: InkPads

## Project Overview
InkPads is a specialized derivative (skew) of [inkpads](https://github.com/the-mongols/redesigned-guacamole).

## Core Objective
To provide a high-performance, tournament-grade toolkit for player analysis, tactical planning, and real-time data insights.

## Project Requirements & Scope

### Core Requirements
The tool must provide the following capabilities:
- **Replay Visualization:** Parse World of Warships replay files and export them as **video files**.
- **Tactical Display:**
    - Show both teams with ship names and health bars (including Repair Party recoverable HP).
    - Visualize projectiles (shells) and torpedoes.
    - Display in-game ribbons and medal progress.
    - Display capture points with status, progress, and team point totals.
- **Discord Integration:** A Discord bot interface allowing users to interact with the tool and trigger replay processing.
- **Maintenance:** Committed maintenance for a minimum of one year.

### Licensing & Attribution
- **Public Repository:** Hosted publicly on GitHub.
- **License:** [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
- **Copyright:** Set to `Wargaming.net`.
- **Attribution:** "This project was developed at Wargaming's request for the community."

### Desired Features (Non-Mandatory)
- **Minimap Annotations:** Ability to "write" or draw on the minimap for tactical explanations.
- **Multiperspective Sync:** Merging and syncing two replays from the same match (e.g., opposing team perspectives) into a single visualization.
- **Tournament Integration:** Compatibility/Integration with platforms like [WoWs-Tournaments](https://wows-tournaments.com/).
- **Tournament Integration:** Compatibility/Integration with platforms like [WoWs-Tournaments](https://wows-tournaments.com/).

---

### Target Audience
- International Tournament Competitors
- Competitive Clan Players
- Standard World of Warships Enthusiasts

### Key References
- Base Project: [landaire/inkpads](https://github.com/the-mongols/redesigned-guacamole)
- Goal: Tournament-level competitive advantage and tactical analysis.

---

## Technical Setup (Local)
### Repository Status
- [x] Git Initialized
- [x] GitHub Remote Connected (`the-mongols/redesigned-guacamole`)
- [x] GitHub CLI Authorized (`gh` verified)

### Development Environment
- Language: (Likely Rust, based on upstream)
- Build System: (Likely Cargo)
