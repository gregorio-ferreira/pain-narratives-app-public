"""Application settings and configuration."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class OpenAIConfig:
    """OpenAI configuration."""

    api_key: str
    api_key_pain_narratives: str
    org_id: str


@dataclass
class BedrockConfig:
    """AWS Bedrock configuration."""

    aws_credentials: str
    aws_access_key: str
    aws_secret_key: str
    aws_region: str


@dataclass
class PostgreSQLConfig:
    """PostgreSQL configuration."""

    password: str
    host: str
    database: str
    user: str
    port: int = 5432

    @property
    def url(self) -> str:
        """Return the PostgreSQL connection URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class ModelConfig:
    """Model configuration."""

    default_model: str = "gpt-5-mini"
    default_temperature: float = 1.0
    default_top_p: float = 1.0
    default_max_tokens: int = 8000  # GPT-5 needs high limits for reasoning tokens + output
    translation_model: str = "gpt-5-mini"
    translation_temperature: float = 1.0  # GPT-5 models work best with temperature 1.0
    translation_max_tokens: int = 8000  # Increased to match default for consistency


@dataclass
class AppConfig:
    """Application configuration."""

    data_root_path: str = "./data"
    environment: str = "development"
    streamlit_server_port: int = 8501
    streamlit_server_address: str = "localhost"

    @property
    def data_path(self) -> Path:
        """Return the resolved data path as a Path object."""
        return Path(self.data_root_path).resolve()


class ConfigManager:
    """Configuration manager that loads settings from YAML file."""

    def __init__(self, config_path: Optional[str] = None, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize configuration manager.

        Args:
            config_path (str, optional): Path to config file. Defaults to ~/.yaml.
            logger (Logger, optional): Logger instance.
        """
        if config_path is None:
            # Use project-level .yaml by default (need 4 dirname calls: settings.py -> config -> pain_narratives -> src -> project_root)
            project_yaml = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".yaml")
            if os.path.exists(project_yaml):
                config_path = project_yaml
            else:
                config_path = os.path.expanduser("~/.yaml")
        self.config_path = config_path
        self.logger = logger
        self._config: dict[str, Any] = {}

        if self.logger:
            self.logger.debug(f"Loading configuration from {config_path}")

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                self._config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            if self.logger:
                self.logger.warning(f"Config file not found: {self.config_path}")
            self._config = {}
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error loading config: {e}")
            self._config = {}

    @property
    def openai_config(self) -> OpenAIConfig:
        """Get OpenAI configuration."""
        config: dict[str, Any] = self._config or {}
        openai_data: dict[str, Any] = config.get("openai", {})
        return OpenAIConfig(
            api_key=openai_data.get("api_key", ""),
            api_key_pain_narratives=openai_data.get("api_key_pain_narratives", ""),
            org_id=openai_data.get("org_id", ""),
        )

    @property
    def bedrock_config(self) -> BedrockConfig:
        """Get AWS Bedrock configuration."""
        config: dict[str, Any] = self._config or {}
        bedrock_data: dict[str, Any] = config.get("bedrock", {})
        return BedrockConfig(
            aws_credentials=bedrock_data.get("aws_credentials", ""),
            aws_access_key=bedrock_data.get("aws_access_key", ""),
            aws_secret_key=bedrock_data.get("aws_secret_key", ""),
            aws_region=bedrock_data.get("aws_region", "us-east-1"),
        )

    @property
    def pg_config(self) -> PostgreSQLConfig:
        """Get PostgreSQL configuration."""
        config: dict[str, Any] = self._config or {}
        pg_data: dict[str, Any] = config.get("pg-prod", {})
        return PostgreSQLConfig(
            password=pg_data.get("password", ""),
            host=pg_data.get("host", "localhost"),
            database=pg_data.get("database", "pain_narratives"),
            user=pg_data.get("user", ""),
            port=int(pg_data.get("port", 5432)),
        )

    @property
    def model_config(self) -> ModelConfig:
        """Get model configuration."""
        config: dict[str, Any] = self._config or {}
        model_data: dict[str, Any] = config.get("models", {})
        return ModelConfig(
            default_model=model_data.get("default_model", "gpt-5-mini"),
            default_temperature=float(model_data.get("default_temperature", 1.0)),
            default_top_p=float(model_data.get("default_top_p", 1.0)),
            default_max_tokens=int(model_data.get("default_max_tokens", 8000)),
            translation_model=model_data.get("translation_model", "gpt-5-mini"),
            translation_temperature=float(model_data.get("translation_temperature", 1.0)),
            translation_max_tokens=int(model_data.get("translation_max_tokens", 8000)),
        )

    @property
    def app_config(self) -> AppConfig:
        """Get application configuration."""
        config: dict[str, Any] = self._config or {}
        app_data: dict[str, Any] = config.get("app", {})
        return AppConfig(
            data_root_path=app_data.get("data_root_path", "./data"),
            environment=app_data.get("environment", "development"),
            streamlit_server_port=int(app_data.get("streamlit_server_port", 8501)),
            streamlit_server_address=app_data.get("streamlit_server_address", "localhost"),
        )

    # Convenience properties for easier access
    @property
    def openai_api_key(self) -> str:
        return self.openai_config.api_key

    @property
    def openai_api_key_pain_narratives(self) -> str:
        return self.openai_config.api_key_pain_narratives

    @property
    def openai_org_id(self) -> str:
        return self.openai_config.org_id

    @property
    def database_url(self) -> str:
        return self.pg_config.url


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path=config_path)
    return _config_manager


def get_settings() -> ConfigManager:
    """Get settings - main function for accessing configuration."""
    return get_config_manager()


# Backward compatibility - simplified approach
def load_legacy_config() -> dict[str, Any]:
    """Load legacy config as a dict, never None."""
    config = get_config_manager()._config
    return config
