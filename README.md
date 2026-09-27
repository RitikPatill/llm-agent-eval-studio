# agenteval

A lightweight, local-first evaluation framework for tool-calling LLM agents.

## What it is

Write task definitions in YAML (input prompt, expected tool calls, expected output, scoring rubric), point the runner at any OpenAI- or Anthropic-compatible model, and get a structured scorecard back — both as a terminal table (via `rich`) and as a persistent SQLite store queryable through a minimal FastAPI dashboard.

## Why it exists

Every serious AI team runs evals, but hosted eval platforms (Braintrust, LangSmith, etc.) lock you in and cost money. Open-source alternatives like `evals` (OpenAI) are complex to extend. This project gives a developer a **working eval loop in under 5 minutes**: clone, `pip install -r requirements.txt`, drop a YAML file, run one command.

It's intentionally small — the value is in the pattern, not the size.

## Status

**M2 — task schema + mock tool executor complete.**

- `src/agenteval/schema.py`: `TaskDefinition` Pydantic v2 model + `load_task(path)` YAML loader
- `src/agenteval/tools.py`: `ToolExecutor` with four mock tools — `read_file`, `write_file`, `calculator`, `web_search_stub`
- `tasks/sample/`: three example YAML task files (calculator, file round-trip, web search)
- 9 unit tests in `tests/test_schema.py` — all pass (`pytest tests/test_schema.py`)

**M1 — scaffold complete.**

- `src/agenteval/` package installs cleanly via `pip install -e .` (src layout, `pyproject.toml`, PEP 561 `py.typed` marker)
- CLI entry point registered: `agenteval` prints version stub
- All runtime dependencies pinned in `requirements.txt`; dev dependencies (`pytest`, `pytest-cov`) in `requirements-dev.txt`
- Smoke tests pass: package importable, version string asserted (`tests/test_scaffold.py`)

Runner, scorer, store, and dashboard are planned for M3–M5 — see Architecture below.

## Quickstart

> ⚠️ Quickstart commands are fully operational after M4.

```bash
# 1. Clone and install
git clone https://github.com/your-username/llm-agent-eval-studio.git
cd llm-agent-eval-studio
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...   # or OPENAI_API_KEY for OpenAI

# 3. Run the built-in sample tasks
agenteval run tasks/

# 4. (Optional) Launch the dashboard
agenteval serve
# Open http://localhost:8000
```

A task YAML looks like this:

```yaml
id: calc_basic
prompt: "What is 17 multiplied by 6?"
tools_available: [calculator]
expected_tool_calls: [calculator]
expected_output_keywords: ["102"]
max_turns: 3
```

## Architecture overview

```
src/agenteval/
├── __init__.py       # package version                        [M1 - exists]
├── __main__.py       # CLI entry point stub                   [M1 - exists]
├── py.typed          # PEP 561 marker                        [M1 - exists]
├── schema.py         # TaskDefinition Pydantic model, load_task()  (M2)
├── tools.py          # ToolExecutor with four mock tools            (M2)
├── runner.py         # Anthropic + OpenAI runners                  (M3)
├── scorer.py         # Exact-match, keyword, turn-penalty     (M3)
├── store.py          # SQLite persistence                     (M4)
├── cli.py            # rich table output, run/serve commands  (M4)
└── dashboard.py      # FastAPI app + HTML templates           (M5)

tasks/sample/         # three sample YAML task files               (M2)
tests/                # pytest suite                           [M1 - exists]
pyproject.toml        # build config, entry point, deps        [M1 - exists]
requirements.txt      # pinned runtime deps                    [M1 - exists]
requirements-dev.txt  # pinned dev deps (pytest, pytest-cov)   [M1 - exists]
```

## Roadmap

| Milestone | Scope | Status |
|-----------|-------|--------|
| M1 | Repo scaffold, package layout, pinned deps, smoke tests | **done** |
| M2 | Pydantic task/result schema, YAML loader, mock tools, sample tasks | **done** |
| M3 | Anthropic + OpenAI runners, exact-match + keyword scorer | planned |
| M4 | SQLite store, `agenteval run` CLI, rich scorecard table | planned |
| M5 | FastAPI dashboard, HTML results view, `agenteval serve` | planned |

## License

MIT — see [LICENSE](LICENSE).
