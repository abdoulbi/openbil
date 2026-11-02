import httpx
import pytest
from openbil.connectors.worldbank import WorldBank


def test_pagination_and_raw(tmp_path):
    def handler(request):
        page = int(request.url.params["page"])
        return httpx.Response(
            200, json=[{"page": page, "pages": 2, "total": 2}, [{"id": str(page)}]]
        )

    w = WorldBank(
        tmp_path, httpx.Client(transport=httpx.MockTransport(handler)), delay=0
    )
    _, rows = w.pages("indicator")
    assert [r["id"] for r, _ in rows] == ["1", "2"]
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_api_error(tmp_path):
    w = WorldBank(
        tmp_path,
        httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json=[{"message": [{"id": "120"}]}])
            )
        ),
        delay=0,
    )
    with pytest.raises(ValueError, match="envelope"):
        w.pages("indicator")


def test_incomplete(tmp_path):
    w = WorldBank(
        tmp_path,
        httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json=[{"pages": 1, "total": 2}, [{}]])
            )
        ),
        delay=0,
    )
    with pytest.raises(ValueError, match="Incomplete"):
        w.pages("indicator")


def test_retry_429(tmp_path):
    calls = []

    def handler(r):
        calls.append(r)
        return (
            httpx.Response(429, headers={"Retry-After": "0"})
            if len(calls) == 1
            else httpx.Response(200, json=[{"pages": 1, "total": 0}, []])
        )

    w = WorldBank(
        tmp_path, httpx.Client(transport=httpx.MockTransport(handler)), delay=0
    )
    assert w.pages("indicator")[1] == []
    assert len(calls) == 2


def test_no_retry_forbidden(tmp_path):
    calls = []

    def handler(r):
        calls.append(r)
        return httpx.Response(403)

    w = WorldBank(
        tmp_path, httpx.Client(transport=httpx.MockTransport(handler)), delay=0
    )
    with pytest.raises(httpx.HTTPStatusError):
        w.pages("indicator")
    assert len(calls) == 1


def test_changed_during_pagination(tmp_path):
    def handler(r):
        page = int(r.url.params["page"])
        return httpx.Response(
            200, json=[{"pages": 2, "total": 2, "lastupdated": str(page)}, [{}]]
        )

    w = WorldBank(
        tmp_path, httpx.Client(transport=httpx.MockTransport(handler)), delay=0
    )
    with pytest.raises(ValueError, match="changed"):
        w.pages("indicator")
