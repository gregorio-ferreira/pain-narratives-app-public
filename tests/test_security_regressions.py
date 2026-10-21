"""Offline regressions for data integrity, validation, logging and recovery."""

import io
import json
import platform
from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch

import pytest
from sqlmodel import select

from pain_narratives.batch.processor import BatchConfig, BatchProcessor, NarrativeEvaluationResult
from pain_narratives.config.settings import ConfigManager, PostgreSQLConfig
from pain_narratives.core.openai_client import OpenAIClient
from pain_narratives.core.questionnaire_runner import BPI_CODES, TSK_CODES, parse_questionnaire_response
from pain_narratives.db.models_sqlmodel import EvaluationResult, ExperimentList, RequestResponse
from pain_narratives.utils.file_utils import file_to_markdown


@pytest.mark.parametrize("kind", ["PCS", "BPI-IS", "TSK-11SV"])
def test_complete_instrument_validation(kind):
    if kind == "PCS":
        data = {"scores": {str(i): 2 for i in range(1, 14)}}
        invalid = {"scores": {**data["scores"], "1": True}}
    else:
        codes = BPI_CODES if kind == "BPI-IS" else TSK_CODES
        data = {"responses": [{"code": c, "value": 2} for c in sorted(codes)]}
        invalid = {"responses": data["responses"][:-1] + [data["responses"][0]]}
    assert parse_questionnaire_response(json.dumps(data), kind)[0]
    assert not parse_questionnaire_response(json.dumps(invalid), kind)[0]
    assert not parse_questionnaire_response('{"scores": {}, "responses": []}', kind)[0]


def test_upload_size_and_format_limits():
    with pytest.raises(RuntimeError, match="5 MiB"):
        file_to_markdown(io.BytesIO(b"x" * (5 * 1024 * 1024 + 1)), "sample.txt")
    with pytest.raises(RuntimeError, match="Only"):
        file_to_markdown(io.BytesIO(b"x"), "payload.pickle")


def test_reserved_db_password_and_remote_tls():
    config = PostgreSQLConfig(
        password="test-only:@/%?#", host="localhost", database="test", user="test", sslmode="disable"
    )
    assert config.connection_url.password == "test-only:@/%?#"
    assert config.connection_url.host == "localhost"
    with pytest.raises(ValueError, match="require"):
        PostgreSQLConfig(
            password="unused", host="db.example.com", database="test", user="test", sslmode="disable"
        ).connection_url
    assert (
        PostgreSQLConfig(password="unused", host="db.example.com", database="test", user="test").connection_url.query[
            "sslmode"
        ]
        == "verify-full"
    )


