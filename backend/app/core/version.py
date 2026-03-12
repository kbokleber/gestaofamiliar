from app.core.config import settings


def get_app_version_info() -> dict[str, str]:
    release_name = settings.APP_RELEASE_NAME or settings.APP_VERSION

    return {
        "version": settings.APP_VERSION,
        "commit": settings.APP_COMMIT_SHORT,
        "releaseName": release_name,
    }
