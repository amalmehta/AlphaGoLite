"""Regenerate every value, table and figure for one venue folder.

    python make_all.py ../aaai27
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
venue_dir = Path(sys.argv[1] if len(sys.argv) > 1 else HERE.parent / "aaai27").resolve()
env = dict(os.environ, VENUE_DIR=str(venue_dir), VENUE=venue_dir.name, SOURCE_DATE_EPOCH="1760000000")
for script in ["make_values.py", "hyperparams_table.py", "platform_table.py",
               "loss_curves.py", "elo_comparison.py", "step_gain.py"]:
    print("running", script, flush=True)
    subprocess.run([sys.executable, str(HERE / script)], check=True, env=env, cwd=HERE)
