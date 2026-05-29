# Architecture Prototype Bee — Structure Reducer

> *Architecture is reduction, not construction.*

## Problem

You have a vague idea in your head ("I want a roguelike with deep combat"). It is "将出未出" — not yet formed. Before writing code, you need to reduce it to irreducible constraints.

## First Principle

**Code is expensive. Structure is cheap.** If you start coding before the structure is clear, you will refactor endlessly. The LLM should force you to strip away ambiguity until only constraints remain.

## Behavior

1. **Interrogate** — ask what, not how
   - "What is the goal?" not "What framework should I use?"
   - "What must be true?" not "How do I implement it?"
2. **Reduce** — keep asking "why" until you hit constraints that cannot split further
   - Stop when the answer is "because that's the physical reality" or "because that's the user need"
   - If a constraint can be split, it is not a core constraint
3. **Estimate** — sketch algorithmic complexity (Big O intuition) for each module
   - Time vs space tradeoffs
   - Which operations will dominate at scale?
4. **Output** — module decomposition as an orthogonal basis
   - High cohesion: each module does one thing
   - Low coupling: modules communicate through narrow interfaces
   - Each module's interface is its contract

## Exogenous Pheromone Format

File: `~/.worker-bee/arch/<project>.md`

```markdown
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
```

## Orthogonal Basis = High Cohesion + Low Coupling

In linear algebra, an orthogonal basis is a set of vectors where:
- Each vector points in a unique direction (no redundancy)
- They span the entire space (complete coverage)
- You can combine them to express any point in the space

In architecture:
- **Each module = a basis vector** — it handles one dimension of the problem
- **No overlap** — if two modules share responsibility, the basis is not orthogonal
- **Complete coverage** — every requirement is owned by some module
- **Composable** — modules combine through interfaces (dot products)

## Skill Contract

See `worker_bee/skills/architect.md`

## Why It Works

- The LLM does not design — it **interrogates** and records
- Big O estimation forces early thinking about bottlenecks
- Tradeoff section captures decisions before they are forgotten
- The architecture doc is a **contract** between human and LLM: this is the structure, code comes after

## Use Cases

- Game prototypes that need structural clarity before implementation
- Research systems with complex data flows
- Any project where "vague idea → code" is too big a leap
