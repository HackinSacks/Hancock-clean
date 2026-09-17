from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from hancock import __version__
from hancock.api.auth import require_auth
from hancock.api.metrics import ERRORS, REQUESTS
from hancock.backends import get_backend
from hancock.config import get_settings
from hancock.modes import VALID_MODES, normalize_mode, system_prompt

router = APIRouter()


class ChatBody(BaseModel):
    message: str | None = None
    messages: list[dict[str, str]] | None = None
    mode: str = "auto"
    model: str | None = None
    temperature: float = 0.2


class AskBody(BaseModel):
    question: str
    mode: str = "auto"
    model: str | None = None


class TriageBody(BaseModel):
    alert: str
    context: str | None = None


class HuntBody(BaseModel):
    hypothesis: str
    platform: str = Field(default="splunk", description="splunk|elastic|sentinel")


class RespondBody(BaseModel):
    incident: str


class CodeBody(BaseModel):
    prompt: str
    language: str = "python"


class CisoBody(BaseModel):
    question: str


class SigmaBody(BaseModel):
    description: str
    logsource: str | None = None


class YaraBody(BaseModel):
    description: str
    sample_hints: str | None = None


class IocBody(BaseModel):
    indicator: str


class WebhookBody(BaseModel):
    alert: str | dict[str, Any]
    source: str | None = None


async def _complete(mode: str, user_text: str, *, model: str | None = None, temperature: float = 0.2) -> str:
    backend = get_backend()
    messages = [
        {"role": "system", "content": system_prompt(mode)},
        {"role": "user", "content": user_text},
    ]
    return await backend.chat(messages, model=model, temperature=temperature)


@router.get("/health")
async def health() -> dict[str, Any]:
    settings = get_settings()
    backend = get_backend(settings)
    bhealth = await backend.health()
    return {
        "status": "ok",
        "service": "hancock",
        "version": __version__,
        "backend": settings.hancock_llm_backend,
        "backend_health": bhealth,
        "modes": sorted(VALID_MODES),
        "endpoints": [
            "/v1/chat", "/v1/ask", "/v1/triage", "/v1/hunt", "/v1/respond",
            "/v1/code", "/v1/ciso", "/v1/sigma", "/v1/yara", "/v1/ioc", "/v1/webhook",
        ],
    }


@router.post("/v1/chat", dependencies=[Depends(require_auth)])
async def chat(body: ChatBody) -> dict[str, Any]:
    mode = normalize_mode(body.mode)
    REQUESTS.labels("/v1/chat", mode).inc()
    try:
        if body.messages:
            msgs = list(body.messages)
            if not msgs or msgs[0].get("role") != "system":
                msgs = [{"role": "system", "content": system_prompt(mode)}, *msgs]
            text = await get_backend().chat(msgs, model=body.model, temperature=body.temperature)
        else:
            if not body.message:
                raise HTTPException(400, "message or messages required")
            text = await _complete(mode, body.message, model=body.model, temperature=body.temperature)
        return {"mode": mode, "response": text}
    except HTTPException:
        raise
    except Exception as exc:
        ERRORS.labels("/v1/chat").inc()
        raise HTTPException(502, f"backend error: {exc}") from exc


@router.post("/v1/ask", dependencies=[Depends(require_auth)])
async def ask(body: AskBody) -> dict[str, Any]:
    mode = normalize_mode(body.mode)
    REQUESTS.labels("/v1/ask", mode).inc()
    try:
        text = await _complete(mode, body.question, model=body.model)
        return {"mode": mode, "response": text}
    except Exception as exc:
        ERRORS.labels("/v1/ask").inc()
        raise HTTPException(502, f"backend error: {exc}") from exc


@router.post("/v1/triage", dependencies=[Depends(require_auth)])
async def triage(body: TriageBody) -> dict[str, Any]:
    REQUESTS.labels("/v1/triage", "soc").inc()
    prompt = (
        "Triage this SIEM/EDR alert. Return severity, MITRE ATT&CK mapping, verdict "
        "(TP/FP/Benign), and containment steps.\n\n"
        f"ALERT:\n{body.alert}\n"
        + (f"\nCONTEXT:\n{body.context}" if body.context else "")
    )
    try:
        return {"mode": "soc", "response": await _complete("soc", prompt)}
    except Exception as exc:
        ERRORS.labels("/v1/triage").inc()
        raise HTTPException(502, str(exc)) from exc


@router.post("/v1/hunt", dependencies=[Depends(require_auth)])
async def hunt(body: HuntBody) -> dict[str, Any]:
    REQUESTS.labels("/v1/hunt", "soc").inc()
    prompt = (
        f"Generate threat-hunting queries for platform={body.platform}. "
        f"Hypothesis:\n{body.hypothesis}\nInclude MITRE mapping and false-positive notes."
    )
    try:
        return {"mode": "soc", "platform": body.platform, "response": await _complete("soc", prompt)}
    except Exception as exc:
        ERRORS.labels("/v1/hunt").inc()
        raise HTTPException(502, str(exc)) from exc


