# Experiment Protocol

## Instance Generation
- Seeded random generation for reproducibility
- Configurable: size, spatial distribution, edge weights
- Hidden complete instance generated first, then partially revealed

## Dynamic Event Model
- Initial subset of vertices revealed for initial solution
- Subsequent events reveal new vertices at controlled intervals
- Event sequence determined by seed

## Strategies Under Test
1. Greedy Insertion Repair
2. Insertion + 2-opt Local Search
3. Stronger Re-optimization (TBD in Phase 2/4)

## Computational Budget
- Single primary budget definition (wall-clock OR evaluation count)
- Same budget applied to all strategies for fair comparison
- Budget rationale documented before main campaign

## Execution Protocol
1. Generate instance with seed S
2. Generate event sequence with seed S
3. Build initial solution on initial vertex subset
4. For each event:
   - Apply each strategy under budget
   - Record: route cost, update time, disruption, feasibility
5. Repeat for all seeds per condition
6. Aggregate and analyze

## Reproducibility Requirements
- Config file + seed + commit hash = exact reproduction
- Raw results stored with full metadata
- Batch runner produces identical output on re-run