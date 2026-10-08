"""Unit and integration tests for multi-provider LLM advisory adapters with mocked network calls."""
import json
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from app.core.config import settings
from app.services.llm_service import LLMService, redact_error


@pytest.mark.asyncio
async def test_llm_unconfigured_service_raises_503():
    with patch.object(settings, "LLM_API_KEY", None):
        with pytest.raises(Exception) as excinfo:
            await LLMService.generate_advisory(
                candidate_name="test-model",
                task_type="text-generation",
                metrics={"acc": 0.8},
                gate_verdict="APPROVED_FOR_RELEASE",
                failed_rules=[]
            )
        assert "LLM_API_KEY is not configured" in str(excinfo.value)


@pytest.mark.asyncio
async def test_openai_adapter_mocked():
    synthetic_key = "dummy-test-key-" + ("0" * 24)
    with patch.object(settings, "LLM_API_KEY", synthetic_key), \
         patch.object(settings, "LLM_PROVIDER", "openai"):

        mock_resp_data = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "advisory_summary": "Model shows solid convergence across reasoning tasks.",
                            "risk_level": "LOW",
                            "recommendations": ["Monitor inference p99 latency in canary deployment."]
                        })
                    }
                }
            ]
        }

        mock_req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        mock_resp = httpx.Response(status_code=200, json=mock_resp_data, request=mock_req)
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = await LLMService.generate_advisory(
                candidate_name="cand-1",
                task_type="text-generation",
                metrics={"acc": 0.85},
                gate_verdict="APPROVED_FOR_RELEASE",
                failed_rules=[]
            )
            assert res["risk_level"] == "LOW"
            assert "advisory_summary" in res
            assert res["provider"] == "openai"


@pytest.mark.asyncio
async def test_anthropic_adapter_mocked():
    synthetic_key = "dummy-anthropic-key-" + ("0" * 24)
    with patch.object(settings, "LLM_API_KEY", synthetic_key), \
         patch.object(settings, "LLM_PROVIDER", "anthropic"):

        mock_resp_data = {
            "content": [
                {
                    "text": json.dumps({
                        "advisory_summary": "Toxicity thresholds passed but latency warning present.",
                        "risk_level": "MEDIUM",
                        "recommendations": ["Optimize batch size."]
                    })
                }
            ]
        }

        mock_req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        mock_resp = httpx.Response(status_code=200, json=mock_resp_data, request=mock_req)
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = await LLMService.generate_advisory(
                candidate_name="cand-2",
                task_type="text-generation",
                metrics={"latency_p95_ms": 320.0},
                gate_verdict="NEEDS_REVIEW",
                failed_rules=["latency_p95_ms exceeded warning threshold"]
            )
            assert res["risk_level"] == "MEDIUM"
            assert res["provider"] == "anthropic"


@pytest.mark.asyncio
async def test_gemini_adapter_mocked():
    synthetic_key = "dummy-gemini-key-" + ("0" * 24)
    with patch.object(settings, "LLM_API_KEY", synthetic_key), \
         patch.object(settings, "LLM_PROVIDER", "gemini"):

        mock_resp_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "advisory_summary": "Clean safety profile.",
                                    "risk_level": "LOW",
                                    "recommendations": ["Safe to proceed with release sign-off."]
                                })
                            }
                        ]
                    }
                }
            ]
        }

        mock_req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models")
        mock_resp = httpx.Response(status_code=200, json=mock_resp_data, request=mock_req)
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = await LLMService.generate_advisory(
                candidate_name="cand-3",
                task_type="text-classification",
                metrics={"f1": 0.94},
                gate_verdict="APPROVED_FOR_RELEASE",
                failed_rules=[]
            )
            assert res["risk_level"] == "LOW"
            assert res["provider"] == "gemini"


def test_credential_redaction_utility():
    synthetic_val = "custom-key-" + ("0" * 32)
    with patch.object(settings, "LLM_API_KEY", synthetic_val):
        error_msg = f"Failed to connect using key {synthetic_val} on remote host."
        redacted = redact_error(error_msg)
        assert synthetic_val not in redacted
        assert "[REDACTED_CREDENTIAL]" in redacted