@router.post("/v1/respond", dependencies=[Depends(require_auth)])
async def respond(body: RespondBody) -> dict[str, Any]:
    REQUESTS.labels("/v1/respond", "soc").inc()
    prompt = (
        "Produce a PICERL incident response playbook (Prepare, Identify, Contain, "
        f"Eradicate, Recover, Lessons Learned) for:\n{body.incident}"
    )
    try:
        return {"mode": "soc", "response": await _complete("soc", prompt)}
    except Exception as exc:
        ERRORS.labels("/v1/respond").inc()
        raise HTTPException(502, str(exc)) from exc


@router.post("/v1/code", dependencies=[Depends(require_auth)])
async def code(body: CodeBody) -> dict[str, Any]:
    REQUESTS.labels("/v1/code", "code").inc()
    settings = get_settings()
    if settings.hancock_llm_backend == "ollama":
        model = settings.ollama_coder_model
    elif settings.hancock_llm_backend == "nvidia":
        model = settings.hancock_coder_model
    else:
        model = settings.openai_coder_model
    prompt = (
        f"Write {body.language} security code for the following. "
        f"Authorized research only; add warnings.\n\n{body.prompt}"
    )
    try:
        return {"mode": "code", "response": await _complete("code", prompt, model=model)}
    except Exception as exc:
        ERRORS.labels("/v1/code").inc()
        raise HTTPException(502, str(exc)) from exc


@router.post("/v1/ciso", dependencies=[Depends(require_auth)])
async def ciso(body: CisoBody) -> dict[str, Any]:
    REQUESTS.labels("/v1/ciso", "ciso").inc()
    try:
        return {"mode": "ciso", "response": await _complete("ciso", body.question)}
    except Exception as exc:
        ERRORS.labels("/v1/ciso").inc()
        raise HTTPException(502, str(exc)) from exc


@router.post("/v1/sigma", dependencies=[Depends(require_auth)])
async def sigma(body: SigmaBody) -> dict[str, Any]:
    REQUESTS.labels("/v1/sigma", "sigma").inc()
    prompt = f"Author a Sigma rule for:\n{body.description}"
    if body.logsource:
        prompt += f"\nPreferred logsource: {body.logsource}"
    try:
        return {"mode": "sigma", "response": await _complete("sigma", prompt)}
    except Exception as exc:
        ERRORS.labels("/v1/sigma").inc()
        raise HTTPException(502, str(exc)) from exc


@router.post("/v1/yara", dependencies=[Depends(require_auth)])
async def yara(body: YaraBody) -> dict[str, Any]:
    REQUESTS.labels("/v1/yara", "yara").inc()
    prompt = f"Author a YARA rule for:\n{body.description}"
    if body.sample_hints:
        prompt += f"\nHints:\n{body.sample_hints}"
    try:
        return {"mode": "yara", "response": await _complete("yara", prompt)}
    except Exception as exc:
        ERRORS.labels("/v1/yara").inc()
        raise HTTPException(502, str(exc)) from exc


@router.post("/v1/ioc", dependencies=[Depends(require_auth)])
async def ioc(body: IocBody) -> dict[str, Any]:
    REQUESTS.labels("/v1/ioc", "ioc").inc()
    prompt = f"Enrich this IOC and return a structured threat intel report:\n{body.indicator}"
    try:
        return {"mode": "ioc", "response": await _complete("ioc", prompt)}
    except Exception as exc:
        ERRORS.labels("/v1/ioc").inc()
        raise HTTPException(502, str(exc)) from exc


async def _notify(url: str, payload: dict[str, Any]) -> None:
    if not url:
        return
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(url, json=payload)


@router.post("/v1/webhook", dependencies=[Depends(require_auth)])
async def webhook(request: Request, body: WebhookBody) -> dict[str, Any]:
    REQUESTS.labels("/v1/webhook", "soc").inc()
    settings = get_settings()
    secret = (settings.hancock_webhook_secret or "").strip()
    if secret:
        sig = request.headers.get("X-Hancock-Signature", "")
        raw = await request.body()
        expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(401, "Invalid webhook signature")
    alert_text = body.alert if isinstance(body.alert, str) else str(body.alert)
    prompt = (
        "Auto-triage this SIEM webhook alert. Return severity, MITRE mapping, verdict, actions.\n\n"
        f"SOURCE: {body.source or 'unknown'}\nALERT:\n{alert_text}"
    )
    try:
        result = await _complete("soc", prompt)
    except Exception as exc:
        ERRORS.labels("/v1/webhook").inc()
        raise HTTPException(502, str(exc)) from exc
    notify = {"text": f"[Hancock] webhook triage\n{result[:3500]}"}
    await _notify(settings.hancock_slack_webhook, notify)
    await _notify(settings.hancock_teams_webhook, {"text": notify["text"]})
    return {"mode": "soc", "response": result}
