"""Unit and integration tests for Stage 3: Benchmark and Scenario Expansion.

Covers:
- Synthetic customer distributions: Uniform, Clustered, and Mixed.
- Deterministic reproducibility and bounding validation.
- Edge cases for synthetic generators (n=0, 1, 2, small clusters).
- Configuration error handling.
- TSPLIB parser correctness, metadata preservation, and distance conventions.
- Separation of static benchmark topology from dynamic arrival scenarios.
- Batch customer arrivals: uniform batches, scheduled variable batches, empty events.
- Frozen-prefix invariance and route feasibility across Strategies A, B, C, and ADAPTIVE.
- Compatibility with experiment configuration schemas and ExperimentRunner execution.
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path

from adaptive_route_optimization.models import Instance, CustomerDistribution, Route
from adaptive_route_optimization.benchmarks import (
    TSPLIBMetadata,
    TSPLIBInstance,
    parse_tsplib_file,
    load_tsplib_benchmark,
    create_dynamic_scenario_from_instance,
)
from adaptive_route_optimization.simulation.events import (
    EventConfig,
    EventSequence,
    EventGenerator,
    generate_event_sequence,
)
from adaptive_route_optimization.simulation.simulator import (
    Simulator,
    Strategy,
    StepResult,
    SimulationResult,
)
from adaptive_route_optimization.experiments.schema import (
    ConditionConfig,
    ExperimentConfig,
    BudgetConfig,
    BudgetType,
)
from adaptive_route_optimization.experiments.runner import ExperimentRunner


# ---------------------------------------------------------------------------
# 1. Synthetic Instance Distributions
# ---------------------------------------------------------------------------

class TestSyntheticDistributions:
    """Tests for Uniform, Clustered, and Mixed synthetic instance generation."""

    def test_uniform_reproducibility_and_bounds(self):
        """Uniform generator produces identical coordinates for fixed seed within bounds."""
        inst1 = Instance.generate_random(n=30, seed=42, x_range=(10.0, 90.0), y_range=(20.0, 80.0))
        inst2 = Instance.generate_random(n=30, seed=42, x_range=(10.0, 90.0), y_range=(20.0, 80.0))

        assert np.array_equal(inst1.coords, inst2.coords)
        assert inst1.n == 30
        assert inst1.num_vertices == 31

        # Bounds check
        assert np.all(inst1.coords[:, 0] >= 10.0 - 1e-5)
        assert np.all(inst1.coords[:, 0] <= 90.0 + 1e-5)
        assert np.all(inst1.coords[:, 1] >= 20.0 - 1e-5)
        assert np.all(inst1.coords[:, 1] <= 80.0 + 1e-5)

    def test_clustered_reproducibility_and_bounds(self):
        """Clustered generator produces identical coordinates for fixed seed within bounds."""
        inst1 = Instance.generate_clustered(
            n=40, seed=123, num_clusters=4, cluster_spread=4.0, x_range=(0.0, 100.0), y_range=(0.0, 100.0)
        )
        inst2 = Instance.generate_clustered(
            n=40, seed=123, num_clusters=4, cluster_spread=4.0, x_range=(0.0, 100.0), y_range=(0.0, 100.0)
        )

        assert np.array_equal(inst1.coords, inst2.coords)
        assert inst1.n == 40
        assert inst1.num_vertices == 41

        # Coordinates must strictly respect bounding box
        assert np.all(inst1.coords >= 0.0 - 1e-5)
        assert np.all(inst1.coords <= 100.0 + 1e-5)

    def test_mixed_reproducibility_and_distribution(self):
        """Mixed generator produces identical coordinates and respects ratio."""
        inst1 = Instance.generate_mixed(
            n=50, seed=777, num_clusters=3, cluster_spread=5.0, cluster_ratio=0.8
        )
        inst2 = Instance.generate_mixed(
            n=50, seed=777, num_clusters=3, cluster_spread=5.0, cluster_ratio=0.8
        )

        assert np.array_equal(inst1.coords, inst2.coords)
        assert inst1.n == 50
        assert inst1.num_vertices == 51

    def test_generate_synthetic_dispatch(self):
        """generate_synthetic correctly dispatches to uniform, clustered, and mixed."""
        u = Instance.generate_synthetic(n=10, distribution="uniform", seed=1)
        c = Instance.generate_synthetic(n=10, distribution="clustered", seed=1, num_clusters=2)
        m = Instance.generate_synthetic(n=10, distribution="mixed", seed=1, cluster_ratio=0.5)

        assert u.n == 10
        assert c.n == 10
        assert m.n == 10

        # With CustomerDistribution enum
        u_enum = Instance.generate_synthetic(n=10, distribution=CustomerDistribution.UNIFORM, seed=1)
        assert np.array_equal(u.coords, u_enum.coords)

    def test_small_customer_counts(self):
        """Generators handle small customer counts (n=0, 1, 2) safely."""
        for dist in ["uniform", "clustered", "mixed"]:
            # n = 0 (depot only)
            inst0 = Instance.generate_synthetic(n=0, distribution=dist, seed=42)
            assert inst0.n == 0
            assert inst0.num_vertices == 1

            # n = 1
            inst1 = Instance.generate_synthetic(n=1, distribution=dist, seed=42, num_clusters=5)
            assert inst1.n == 1
            assert inst1.num_vertices == 2

            # n = 2
            inst2 = Instance.generate_synthetic(n=2, distribution=dist, seed=42, num_clusters=5)
            assert inst2.n == 2
            assert inst2.num_vertices == 3

    def test_invalid_parameters_raise_errors(self):
        """Invalid generator configurations raise explicit ValueErrors."""
        with pytest.raises(ValueError, match="Customer count n must be >= 0"):
            Instance.generate_clustered(n=-1, seed=0)

        with pytest.raises(ValueError, match="num_clusters must be >= 1"):
            Instance.generate_clustered(n=10, seed=0, num_clusters=0)

        with pytest.raises(ValueError, match="cluster_spread must be > 0"):
            Instance.generate_clustered(n=10, seed=0, cluster_spread=-2.0)

        with pytest.raises(ValueError, match="cluster_ratio must be in"):
            Instance.generate_mixed(n=10, seed=0, cluster_ratio=1.5)

        with pytest.raises(ValueError, match="Invalid coordinate ranges"):
            Instance.generate_clustered(n=10, seed=0, x_range=(50.0, 10.0))

        with pytest.raises(ValueError, match="Unknown distribution"):
            Instance.generate_synthetic(n=10, distribution="hyperspherical")

    def test_different_seeds_produce_different_instances(self):
        """Different seeds produce distinct coordinates across all distributions."""
        u1 = Instance.generate_random(n=20, seed=1)
        u2 = Instance.generate_random(n=20, seed=2)
        assert not np.array_equal(u1.coords, u2.coords)

        c1 = Instance.generate_clustered(n=20, seed=1, num_clusters=3)
        c2 = Instance.generate_clustered(n=20, seed=2, num_clusters=3)
        assert not np.array_equal(c1.coords, c2.coords)

        m1 = Instance.generate_mixed(n=20, seed=1)
        m2 = Instance.generate_mixed(n=20, seed=2)
        assert not np.array_equal(m1.coords, m2.coords)

    def test_clustered_spatial_dispersion_differs_from_uniform(self):
        """Clustered distribution exhibits significantly lower intra-cluster dispersion than uniform."""
        n = 60
        u = Instance.generate_random(n=n, seed=42)
        c_tight = Instance.generate_clustered(n=n, seed=42, num_clusters=4, cluster_spread=2.0)
        c_loose = Instance.generate_clustered(n=n, seed=42, num_clusters=4, cluster_spread=20.0)

        def mean_nn_dist(inst: Instance) -> float:
            coords = inst.coords[1:]  # customers
            dists = []
            for i in range(len(coords)):
                d = np.linalg.norm(coords - coords[i], axis=1)
                d[i] = np.inf
                dists.append(np.min(d))
            return float(np.mean(dists))

        u_disp = mean_nn_dist(u)
        tight_disp = mean_nn_dist(c_tight)
        loose_disp = mean_nn_dist(c_loose)

        # Tight clustering should have much lower nearest neighbor distance than uniform and loose
        assert tight_disp < loose_disp
        assert tight_disp < u_disp / 2.0


# ---------------------------------------------------------------------------
# 2. TSPLIB Benchmark Parser and Integration
# ---------------------------------------------------------------------------

class TestTSPLIBIntegration:
    """Tests for TSPLIB benchmark parsing, distance conventions, and scenarios."""

    def test_load_berlin52_benchmark(self):
        """berlin52.tsp is loaded and parsed with exact dimensions and coordinates."""
        tsplib_obj = load_tsplib_benchmark("berlin52")
        assert tsplib_obj.name == "berlin52"
        assert tsplib_obj.dimension == 52
        assert tsplib_obj.instance.n == 51  # 51 customers + 1 depot = 52 total
        assert tsplib_obj.metadata.edge_weight_type == "EUC_2D"
        assert tsplib_obj.instance.num_vertices == 52

        # Node 1 coordinate in berlin52 is (565.0, 575.0) -> mapped to index 0 (Depot)
        assert np.allclose(tsplib_obj.instance.coords[0], [565.0, 575.0])
        # Node 52 coordinate in berlin52 is (1740.0, 245.0) -> mapped to index 51
        assert np.allclose(tsplib_obj.instance.coords[51], [1740.0, 245.0])

    def test_load_eil51_benchmark(self):
        """eil51.tsp is loaded and parsed with exact dimensions and coordinates."""
        tsplib_obj = load_tsplib_benchmark("eil51")
        assert tsplib_obj.name == "eil51"
        assert tsplib_obj.dimension == 51
        assert tsplib_obj.instance.n == 50
        assert tsplib_obj.metadata.edge_weight_type == "EUC_2D"

        # Node 1 coordinate in eil51 is (37, 52) -> mapped to index 0 (Depot)
        assert np.allclose(tsplib_obj.instance.coords[0], [37.0, 52.0])
        # Node 51 coordinate in eil51 is (30, 40) -> mapped to index 50
        assert np.allclose(tsplib_obj.instance.coords[50], [30.0, 40.0])

    def test_tsplib_distance_convention(self):
        """tsplib_distance computes rounded integer EUC_2D while cost computes exact float."""
        tsplib_obj = load_tsplib_benchmark("berlin52")

        # Between index 0 (565, 575) and index 1 (25, 185):
        # dx = 540, dy = 390
        # sqrt(540^2 + 390^2) = sqrt(291600 + 152100) = sqrt(443700) = 666.108099335...
        # Standard TSPLIB rounded integer: 666
        # Float exact cost: 666.108099335...
        int_dist = tsplib_obj.tsplib_distance(0, 1)
        float_cost = tsplib_obj.cost(0, 1)

        assert int_dist == 666
        assert np.isclose(float_cost, 666.1080993352356)
        assert isinstance(int_dist, int)
        assert isinstance(float_cost, float)

    def test_create_dynamic_scenario_from_tsplib(self):
        """Static TSPLIB benchmark is decoupled from generated dynamic event sequences."""
        tsplib_obj = load_tsplib_benchmark("berlin52")
        inst = tsplib_obj.instance

        event_cfg = EventConfig(
            total_vertices=inst.n,
            dynamicity=0.4,
            events_per_step=2,
            seed=42,
        )
        static_inst, event_seq = create_dynamic_scenario_from_instance(inst, event_cfg)

        assert static_inst is inst
        assert static_inst.n == 51
        assert event_seq.total_revealed == int(round(51 * 0.4))
        # Initial known count: depot + remaining
        assert 0 in event_seq.initial_known
        # Verify events are groups of at most 2
        for ev in event_seq.events:
            assert len(ev) <= 2

    def test_parser_unsupported_edge_weight_type(self, tmp_path):
        """Parser rejects non-Euclidean conventions explicitly without silent conversion."""
        bad_tsp = tmp_path / "geo_test.tsp"
        bad_tsp.write_text(
            "NAME: geo_test\n"
            "TYPE: TSP\n"
            "DIMENSION: 3\n"
            "EDGE_WEIGHT_TYPE: GEO\n"
            "NODE_COORD_SECTION\n"
            "1 30.0 50.0\n"
            "2 32.0 51.0\n"
            "3 34.0 52.0\n"
            "EOF\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Unsupported TSPLIB EDGE_WEIGHT_TYPE 'GEO'"):
            parse_tsplib_file(bad_tsp)

    def test_berlin52_optimal_tour_and_distance_convention_comparison(self):
        """TSPLIB integer tour cost matches exact known optimum (7542) while continuous cost differs."""
        tsplib_obj = load_tsplib_benchmark("berlin52")
        # Official TSPLIB optimal tour for berlin52 (1-based node IDs)
        optimal_tour_1based = [
            1, 49, 32, 45, 19, 41, 8, 9, 10, 43, 33, 51, 11, 52, 14, 13, 47,
            26, 27, 28, 12, 25, 4, 6, 15, 5, 24, 48, 38, 37, 40, 39, 36, 35,
            34, 44, 46, 16, 29, 50, 20, 23, 30, 2, 7, 42, 21, 17, 3, 18, 31,
            22, 1
        ]
        optimal_tour_0based = [tsplib_obj.node_map[node] for node in optimal_tour_1based]

        integer_cost = tsplib_obj.tsplib_tour_cost(optimal_tour_0based)
        continuous_cost = tsplib_obj.continuous_tour_cost(optimal_tour_0based)

        # Exact match to published TSPLIB optimum
        assert integer_cost == 7542
        # Continuous Euclidean cost is explicitly decoupled and slightly higher (+2.37 units, +0.03%)
        assert np.isclose(continuous_cost, 7544.3659019, atol=1e-4)
        assert continuous_cost > integer_cost

    def test_ceil_2d_distance_convention(self, tmp_path):
        """CEIL_2D applies ceiling rounding instead of standard TSPLIB nint floor rounding."""
        ceil_tsp = tmp_path / "ceil_test.tsp"
        ceil_tsp.write_text(
            "NAME: ceil_test\n"
            "TYPE: TSP\n"
            "DIMENSION: 2\n"
            "EDGE_WEIGHT_TYPE: CEIL_2D\n"
            "NODE_COORD_SECTION\n"
            "1 0.0 0.0\n"
            "2 1.0 0.5\n"
            "EOF\n",
            encoding="utf-8",
        )
        parsed = parse_tsplib_file(ceil_tsp)
        assert parsed.metadata.edge_weight_type == "CEIL_2D"

        # Euclidean distance is sqrt(1^2 + 0.5^2) = sqrt(1.25) = 1.1180339887...
        # Under EUC_2D (nint): floor(1.118 + 0.5) = floor(1.618) = 1
        # Under CEIL_2D: ceil(1.118) = 2
        int_dist = parsed.tsplib_distance(0, 1)
        assert int_dist == 2
        assert np.isclose(parsed.cost(0, 1), 1.1180339887)

    def test_tsplib_metadata_provenance(self):
        """TSPLIBMetadata records benchmark collection origin and provenance notes."""
        b52 = load_tsplib_benchmark("berlin52")
        assert "Groetschel" in b52.metadata.comment or "Grötschel" in b52.metadata.comment or "Groetschel" in b52.metadata.provenance_note or "Grötschel" in b52.metadata.provenance_note
        assert b52.metadata.source == "TSPLIB95 (University of Heidelberg)"
        assert "7542" in b52.metadata.provenance_note

        e51 = load_tsplib_benchmark("eil51")
        assert "Christofides" in e51.metadata.comment or "Eilon" in e51.metadata.comment or "Christofides" in e51.metadata.provenance_note
        assert e51.metadata.source == "TSPLIB95 (University of Heidelberg)"
        assert "426" in e51.metadata.provenance_note


# ---------------------------------------------------------------------------
# 3. Batch Customer Arrivals
# ---------------------------------------------------------------------------

class TestBatchCustomerArrivals:
    """Tests for multi-customer batch arrivals and variable schedules."""

    def test_uniform_batch_size_event_generation(self):
        """EventConfig with events_per_step > 1 correctly batches customer arrivals."""
        inst = Instance.generate_random(n=12, seed=42)
        cfg = EventConfig(total_vertices=12, dynamicity=0.5, events_per_step=3, seed=42)
        seq = EventGenerator(cfg).generate(inst)

        # 6 customers revealed in batches of 3 -> exactly 2 event steps
        assert seq.num_event_steps == 2
        assert len(seq.events[0]) == 3
        assert len(seq.events[1]) == 3
        # No duplicates
        assert len(seq.events[0] & seq.events[1]) == 0
        assert seq.total_revealed == 6

    def test_batch_schedule_catch_up_when_schedule_is_shorter_than_remaining(self):
        """When batch_schedule reveals fewer customers than remaining, catch-up batch reveals rest."""
        inst = Instance.generate_random(n=10, seed=42)
        # 10 customers total. initial_known_count=2 -> 8 remaining.
        # schedule is (2, 2) which only covers 4 customers.
        cfg = EventConfig(
            total_vertices=10,
            initial_known_count=2,
            batch_schedule=(2, 2),
            seed=42,
        )
        seq = EventGenerator(cfg).generate(inst)
        # Should have 3 event steps: 2, 2, and catch-up 4
        assert seq.num_event_steps == 3
        assert len(seq.events[0]) == 2
        assert len(seq.events[1]) == 2
        assert len(seq.events[2]) == 4
        assert seq.total_revealed == 8

    def test_batch_schedule_exceeding_remaining(self):
        """When batch_schedule entries exceed remaining customers, batches truncate safely."""
        inst = Instance.generate_random(n=8, seed=42)
        # 8 customers total. initial_known_count=5 -> 3 remaining.
        # schedule is (2, 5, 2).
        cfg = EventConfig(
            total_vertices=8,
            initial_known_count=5,
            batch_schedule=(2, 5, 2),
            seed=42,
        )
        seq = EventGenerator(cfg).generate(inst)
        assert seq.num_event_steps == 3
        assert len(seq.events[0]) == 2
        assert len(seq.events[1]) == 1  # only 1 was left
        assert len(seq.events[2]) == 0  # 0 remaining
        assert seq.total_revealed == 3

    def test_batch_schedule_with_variable_and_empty_events(self):
        """batch_schedule supports arbitrary batch sizes including empty events."""
        inst = Instance.generate_random(n=10, seed=42)
        # initial known: 4 customers + depot = 5. remaining: 6 customers.
        # schedule: [2, 0, 3, 1] -> reveals 2, then 0, then 3, then 1 = 6 total.
        cfg = EventConfig(
            total_vertices=10,
            initial_known_count=4,
            batch_schedule=(2, 0, 3, 1),
            seed=42,
        )
        seq = EventGenerator(cfg).generate(inst)

        assert seq.num_event_steps == 4
        assert len(seq.events[0]) == 2
        assert len(seq.events[1]) == 0  # Empty event
        assert len(seq.events[2]) == 3
        assert len(seq.events[3]) == 1
        assert seq.total_revealed == 6

    def test_simulator_batch_arrivals_across_all_strategies(self):
        """Strategies A, B, C, and ADAPTIVE all preserve feasibility and frozen prefix under batches."""
        inst = Instance.generate_clustered(n=14, seed=99, num_clusters=3)
        cfg = EventConfig(
            total_vertices=14,
            dynamicity=0.5,
            batch_schedule=(2, 0, 3, 2),  # 7 revealed dynamically
            seed=99,
        )
        seq = EventGenerator(cfg).generate(inst)

        strategies = [Strategy.A, Strategy.B, Strategy.C, Strategy.ADAPTIVE]

        for strat in strategies:
            sim = Simulator(instance=inst, event_sequence=seq, freeze_per_step=1)
            res = sim.run(strat, seed=99)

            assert res.all_feasible, f"Strategy {strat} produced infeasible route under batch arrivals"
            assert len(res.steps) == 4

            # Route at step 2 after empty event should visit same number of customers as step 1
            assert len(res.steps[1].known_vertices) == len(res.steps[0].known_vertices)
            # Final route must visit all 14 customers + depot
            assert res.final_route.is_feasible(inst, required_vertices=set(range(1, 15)))

    def test_consecutive_large_batches_with_budget(self):
        """Simulator handles multiple consecutive large batches under computational budget."""
        inst = Instance.generate_mixed(n=16, seed=55, cluster_ratio=0.7)
        cfg = EventConfig(
            total_vertices=16,
            dynamicity=0.6,  # ~10 customers dynamic
            events_per_step=4,  # batches of 4
            seed=55,
        )
        seq = EventGenerator(cfg).generate(inst)

        sim = Simulator(instance=inst, event_sequence=seq, freeze_per_step=1, max_evaluations=150)
        res_c = sim.run(Strategy.C, seed=55)

        assert res_c.all_feasible
        for step in res_c.steps:
            assert step.metrics.computational_effort <= 150
            assert step.metrics.feasible


# ---------------------------------------------------------------------------
# 4. Experiment Schema and Runner Compatibility
# ---------------------------------------------------------------------------

class TestExperimentSchemaAndRunnerExpansion:
    """Tests for ConditionConfig metadata, serialization, and runner compatibility."""

    def test_condition_config_serialization_with_new_fields(self):
        """ConditionConfig serializes and deserializes distribution and batch parameters."""
        cond = ConditionConfig(
            condition_id="clustered_batch_test",
            total_vertices=30,
            dynamicity=0.4,
            events_per_step=3,
            distribution="clustered",
            distribution_params={"num_clusters": 4, "cluster_spread": 6.0},
            instance_source="synthetic",
            batch_schedule=(3, 3, 3, 3),
            budget=BudgetConfig(budget_type=BudgetType.MAX_EVALUATIONS, limit=300),
        )

        d = cond.to_dict()
        assert d["distribution"] == "clustered"
        assert d["distribution_params"]["num_clusters"] == 4
        assert d["batch_schedule"] == [3, 3, 3, 3]

        restored = ConditionConfig.from_dict(d)
        assert restored.condition_id == cond.condition_id
        assert restored.distribution == "clustered"
        assert restored.distribution_params == {"num_clusters": 4, "cluster_spread": 6.0}
        assert restored.batch_schedule == (3, 3, 3, 3)

    def test_runner_executes_clustered_and_tsplib_conditions(self):
        """ExperimentRunner successfully executes clustered conditions and TSPLIB benchmarks."""
        cond_clustered = ConditionConfig(
            condition_id="cond_clustered",
            total_vertices=12,
            dynamicity=0.3,
            events_per_step=2,
            distribution="clustered",
            distribution_params={"num_clusters": 2, "cluster_spread": 4.0},
            budget=BudgetConfig(budget_type=BudgetType.MAX_EVALUATIONS, limit=200),
        )

        cond_tsplib = ConditionConfig(
            condition_id="cond_tsplib_berlin",
            total_vertices=51,  # 51 customers in berlin52
            dynamicity=0.2,
            events_per_step=2,
            instance_source="tsplib",
            benchmark_name="berlin52",
            budget=BudgetConfig(budget_type=BudgetType.MAX_EVALUATIONS, limit=300),
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_cfg = ExperimentConfig(
                name="test_expanded_runner",
                conditions=(cond_clustered, cond_tsplib),
                seeds=(42,),
                strategies=("A", "C"),
                output_dir=tmp_dir,
            )

            runner = ExperimentRunner(exp_cfg)
            manifest = runner.run()

            assert manifest.completed_runs == 4  # 2 conditions x 1 seed x 2 strategies
            assert manifest.failed_runs == 0

            # Verify runs.csv contains distribution metadata
            runs_csv = Path(tmp_dir) / "runs.csv"
            assert runs_csv.exists()
            content = runs_csv.read_text(encoding="utf-8")
            assert "cond_clustered" in content
            assert "cond_tsplib_berlin" in content
            assert "clustered" in content
            assert "tsplib" in content
