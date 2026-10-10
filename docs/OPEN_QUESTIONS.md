# Open Questions

## Phase 2: Algorithmic Specification
- [ ] Single-route dynamic TSP vs multi-route VRP? (Default: single-route TSP first)
- [ ] Precise definition of route disruption metric
- [ ] Exact event model: single vertex at a time, or batches?
- [ ] Are there time windows or other constraints on vertices?
- [ ] Is the graph fully connected Euclidean, or general weighted graph?

## Phase 6: Experimental Framework
- [ ] Primary computational budget: wall-clock time vs evaluation count?
- [ ] Number of seeds per condition (start with 10, adjust after pilot)
- [ ] Exact instance sizes for pilot vs full campaign
- [ ] Random instance distribution (uniform, clustered, mixed)

## Phase 7: Analysis
- [ ] Statistical tests to use (paired t-test, Wilcoxon, bootstrap CI?)
- [ ] Effect size measures to report
- [ ] Held-out validation protocol for adaptive selector

## Phase 8: Adaptive Selection (Conditional)
- [ ] What state features are available at decision time?
- [ ] Selection overhead budget
- [ ] Oracle definition for regret calculation