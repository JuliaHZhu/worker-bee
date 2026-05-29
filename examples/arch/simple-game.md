# Architecture: Simple Roguelike

## Goal
A turn-based roguelike where combat depth comes from positional tactics, not stat grinding.

## Core Constraints
- **Constraint 1**: Must run at 60fps on a 2015 laptop (no GPU required)
- **Constraint 2**: Combat must be completable without leveling (skill-based)
- **Constraint 3**: Map generation must produce solvable dungeons (no soft-locks)

## Modules

### Map Generator
- **Responsibility**: Procedural dungeon layout + enemy placement
- **Interface**: Input (seed, difficulty), Output (tilemap, entity list)
- **Algorithm**: Cellular automata + A* solvability check
- **Complexity**: O(n²) for n×n grid, acceptable for n≤50
- **Dependencies**: None

### Combat Engine
- **Responsibility**: Turn resolution, line-of-sight, damage calculation
- **Interface**: Input (player action, entity state), Output (new state, events)
- **Algorithm**: BFS for LoS, event queue for turn order
- **Complexity**: O(e log e) for e entities
- **Dependencies**: Map Generator (reads tilemap)

### Renderer
- **Responsibility**: ASCII display with color
- **Interface**: Input (entity positions, tilemap), Output (terminal buffer)
- **Algorithm**: Double-buffered terminal output
- **Complexity**: O(n²) for n×n viewport
- **Dependencies**: Map Generator, Combat Engine

## Tradeoffs
- Chose ASCII over sprites: reduces art dependency, fits constraint 1
- Chose BFS over raycasting for LoS: simpler, deterministic, good enough for grid
