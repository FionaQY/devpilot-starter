import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from devpilot.agent import Agent
from devpilot.config import get_settings
from devpilot.providers import AllProvidersFailed, get_provider_pool

logger = logging.getLogger("devpilot.routes")

router = APIRouter(prefix="/api")


class AgentRunRequest(BaseModel):
    task: str = Field(min_length=3, max_length=4000)
    repository: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Name of a repository folder directly inside DEV_PILOT_WORKSPACE.",
    )


class AgentRunResponse(BaseModel):
    answer: str
    tool_log: list[str]
    providers_used: list[str]
    total_tokens: int


@router.post("/agent/run", response_model=AgentRunResponse, tags=["agent"])
def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    settings = get_settings()
    pool = get_provider_pool()

    if not pool.providers:
        raise HTTPException(
            status_code=503,
            detail="No AI providers configured. Set at least one API key (e.g. GEMINI_API_KEY).",
        )

    workspace = settings.dev_pilot_workspace.expanduser().resolve()
    repo_path = (workspace / request.repository).resolve()

    # Only allow a direct child directory of the configured workspace.
    if repo_path.parent != workspace or not repo_path.is_dir():
        # Don't leak absolute filesystem paths to the client.
        raise HTTPException(status_code=404, detail=f"Repository '{request.repository}' not found.")

    try:
        agent = Agent(
            repository=repo_path,
            pool=pool,
            max_steps=settings.max_agent_steps,
            max_file_chars=settings.max_file_chars,
            keep_last_tool_results=settings.history_keep_tool_results,
            stub_chars=settings.history_stub_chars,
        )
        result = agent.run(request.task)
    except AllProvidersFailed as exc:
        logger.error("All providers failed: %s", exc.failures)
        raise HTTPException(
            status_code=503,
            detail="All AI providers failed: " + "; ".join(exc.failures),
        ) from exc
    except Exception as exc:
        logger.exception("Agent run failed")
        raise HTTPException(status_code=500, detail="Agent run failed. See server logs.") from exc

    return AgentRunResponse(
        answer=result.answer,
        tool_log=result.tool_log,
        providers_used=result.providers_used,
        total_tokens=result.total_tokens,
    )