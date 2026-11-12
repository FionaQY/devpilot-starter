# DevPilot

A small, local-first AI software engineering agent. The first milestone is intentionally
read-only: DevPilot can inspect a repository, answer questions about it, and cite the files
it used. It cannot edit files or execute shell commands yet.

## What is included

- **FastAPI** backend with `GET /health` and `POST /api/agent/run`
- **OpenAI Responses API** integration
- A minimal agent loop that handles model-requested function calls
- Three repository tools: `list_files`, `read_file`, and `search_files`
- Workspace path restrictions so the agent cannot read arbitrary paths on your computer
- A small test suite for the filesystem boundary

## Architecture

```text
You / API client
      |
      v
FastAPI route  (src/devpilot/api/routes.py)
      |
      v
Agent loop     (src/devpilot/agent.py)
      |                     ^
      | model request       | final answer / tool request
      v                     |
OpenAI Responses API -------+
      |
      | function call request
      v
Tool registry  (src/devpilot/tools/registry.py)
      |
      v
Filesystem tools (src/devpilot/tools/filesystem.py)
      |
      v
Selected repository, inside DEV_PILOT_WORKSPACE
```

The model does not directly access your computer. It requests a tool call; **your Python
application validates the arguments and runs the corresponding function**. The workspace
boundary is enforced in Python, not by the prompt.

## Requirements

- Python 3.11+
- An OpenAI API key and API access to the model configured in `.env`
- macOS, Windows, or Linux

You do **not** need Docker, a database, LangGraph, or MCP for this first milestone.

## Setup

From this directory:

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .venv\\Scripts\\activate    # Windows PowerShell

# 2. Install the project and development tools
python -m pip install --upgrade pip
pip install -e ".[dev]"

# 3. Configure your environment
cp .env.example .env
```

Edit `.env`:
- Set `OPENAI_API_KEY` to your API key.
- Set `DEV_PILOT_WORKSPACE` to a directory that contains the repositories you want DevPilot
  to inspect. For example, if your projects live in `~/code`, use the expanded absolute path
  such as `/Users/yourname/code`.
- Change `OPENAI_MODEL` if you want to use another model available to your API account.

**Never commit `.env` or share your API key.** The `.gitignore` already excludes `.env`.

## Run it

Start the API server:

```bash
uvicorn devpilot.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API page.

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/agent/run \\
  -H "Content-Type: application/json" \\
  -d '{
    "task": "Explain how this project is organised. Find the main entry points.",
    "repository": "my-project"
  }'
```

Here, `my-project` must be a folder directly inside `DEV_PILOT_WORKSPACE`. The API returns
the agent's final text and a short log of tools it used.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Run tests

```bash
pytest
```

## Project structure

```text
devpilot/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
├── src/
│   └── devpilot/
│       ├── __init__.py
│       ├── main.py                 # FastAPI application entry point
│       ├── config.py               # Loads environment configuration
│       ├── agent.py                # The model/tool orchestration loop
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes.py           # HTTP endpoints and request validation
│       └── tools/
│           ├── __init__.py
│           ├── filesystem.py       # Safe, read-only repository operations
│           └── registry.py         # Tool schemas + dispatch
└── tests/
    └── test_filesystem.py
```

## How the agent loop works

1. Your task and the available tool definitions are sent to the model.
2. The model either responds with text or requests a function such as `list_files`.
3. The backend parses the function arguments and dispatches the call through the registry.
4. The tool result is sent back to the model.
5. The model can request another tool or produce its final answer.
6. The loop stops after `MAX_AGENT_STEPS` to avoid runaway calls.

This is the core agent pattern. The model chooses *what it wants to do*; your application decides
*whether and how that action is allowed*.

## Build roadmap

### Milestone 1 — Repository Q&A (this starter)
- [x] FastAPI service
- [x] Model/tool loop
- [x] Read-only file tools
- [x] Workspace boundary
- [ ] Add conversation history and streaming

### Milestone 2 — Controlled code changes
- Add `propose_patch` and `apply_patch` tools.
- Show a diff and require explicit approval before applying it.
- Add Git status/diff tools.
- Keep shell execution disabled for now.

### Milestone 3 — Tests in an isolated environment
- Run tests inside a Docker container, not directly on your host.
- Set time, memory, CPU, and network limits.
- Return stdout, stderr, and exit code to the agent.
- Require approval before running unfamiliar commands.

### Milestone 4 — MCP integrations
- Add an MCP client and connect one external server (for example, GitHub).
- Learn tool discovery, resources, prompts, and server/client boundaries.
- Keep local filesystem tools as native Python tools initially; MCP is an integration protocol,
  not a requirement for every function.

### Milestone 5 — Better codebase retrieval
- Add `ripgrep` for fast text search.
- Add Tree-sitter for language-aware symbol extraction.
- Later experiment with embeddings and semantic retrieval.

### Milestone 6 — Orchestration, UI, and evaluation
- Consider LangGraph for persistent, checkpointed workflows.
- Build a React + TypeScript frontend with task history, tool traces, and diff approval.
- Evaluate on a fixed set of real repository tasks: task completion, test pass rate, regressions,
  tool-call count, latency, and cost.

## Safety rules for this starter

- Only inspect repositories inside the configured workspace.
- The initial tools are read-only.
- Do not add unrestricted shell access.
- Do not let the model decide its own permissions.
- Before enabling edits or command execution, add explicit approval and an isolated sandbox.

## Troubleshooting

- **`OPENAI_API_KEY` missing:** check that `.env` exists and contains the key.
- **Workspace error:** `DEV_PILOT_WORKSPACE` must be an existing directory. Use an absolute path.
- **Repository not found:** the `repository` value must name a child directory of the workspace.
- **Model error:** verify the model name and that your API account can use it.
- **Import error:** activate `.venv` and run `pip install -e ".[dev]"` again.

## Useful references

- OpenAI function calling guide: https://developers.openai.com/api/docs/guides/function-calling
- OpenAI Python SDK: https://developers.openai.com/api/reference/python
- FastAPI documentation: https://fastapi.tiangolo.com/
