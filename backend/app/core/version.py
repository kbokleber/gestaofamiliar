from functools import lru_cache
from pathlib import Path
import subprocess
from datetime import datetime, timezone

from app.core.config import settings


def _short_commit(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned[:7]


def _resolve_ci_version_info() -> dict[str, str] | None:
    commit_raw = settings.SOURCE_COMMIT or settings.COMMIT_SHA or settings.GITHUB_SHA
    commit_short = _short_commit(commit_raw)
    if not commit_short:
        return None

    release_name = f"{datetime.now(timezone.utc).strftime('%Y.%m.%d')}-{commit_short}"
    return {
        "version": release_name,
        "commit": commit_short,
        "releaseName": release_name,
    }


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

    ci_version_info = _resolve_ci_version_info()
    if ci_version_info is not None:
        return ci_version_info

    git_version_info = _resolve_git_version_info()
    if git_version_info is not None:
        return git_version_info

    release_name = settings.APP_RELEASE_NAME or settings.APP_VERSION
    return {
        "version": settings.APP_VERSION,
        "commit": settings.APP_COMMIT_SHORT,
        "releaseName": release_name,
    }
