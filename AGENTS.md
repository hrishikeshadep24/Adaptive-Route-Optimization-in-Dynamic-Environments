# Project Rules for Adaptive Route Optimization

## Non-Negotiable Rules

1. **Before any work**, read `docs/MASTER_BLUEPRINT.md`, `docs/PHASE_PLAN.md`, `docs/CHANGELOG.md`, `docs/OPEN_QUESTIONS.md` and inspect the repo.

2. **Work ONLY on the phase the user names**. Never implement future phases.

3. **Where the two documents disagree** on phase numbering/content, `docs/PHASE_PLAN.md` (detailed plan) wins.

4. **Never silently change** the mathematical model, objective, metrics, or experimental protocol. Propose changes in `docs/CHANGELOG.md` and wait for approval.

5. **Never fabricate** benchmark values, statistical significance, or performance claims. Never hard-code research results into the UI; the UI reads generated result files.

6. **If an assumption is missing**, STOP and record it in `docs/OPEN_QUESTIONS.md` instead of guessing.

7. **Small testable modules**. Every algorithm has unit tests and is deterministic under a fixed seed.

8. **Correctness first**, then measure, then optimize bottlenecks.

9. **Every experiment records** configuration, seed, commit hash, runtime environment and raw metrics.

10. **Never compare algorithms on different instances/event sequences**.

11. **Keep `docs/CHANGELOG.md` updated** for meaningful architecture or protocol changes.

12. **Finish every phase** by running the full test suite and writing `docs/evidence/phaseN_evidence.md` containing the commands run and their ACTUAL outputs.

13. **Project is application-neutral**: delivery/courier is only an interpretation. No live GPS, traffic/map/weather APIs, RL, deep learning, drones, production dispatch, mobile app, or cloud deployment.

14. **No team member/doc may claim** "we invented dynamic routing / 2-opt / insertion". The contribution is a controlled, reproducible empirical study.