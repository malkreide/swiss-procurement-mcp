import httpx
import respx

from swiss_procurement_mcp.server import observe_public_url
from swiss_procurement_mcp.inputs import ProvenanceObservationInput


@respx.mock
async def test_observe_public_url_returns_bounded_envelope():
    respx.get("https://example.org/tender/1").mock(
        return_value=httpx.Response(200, text="public tender")
    )
    result = await observe_public_url(ProvenanceObservationInput(url="https://example.org/tender/1"))
    assert result.provenance == "live_api"
    assert result.observation.http_status == 200
    assert result.observation.reachable is True
    assert "configuration-specific stock" in result.observation.unknowns


@respx.mock
async def test_observe_public_url_preserves_unknown_on_error():
    respx.get("https://example.org/tender/2").mock(side_effect=httpx.ReadTimeout("timeout"))
    result = await observe_public_url(ProvenanceObservationInput(url="https://example.org/tender/2"))
    assert result.provenance == "degraded"
    assert result.observation.reachable is False
    assert result.observation.http_status is None
