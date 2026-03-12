from functools import lru_cache
from pathlib import Path
import subprocess

from app.core.config import settings


@lru_cache(maxsize=1)
def _resolve_git_version_info() -> dict[str, str] | None:
    repo_dir = Path(__file__).resolve().parents[2]

    try:
        commit_date = subprocess.check_output(
            ["git", "show", "-s", "--format=%cs", "HEAD"],
            cwd=repo_dir,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip().replace("-", ".")
        commit_short = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_dir,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None

    if not commit_date or not commit_short:
        return None

    release_name = f"{commit_date}-{commit_short}"
    return {
        "version": release_name,
        "commit": commit_short,
        "releaseName": release_name,
    }


def get_app_version_info() -> dict[str, str]:
    has_runtime_version = settings.APP_VERSION not in {"", "dev"} or settings.APP_COMMIT_SHORT not in {"", "local"}
    if has_runtime_version:
        release_name = settings.APP_RELEASE_NAME or settings.APP_VERSION
        return {
            "version": settings.APP_VERSION,
            "commit": settings.APP_COMMIT_SHORT,
            "releaseName": release_name,
        }

    git_version_info = _resolve_git_version_info()
    if git_version_info is not None:
        return git_version_info

    release_name = settings.APP_RELEASE_NAME or settings.APP_VERSION
    return {
        "version": settings.APP_VERSION,
        "commit": settings.APP_COMMIT_SHORT,
        "releaseName": release_name,
    }
