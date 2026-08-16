import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

_database_setting = os.environ.get("DRID_DATABASE")

DATABASE_PATH = (
    Path(_database_setting).expanduser().resolve()
    if _database_setting
    else BASE_DIR / "drid.db"
)

DEBUG = os.environ.get("DRID_DEBUG", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}