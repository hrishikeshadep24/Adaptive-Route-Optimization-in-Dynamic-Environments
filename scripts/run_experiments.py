"""CLI Entry Point to execute experimental campaigns."""
from __future__ import annotations

import argparse
import dataclasses
import logging
import sys

from adaptive_route_optimization.experiments.schema import ExperimentConfig
from adaptive_route_optimization.experiments.runner import run_experiment


def main() -> int:
    parser = argparse.ArgumentParser(description="Run experiment campaign from JSON config")
    parser.add_argument("--config", "-c", required=True, help="Path to ExperimentConfig JSON file")
    parser.add_argument("--output-dir", "-o", default=None, help="Override output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    cfg = ExperimentConfig.load(args.config)
    if args.output_dir:
        cfg = dataclasses.replace(cfg, output_dir=args.output_dir)

    manifest = run_experiment(cfg)
    return 0 if manifest.failed_runs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
