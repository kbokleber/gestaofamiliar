from app.core import version


def test_get_app_version_info_falls_back_to_git(monkeypatch):
    monkeypatch.setattr(version.settings, "APP_VERSION", "dev")
    monkeypatch.setattr(version.settings, "APP_COMMIT_SHORT", "local")
    monkeypatch.setattr(version.settings, "APP_RELEASE_NAME", None)
    version._resolve_git_version_info.cache_clear()
    monkeypatch.setattr(
        version,
        "_resolve_git_version_info",
        lambda: {
            "version": "2026.03.12-b5243f9",
            "commit": "b5243f9",
            "releaseName": "2026.03.12-b5243f9",
        },
    )

    data = version.get_app_version_info()

    assert data == {
        "version": "2026.03.12-b5243f9",
        "commit": "b5243f9",
        "releaseName": "2026.03.12-b5243f9",
    }


def test_get_app_version_info_prefers_runtime_env(monkeypatch):
    monkeypatch.setattr(version.settings, "APP_VERSION", "2026.03.12-b5243f9")
    monkeypatch.setattr(version.settings, "APP_COMMIT_SHORT", "b5243f9")
    monkeypatch.setattr(version.settings, "APP_RELEASE_NAME", "2026.03.12-b5243f9")
    version._resolve_git_version_info.cache_clear()
    monkeypatch.setattr(version, "_resolve_git_version_info", lambda: None)

    data = version.get_app_version_info()

    assert data == {
        "version": "2026.03.12-b5243f9",
        "commit": "b5243f9",
        "releaseName": "2026.03.12-b5243f9",
    }
