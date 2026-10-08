"""Multi-provider LLM advisory adapter with error redaction and deterministic fallback."""
import re
import json
from typing import Dict, Any, List
import httpx
from fastapi import HTTPException, status
from app.core.config import settings


def redact_error(message: str) -> str:
    if not message:
        return ""
    msg = re.sub(r'(?:sk-[a-zA-Z0-9_\-]{8,}|Bearer\s+[a-zA-Z0-9_\-\.]+)', '[REDACTED_CREDENTIAL]', message)
    if settings.LLM_API_KEY:
        msg = msg.replace(settings.LLM_API_KEY, '[REDACTED_CREDENTIAL]')
    return msg


class LLMService:
    @staticmethod
    def is_configured() -> bool:
        return bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip())

    @classmethod
    async def generate_advisory(cls, candidate_name: str, task_type: str, metrics: Dict[str, float], gate_verdict: str, failed_rules: List[str]) -> Dict[str, Any]:
        if not cls.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM advisory service is unavailable: LLM_API_KEY is not configured."
            )

        provider = settings.LLM_PROVIDER.lower()
        model = settings.LLM_MODEL
        timeout = settings.LLM_TIMEOUT_SECONDS
        sys_p = "You are an AI Safety Gatekeeper advisor. Ground statements in supplied metrics. Output JSON: {'advisory_summary': str, 'risk_level': 'LOW'|'MEDIUM'|'HIGH', 'recommendations': list}."
        user_p = f"Model: {candidate_name}, Task: {task_type}, Verdict: {gate_verdict}, Metrics: {json.dumps(metrics)}, Failed: {json.dumps(failed_rules)}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if provider in ("openai", "openai-compatible", "ollama"):
                    b_url = settings.LLM_BASE_URL or "https://api.openai.com/v1"
                    url = f"{b_url.rstrip('/')}/chat/completions"
                    hdrs = {"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"}
                    body = {"model": model, "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}]}
                    resp = await client.post(url, headers=hdrs, json=body)
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                elif provider == "anthropic":
                    b_url = settings.LLM_BASE_URL or "https://api.anthropic.com/v1"
                    url = f"{b_url.rstrip('/')}/messages"
                    hdrs = {"x-api-key": settings.LLM_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
                    body = {"model": model, "system": sys_p, "messages": [{"role": "user", "content": user_p}], "max_tokens": 1000}
                    resp = await client.post(url, headers=hdrs, json=body)
                    resp.raise_for_status()
                    content = resp.json()["content"][0]["text"]
                elif provider == "gemini":
                    b_url = settings.LLM_BASE_URL or "https://generativelanguage.googleapis.com/v1beta"
                    url = f"{b_url.rstrip('/')}/models/{model}:generateContent?key={settings.LLM_API_KEY}"
                    body = {"contents": [{"parts": [{"text": f"{sys_p}\n{user_p}"}]}]}
                    resp = await client.post(url, json=body)
                    resp.raise_for_status()
                    content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    raise ValueError(f"Unsupported provider: {provider}")

            clean = content.strip()
            if clean.startswith("```"):
                clean = re.sub(r"^```(?:json)?\n?", "", clean)
                clean = re.sub(r"\n?```$", "", clean)
            parsed = json.loads(clean)
            return {
                "advisory_summary": parsed.get("advisory_summary", "Evaluation complete."),
                "risk_level": parsed.get("risk_level", "MEDIUM"),
                "recommendations": parsed.get("recommendations", []),
                "provider": provider,
                "model": model,
                "is_advisory_only": True,
            }
        except Exception as exc:
            redacted = redact_error(str(exc))
            raise HTTPException(status_code=502, detail=f"LLM provider error ({provider}): {redacted}")
