import sys
from pathlib import Path

# Ensure src/ is on sys.path so 'python main.py' works directly out of the box
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from polarisk_detector.cli import main

if __name__ == "__main__":
    main()

