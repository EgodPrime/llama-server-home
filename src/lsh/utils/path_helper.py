import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
SRC_ROOT = PROJECT_ROOT / "src" / "lsh"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
WEB_FILES_DIR = PROJECT_ROOT / "web_files"
