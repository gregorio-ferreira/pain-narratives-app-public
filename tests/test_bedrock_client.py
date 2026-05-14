from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from pain_narratives.core import bedrock_client
from pain_narratives.core.bedrock_client import BedrockAuthError, BedrockClient


@dataclass
class _FakeBedrockConfig:
    api_key: str = ""
    default_region: str = "us-east-1"
    aws_region: str = "us-east-1"
    aws_profile: str = ""


class _FakeCredentials:
    def __init__(self, expires_at: datetime | None = None) -> None:
        self._expiry_time = expires_at

    def get_frozen_credentials(self) -> object:
        return object()


class _FakeSTSClient:
    def get_caller_identity(self) -> dict[str, str]:
        return {
            "Account": "123456789012",
            "Arn": "arn:aws:sts::123456789012:assumed-role/example/session",
            "UserId": "example",
        }


class _FakeSession:
    def __init__(self, profile_name: str | None = None, credentials: _FakeCredentials | None = None) -> None:
        self.profile_name = profile_name
        self._credentials = credentials or _FakeCredentials()

    def get_credentials(self) -> _FakeCredentials | None:
        return self._credentials

    def client(self, service_name: str, region_name: str | None = None) -> object:
        assert service_name == "sts"
        assert region_name == "us-east-1"
        return _FakeSTSClient()


def _settings(config: _FakeBedrockConfig) -> SimpleNamespace:
    return SimpleNamespace(bedrock_config=config)


def test_check_credentials_uses_configured_aws_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions: list[_FakeSession] = []

    class FakeBoto3:
        @staticmethod
        def Session(profile_name: str | None = None) -> _FakeSession:
            session = _FakeSession(profile_name=profile_name)
            sessions.append(session)
            return session

    monkeypatch.setattr(
        bedrock_client,
        "get_settings",
        lambda: _settings(_FakeBedrockConfig(aws_profile="mfa")),
    )
    monkeypatch.setitem(__import__("sys").modules, "boto3", FakeBoto3)

    status = BedrockClient().check_credentials()

    assert sessions[0].profile_name == "mfa"
    assert status.auth_method == "aws_profile"
    assert status.profile_name == "mfa"
    assert status.account_id == "123456789012"
    assert status.principal_arn == "arn:aws:sts::123456789012:assumed-role/example/session"


def test_check_credentials_fails_without_aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    class SessionWithoutCredentials(_FakeSession):
        def get_credentials(self) -> None:
            return None

    class FakeBoto3:
        @staticmethod
        def Session(profile_name: str | None = None) -> SessionWithoutCredentials:
            return SessionWithoutCredentials(profile_name=profile_name)

    monkeypatch.setattr(
        bedrock_client,
        "get_settings",
        lambda: _settings(_FakeBedrockConfig()),
    )
    monkeypatch.setitem(__import__("sys").modules, "boto3", FakeBoto3)

    with pytest.raises(BedrockAuthError, match="No AWS credentials found"):
        BedrockClient().check_credentials()


def test_check_credentials_fails_when_mfa_session_near_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    class FakeBoto3:
        @staticmethod
        def Session(profile_name: str | None = None) -> _FakeSession:
            return _FakeSession(
                profile_name=profile_name,
                credentials=_FakeCredentials(expires_at=expires_at),
            )

    monkeypatch.setattr(
        bedrock_client,
        "get_settings",
        lambda: _settings(_FakeBedrockConfig(aws_profile="mfa")),
    )
    monkeypatch.setitem(__import__("sys").modules, "boto3", FakeBoto3)

    with pytest.raises(BedrockAuthError, match="Refresh the MFA session"):
        BedrockClient().check_credentials(min_remaining=timedelta(hours=2))


def test_bearer_token_auth_does_not_require_boto3(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bedrock_client,
        "get_settings",
        lambda: _settings(_FakeBedrockConfig(api_key="bedrock-api-key-not-a-real-token")),
    )

    status = BedrockClient().check_credentials()

    assert status.auth_method == "bedrock_api_key"
    assert status.region == "us-east-1"
    assert status.expires_at is None
