from unittest.mock import Mock, PropertyMock, patch

from pain_narratives.core.openai_client import OpenAIClient


class DummyResponse:
    """Simple object mimicking the OpenAI response with a model_dump method."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def model_dump(self) -> dict:
        return self._data


def test_openai_client_basic():
    prompt = (
        "Evaluate the pain severity described in this narrative on a scale of 0-10, "
        "where 0 is no pain and 10 is the worst pain imaginable. "
        "Consider both intensity and impact on daily activities. "
        "Return a JSON object with keys: pain_intensity, functional_impact, "
        "emotional_impact, descriptive_quality, reasoning."
    )
    narrative = (
        "I woke up everydays with pain in my arms and legs. "
        "Over the day, I find myself better, but I am constantly tired and sad"
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": narrative},
    ]

    # Fake response matching the structure returned by the real API
    fake_response_dict = {
        "choices": [{"message": {"content": "fake reply"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
    }
    dummy_response = DummyResponse(fake_response_dict)

    with patch.object(OpenAIClient, "client", new_callable=PropertyMock) as mock_client_prop:
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = dummy_response
        mock_client_prop.return_value = mock_client

        client = OpenAIClient(api_key="test-key")
        response = client.create_completion(messages=messages, model=None, temperature=0.7, max_tokens=512)

    assert response == fake_response_dict
    mock_client.chat.completions.create.assert_called_once()


if __name__ == "__main__":
    test_openai_client_basic()
