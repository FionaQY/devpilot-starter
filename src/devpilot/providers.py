"""Multi-provider chat client with automatic failover.

All providers here expose an OpenAI-compatible chat API, so one message format
works for every one of them. That is what makes it safe to fail over between
providers in the middle of an agent run.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache

import openai
from openai import OpenAI

from devpilot.config import get_settings

logger = logging.getLogger("devpilot.providers")

# name -> (base_url, settings attribute holding the key, settings attribute holding the model)
KNOWN_PROVIDERS: dict[str, tuple[str, str, str]] = {
    "openai": ("https://api.openai.com/v1", "openai_api_key", "openai_model"),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini_api_key",
        "gemini_model",
    ),
    "grok": ("https://api.x.ai/v1", "xai_api_key", "xai_model"),  # xAI's Grok
    "groq": ("https://api.groq.com/openai/v1", "groq_api_key", "groq_model"),  # Groq (different company)
}

RATE_LIMIT_DEFAULT_COOLDOWN = 60.0  # seconds
TRANSIENT_COOLDOWN = 30.0
BROKEN_CONFIG_COOLDOWN = 3600.0  # bad key / wrong model name: don't retry for an hour


class EmptyResponseError(Exception):
    """The provider answered but returned no choices (e.g. a safety filter)."""


class AllProvidersFailed(Exception):
    def __init__(self, failures: list[str]) -> None:
        self.failures = failures
        super().__init__("All providers failed: " + "; ".join(failures))


@dataclass(frozen=True)
class Provider:
    name: str
    model: str
    client: OpenAI


def describe_error(exc: Exception) -> str:
    """Short, safe description of an error (no request bodies, no keys)."""
    status = getattr(exc, "status_code", None)
    return f"{type(exc).__name__}" + (f" (HTTP {status})" if status else "")


def cooldown_for(exc: Exception) -> float:
    """How long to skip a provider after this error. 0 means try it again next time."""
    if isinstance(exc, openai.RateLimitError):
        retry_after = None
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                retry_after = float(response.headers.get("retry-after"))
            except (TypeError, ValueError):
                retry_after = None
        if retry_after is None:
            return RATE_LIMIT_DEFAULT_COOLDOWN
        return min(max(retry_after, 1.0), 3600.0)
    if isinstance(
        exc,
        (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError),
    ):
        return BROKEN_CONFIG_COOLDOWN
    if isinstance(exc, (openai.APIConnectionError, openai.InternalServerError)):
        # APITimeoutError is a subclass of APIConnectionError
        return TRANSIENT_COOLDOWN
    return 0.0  # e.g. a 400 for this specific request: just try the next provider


class ProviderPool:
    """Tries providers in order; skips ones that recently failed."""

    def __init__(self, providers: list[Provider]) -> None:
        self.providers = providers
        # Shared across requests so a rate-limited provider is skipped for a while.
        self._cooldown_until: dict[str, float] = {}

    @property
    def names(self) -> list[str]:
        return [p.name for p in self.providers]

    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        """Send one chat completion. Returns (response, provider_name)."""
        now = time.monotonic()
        ready = [p for p in self.providers if self._cooldown_until.get(p.name, 0.0) <= now]
        # If everything is cooling down, try them all anyway as a last resort.
        candidates = ready or self.providers

        failures: list[str] = []
        for provider in candidates:
            try:
                kwargs: dict = {"model": provider.model, "messages": messages}
                if tools:
                    kwargs["tools"] = tools
                response = provider.client.chat.completions.create(**kwargs)
                if not response.choices:
                    raise EmptyResponseError("no choices returned")
                return response, provider.name
            except (openai.OpenAIError, EmptyResponseError) as exc:
                failures.append(f"{provider.name}: {describe_error(exc)}")
                cooldown = cooldown_for(exc)
                if cooldown > 0:
                    self._cooldown_until[provider.name] = time.monotonic() + cooldown
                logger.warning(
                    "Provider %s failed (%s); cooling down %.0fs, trying next.",
                    provider.name,
                    describe_error(exc),
                    cooldown,
                )

        raise AllProvidersFailed(failures)


@lru_cache
def get_provider_pool() -> ProviderPool:
    settings = get_settings()
    providers: list[Provider] = []

    for name in settings.provider_names:
        spec = KNOWN_PROVIDERS.get(name)
        if spec is None:
            logger.warning("Unknown provider %r in PROVIDER_ORDER; skipping.", name)
            continue

        base_url, key_attr, model_attr = spec
        api_key = getattr(settings, key_attr)
        if not api_key:
            logger.info("No API key for %s; skipping.", name)
            continue

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=0,  # fail fast so we can move to the next provider
            timeout=settings.request_timeout_seconds,
        )
        providers.append(Provider(name=name, model=getattr(settings, model_attr), client=client))

    logger.info("Configured providers (in order): %s", [p.name for p in providers])
    return ProviderPool(providers)