from unittest import mock

import pytest
import requests

from apps.ai.errors import AIOutputError, AIPermanentError, AITransientError
from apps.ai.providers.fake import FakeEmbeddingProvider
from apps.ai.providers.voyage import BATCH_SIZE, VoyageEmbeddingProvider

DIMS = 4


def http_response(status=200, payload=None):
    response = mock.Mock(status_code=status)
    response.json.return_value = payload
    return response


def ok(n, offset=0):
    return http_response(
        payload={
            "data": [{"index": i, "embedding": [float(offset + i)] * DIMS} for i in reversed(range(n))],
            "usage": {"total_tokens": 10},
        }
    )


def provider(session):
    return VoyageEmbeddingProvider(api_key="k", model="voyage-4", dimensions=DIMS, timeout=5, session=session)


def test_request_shape_and_ordering():
    session = mock.Mock(headers={})
    session.post.return_value = ok(2)

    vectors = provider(session).embed(["a", "b"], input_type="query")

    assert vectors == [[0.0] * DIMS, [1.0] * DIMS]  # sorted by index, not response order
    body = session.post.call_args.kwargs["json"]
    assert body == {"input": ["a", "b"], "model": "voyage-4", "input_type": "query", "output_dimension": DIMS}
    assert session.headers["Authorization"] == "Bearer k"


def test_batches_large_inputs():
    session = mock.Mock(headers={})
    session.post.side_effect = [ok(BATCH_SIZE), ok(5, offset=BATCH_SIZE)]

    vectors = provider(session).embed([str(i) for i in range(BATCH_SIZE + 5)])

    assert session.post.call_count == 2
    assert len(vectors) == BATCH_SIZE + 5


@pytest.mark.parametrize(
    ("result", "error"),
    [
        (http_response(429), AITransientError),
        (http_response(503), AITransientError),
        (requests.ConnectionError("down"), AITransientError),
        (requests.Timeout("slow"), AITransientError),
        (http_response(401), AIPermanentError),
        (http_response(400), AIPermanentError),
        (http_response(200, {"unexpected": True}), AIOutputError),
        (http_response(200, {"data": [{"index": 0, "embedding": [1.0]}]}), AIOutputError),  # wrong size
    ],
)
def test_error_mapping(result, error):
    session = mock.Mock(headers={})
    if isinstance(result, Exception):
        session.post.side_effect = result
    else:
        session.post.return_value = result
    with pytest.raises(error):
        provider(session).embed(["a"])


def test_missing_api_key():
    with pytest.raises(AIPermanentError):
        VoyageEmbeddingProvider(api_key="", model="voyage-4", dimensions=DIMS, timeout=5)


def test_fake_embeddings_are_deterministic_unit_vectors():
    fake = FakeEmbeddingProvider(dimensions=64)
    a1, a2, b = fake.embed(["Python Django", "Python Django", "Kubernetes"])
    assert a1 == a2 and a1 != b
    assert abs(sum(v * v for v in a1) - 1.0) < 1e-9
