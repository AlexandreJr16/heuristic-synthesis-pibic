## ADDED Requirements

### Requirement: Same Degradation Mechanisms as the Reference Run
The system SHALL degrade maps with the five mechanisms of `codigo/run-referencia-2026-03/src/map.cpp` (Radial, Linear, Sparse, Organic, Stochastic), with the same parameters (radius, length, density, cell count), the same attempt limit and the same sequence of `rand()` calls, changing only the point where a cell is blocked.

#### Scenario: Rules disabled reproduce the reference run
- **WHEN** rules R1 and R2 are disabled
- **THEN** for every map, seed and pattern, the degraded grid SHALL have the same hash as the grid produced by the reference `degradaMapa*` functions.

#### Scenario: Seeded cumulative state
- **WHEN** a pattern is applied with `grid = original; srand(seed)` and levels 10% -> 20% -> 30%
- **THEN** every cell blocked at a level SHALL remain blocked at the next level
- **AND** running again with the same map, seed and pattern SHALL produce the same grid hash at every level.

### Requirement: R1 - Protected Endpoints
The system SHALL never block a cell that is the start or the goal of any pair in the map's `.scen` file.

#### Scenario: Blocking an endpoint
- **WHEN** a mechanism tries to block a cell that is an endpoint of some pair
- **THEN** the cell SHALL stay free
- **AND** the cell SHALL be counted once in `rejeitadas_r1` and the attempt in `tentativas_r1`.

### Requirement: R2 - Preserved Connectivity
The system SHALL block a cell only if blocking it does not split the 4-connected component it belongs to. Components that already exist in the original map SHALL stay as they are: the rule forbids creating new disconnections, not joining components that were already separate.

#### Scenario: Local test decides
- **WHEN** the free neighbors of the cell form at most one contiguous run (with an orthogonal neighbor) on the 3x3 ring around it
- **THEN** the cell SHALL be blocked without a global search.

#### Scenario: Local test is inconclusive
- **WHEN** the free neighbors form two or more such runs
- **THEN** the system SHALL run a bidirectional BFS with early stop between one neighbor of the first run and one neighbor of each other run, with the cell already blocked
- **AND** if any search fails, the cell SHALL be freed again, act as a passage, and be counted once in `rejeitadas_r2` and the attempt in `tentativas_r2`.

#### Scenario: Linear obstacle crossing a corridor
- **WHEN** a linear obstacle would close a corridor
- **THEN** the rejected cell SHALL remain free, so the obstacle becomes a wall with a door.

### Requirement: R3 - Blockage Target and Its Record
The system SHALL ask each mechanism, at each level, for the absolute missing amount (`(int)(S * level) - cells already blocked`, with `S` the free cells of the original map), with the reference attempt limit, and SHALL record what was reached.

#### Scenario: Target not reached
- **WHEN** rejections prevent a mechanism from reaching the target within the attempt limit
- **THEN** the run SHALL continue with the level as reached
- **AND** `degradacao_v2_resumo.csv` SHALL record, per map, seed, pattern and level, `pct_atingido`, `rejeitadas_r1`, `rejeitadas_r2`, `tentativas_r1` and `tentativas_r2`.

### Requirement: Per-Level Validation That Aborts
The system SHALL validate every degraded level before measuring it, and SHALL abort the run if any check fails.

#### Scenario: Level checks
- **WHEN** a level has been generated
- **THEN** every protected cell SHALL be free (R1)
- **AND** no original component SHALL have cells in two new components, and the number of components SHALL not increase (R2)
- **AND** the blocked cells SHALL contain those of the previous level (cumulative)
- **AND** every pair connected in the original map SHALL have start and goal in the same component.

#### Scenario: Pairs chosen per level
- **WHEN** the A* runs on a degraded level
- **THEN** the valid pairs SHALL be computed on that level, not reused from another level
- **AND** under R1 and R2 they SHALL be exactly the pairs connected in the original map, and their count SHALL be recorded in `pares_validos`.

#### Scenario: Negative control
- **WHEN** the validation receives a grid degraded by the reference functions
- **THEN** it SHALL fail.

### Requirement: Baseline Checked Against the Reference Run
The system SHALL recompute, on the original map, the A* expansions and path lengths of Manhattan, the synthesized formula and the memory heuristic (10, 20, 50 and 100 pivots, in the order of `main.cpp:147-191`), and SHALL abort if any of them differs from `resultados_base.csv` of the reference run.

#### Scenario: Baseline mismatch
- **WHEN** any expansion count or path length differs from the reference CSV
- **THEN** the run SHALL stop with an error and write no output for that map and seed.
