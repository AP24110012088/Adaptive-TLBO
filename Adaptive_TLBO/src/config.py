"""Single, reproducible configuration point for all experiments."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR, OUTPUT_DIR, RESULTS_DIR, LOG_DIR = ROOT / "data", ROOT / "output", ROOT / "results", ROOT / "logs"
PAPER_PROFILE = True
POPULATION = 8 if PAPER_PROFILE else 6
ITERATIONS = 50 if PAPER_PROFILE else 30
RUNS = 10 if PAPER_PROFILE else 3
RANDOM_SEED = 20260715
EARLY_STOPPING_ROUNDS, IMPROVEMENT_THRESHOLD = 10, 1e-3
ENABLE_VERBOSE, ENABLE_PLOTS, ENABLE_MULTIPROCESSING, PLOT_DPI = False, True, False, 300
