# src/lsh/utils/path_helper.py
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
SRC_ROOT = PROJECT_ROOT / "src" / "lsh"
CONTROLLER_CONFIG_PATH = PROJECT_ROOT / "controller.yaml"