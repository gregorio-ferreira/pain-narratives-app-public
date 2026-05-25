from pathlib import Path

from pain_narratives.config import settings as settings_module


def test_pain_narratives_config_env_override(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "custom-config.yaml"
    config_path.write_text(
        """
openai:
  api_key: test-openai-key
  api_key_pain_narratives: test-project-key
  org_id: test-org
pg-prod:
  host: test-db.local
  database: test_db
  user: test_user
  password: test_password
  port: 5433
models:
  default_model: test-model
app:
  environment: test
""".strip()
    )

    monkeypatch.setenv("PAIN_NARRATIVES_CONFIG", str(config_path))
    monkeypatch.setattr(settings_module, "_config_manager", None)

    settings = settings_module.get_settings()

    assert settings.config_path == str(config_path)
    assert settings.pg_config.host == "test-db.local"
    assert settings.pg_config.port == 5433
    assert settings.openai_api_key == "test-openai-key"
    assert settings.model_config.default_model == "test-model"

    monkeypatch.setattr(settings_module, "_config_manager", None)
