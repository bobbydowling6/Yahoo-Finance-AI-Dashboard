import tomllib
from pathlib import Path

# Resolve base project directory safely (/app inside container)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

POSSIBLE_PATHS = [
    BASE_DIR / "config.toml",              # /app/config.toml
    Path.cwd() / "config.toml",            # Current working directory
    Path("/app/config.toml"),              # Explicit container working path
]

CONFIG_PATH = next((p for p in POSSIBLE_PATHS if p.exists()), None)

config = {}
if CONFIG_PATH and CONFIG_PATH.is_file():
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
else:
    print(f"WARNING: config.toml not found in {POSSIBLE_PATHS}. Proceeding with empty defaults.")