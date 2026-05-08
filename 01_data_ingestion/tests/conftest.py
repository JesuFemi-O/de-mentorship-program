import sys
from pathlib import Path

# Allow tests to import from src/ without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
