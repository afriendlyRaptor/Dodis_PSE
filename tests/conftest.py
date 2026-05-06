"""pytest-Konfiguration: src/ zum Python-Suchpfad hinzufügen."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