def test_legacy_openai_config_fallback_and_invalid_yaml(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("openai:\n  api_key_pain_narratives: placeholder-key\n")
    assert ConfigManager(str(config)).openai_api_key == "placeholder-key"
    config.write_text("- this is not a mapping\n")
    with pytest.raises(ValueError, match="Unable to load"):
        ConfigManager(str(config))


def test_provider_logs_omit_content_and_keys(caplog):
    reply = {"model": "snapshot-example", "choices": [{"message": {"content": "PRIVATE_RESPONSE_MARKER"}}]}
    response = SimpleNamespace(model_dump=lambda: reply)
    with patch.object(OpenAIClient, "client", new_callable=PropertyMock) as provider:
        provider.return_value.chat.completions.create.return_value = response
        client = OpenAIClient(api_key="PRIVATE_CREDENTIAL_MARKER")
        with caplog.at_level("INFO"):
            output = client.create_completion([{"role": "user", "content": "PRIVATE_NARRATIVE_MARKER"}])
    assert "PRIVATE_" not in caplog.text
    assert output["_request"]["messages"][0]["content"] == "PRIVATE_NARRATIVE_MARKER"
    assert "_request" not in reply  # Never mutate provider-owned dictionaries.


def test_batch_tripwire_and_success_only_resume(tmp_path):
    db = Mock()
    db.register_new_experiments_group.return_value = 7
    db.register_new_experiment.side_effect = range(100, 110)
    config = BatchConfig(
        include_dimensions=True,
        include_pcs=False,
        include_bpi_is=False,
        include_tsk_11sv=False,
        consecutive_failure_threshold=2,
        checkpoint_file=str(tmp_path / "checkpoint.json"),
    )
    processor = BatchProcessor(db_manager=db, openai_client=Mock(), config=config)
    processor.create_experiment_group = Mock(return_value=7)
    processor.process_single_narrative = Mock(
        side_effect=lambda **kw: NarrativeEvaluationResult(
            narrative_id=kw["narrative_id"],
            narrative_text=kw["narrative_text"],
            dimension_success=kw["narrative_id"] == 1,
        )
    )
    narratives = [{"narrative_id": i, "narrative_text": "Synthetic test narrative"} for i in range(1, 5)]
    with pytest.raises(RuntimeError, match="Batch stopped"):
        processor.run_batch_with_existing_narratives(narratives, user_id=1, group_description="test", run_number=1)
    checkpoint = json.loads((tmp_path / "checkpoint.json").read_text())
    assert checkpoint["processed_ids"] == [1]
    assert processor.progress.processed == 3
    processor.process_single_narrative = Mock(
        side_effect=lambda **kw: NarrativeEvaluationResult(
            narrative_id=kw["narrative_id"], narrative_text=kw["narrative_text"], dimension_success=True
        )
    )
    processor.run_batch_with_existing_narratives(
        narratives, user_id=1, group_description="test", run_number=1, resume=True
    )
    assert [call.kwargs["narrative_id"] for call in processor.process_single_narrative.call_args_list] == [2, 3, 4]
    with pytest.raises(ValueError, match="Cannot safely resume"):
        processor.run_batch_with_existing_narratives(
            narratives, user_id=1, group_description="test", run_number=2, resume=True
        )


class SessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value


def test_ui_persists_selected_narrative_and_request(db, monkeypatch):
    from pain_narratives.ui import app as app_module

    user = db.create_user("reviewer", "test-only-long-password", True)
    group = db.create_experiment_group(user.id, "Synthetic evaluation")
    original = db.create_narrative({"narrative": "Synthetic original narrative", "owner_id": user.id})
    selected = db.create_narrative({"narrative": "Synthetic selected narrative", "owner_id": user.id})
    state = SessionState(
        db_manager=db,
        user={"id": user.id},
        language="en",
        current_narrative_id=selected,
        evaluation_history=[],
        last_openai_response={
            "model": "snapshot-example",
            "_request": {
                "model": "alias-example",
                "messages": [{"role": "user", "content": "Synthetic selected narrative"}],
            },
        },
    )
    monkeypatch.setattr(app_module.st, "session_state", state)
    app = app_module.PainNarrativesApp.__new__(app_module.PainNarrativesApp)
    experiment_id = app.save_to_database(
        {
            "experiment_group_id": group.experiments_group_id,
            "narrative": "Synthetic selected narrative",
            "result": {"pain_severity": 3},
            "model": "alias-example",
        }
    )
    with db.get_session() as session:
        experiment = session.get(ExperimentList, experiment_id)
        assert experiment.narrative_id == selected
        assert experiment.extra_description["dependencies"]["python"] == platform.python_version()
        assert session.exec(select(EvaluationResult)).one().narrative_id == selected
        assert session.exec(select(RequestResponse)).one().request_json["model"] == "alias-example"
    assert original != selected
    with pytest.raises(ValueError, match="Failed evaluations"):
        app.save_to_database({"result": {"error": "synthetic failure"}})


def test_analysis_parsers_preserve_zero_and_use_item_codes():
    from pain_narratives.analysis.revision_data_layer import _parse_bpi, _parse_dimensions, _parse_tsk

    assert _parse_dimensions({"severidad_del_dolor": 0, "discapacidad": 0})["severidad_score"] == 0
    responses = [{"code": code, "value": index} for index, code in enumerate(sorted(BPI_CODES))]
    bpi = _parse_bpi({"raw_data": {"responses": list(reversed(responses))}})
    assert bpi["bpiq11"] == next(item["value"] for item in responses if item["code"] == "BPI_Q1_1")
    tsk_responses = [{"code": f"TSK_{index:02d}", "value": 1 + index % 4} for index in range(1, 12)]
    tsk = _parse_tsk({"raw_data": {"responses": list(reversed(tsk_responses))}})
    assert tsk["tsk_01"] == 2


@pytest.mark.parametrize("failure_type", ["auth", "request"])
def test_permanent_provider_failures_are_not_retried(failure_type):
    from pain_narratives.core.provider_errors import ProviderAuthError, ProviderRequestError

    exception = ProviderAuthError if failure_type == "auth" else ProviderRequestError
    processor = BatchProcessor(db_manager=Mock(), openai_client=Mock(), config=BatchConfig(retry_delay=0))
    call = Mock(side_effect=exception("synthetic provider failure"))
    with pytest.raises(exception):
        processor._call_llm_with_retry(call, label="test")
    assert call.call_count == 1


def test_transient_provider_failure_is_retried():
    from pain_narratives.core.provider_errors import ProviderTransientError

    processor = BatchProcessor(db_manager=Mock(), openai_client=Mock(), config=BatchConfig(retry_delay=0))
    call = Mock(side_effect=[ProviderTransientError("temporary"), {"success": True}])
    assert processor._call_llm_with_retry(call, label="test") == {"success": True}
    assert call.call_count == 2


def test_questionnaire_records_are_linked_to_the_evaluated_text(db, monkeypatch):
    from pain_narratives.db.models_sqlmodel import Questionnaire
    from pain_narratives.ui import app as app_module

    user = db.create_user("questionnaire-reviewer", "test-only-long-password", True)
    group = db.create_experiment_group(user.id, "Synthetic group")
    previous = db.create_narrative({"narrative": "Synthetic original", "owner_id": user.id})
    monkeypatch.setattr(
        app_module.st,
        "session_state",
        SessionState(
            db_manager=db,
            user={"id": user.id},
            current_narrative_id=previous,
            last_openai_response={
                "model": "snapshot-example",
                "_request": {"messages": [{"role": "user", "content": "Synthetic edited"}]},
            },
            last_prompt_messages=[{"role": "user", "content": "Synthetic edited"}],
        ),
    )
    app = app_module.PainNarrativesApp.__new__(app_module.PainNarrativesApp)
    qid = app.save_questionnaire_to_db(
        {"scores": {str(i): 2 for i in range(1, 14)}},
        "Synthetic edited",
        "PCS",
        {"experiment_group_id": group.experiments_group_id, "model": "alias", "temperature": 1.0},
    )
    with db.get_session() as session:
        questionnaire = session.get(Questionnaire, qid)
        experiment = session.get(ExperimentList, questionnaire.experiment_id)
        evaluation = session.exec(select(EvaluationResult)).one()
        response = session.exec(select(RequestResponse)).one()
        assert questionnaire.narrative_id != previous
        assert questionnaire.narrative_id == experiment.narrative_id == evaluation.narrative_id
        assert questionnaire.experiment_id == response.experiment_id
        assert evaluation.result_json["total_score"] == 26


def test_image_audit_gate_reports_unfixed_and_blocks_available_fixes(tmp_path, capsys):
    import importlib.util
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "scripts/security/check_image_report.py"
    spec = importlib.util.spec_from_file_location("image_report_for_tests", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = tmp_path / "image-report.json"
    item = {"Severity": "HIGH", "VulnerabilityID": "CVE-example", "PkgName": "example", "InstalledVersion": "1"}
    payload = {"ArtifactType": "container_image", "Results": [{"Vulnerabilities": [item]}]}
    report.write_text(json.dumps(payload))
    assert module.check_report(report) == 0
    assert "no upstream fix recorded" in capsys.readouterr().out
    item["FixedVersion"] = "2"
    report.write_text(json.dumps(payload))
    assert module.check_report(report) == 1
