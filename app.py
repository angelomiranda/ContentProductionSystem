from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from content_production_team.app import main, run_content_workflow

__all__ = ["main", "run_content_workflow"]


if __name__ == "__main__":
    main()
