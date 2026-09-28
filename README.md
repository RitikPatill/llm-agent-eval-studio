# LLM Agent Eval Studio


> **Video walkthrough:** https://youtu.be/qMa1Rnt6EIE
> **60-second overview:** https://youtu.be/Gu5yKEMlinw

> Self-hostable eval harness for tool-calling LLM agents — define tasks in YAML, run against Claude/GPT-4, get a scored report.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue) ![MIT](https://img.shields.io/badge/license-MIT-green) ![tests passing](https://img.shields.io/badge/tests-34%20passing-brightgreen)

<!-- TODO: replace with a 5-10 second demo gif. Record with ScreenToGif on
     Windows or peek on macOS. Save to docs/demo.gif and update path here. -->
![demo](docs/demo.gif)

## What it is

`agenteval` is a local-first evaluation framework for tool-calling LLM agents. You write task definitions in YAML — specifying the prompt, which tools the agent may call, which tool calls you expect, and what keywords should appear in the final answer — then point the runner at an Anthropic or OpenAI model. It drives the agent through each task, scores the result against your rubric, and prints a `rich` scorecard table to the terminal.

Every run is persisted to a local SQLite database. A minimal FastAPI dashboard (`agenteval serve`) lets you browse run history and drill into per-task results without leaving your machine.

## Quickstart

```bash
git clone https://github.com/RitikPatill/llm-agent-eval-studio.git
cd llm-agent-eval-studio

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Set the API key for the provider you want to use
export ANTHROPIC_API_KEY=sk-ant-...   # or OPENAI_API_KEY for OpenAI

# Run the 10 built-in sample tasks
agenteval run tasks/sample/

# Launch the results dashboard
agenteval serve
# Open http://localhost:8000
```

## Usage

Run a task directory against a specific provider and model:

```bash
agenteval run tasks/sample/ --provider openai --model gpt-4o
```

The terminal prints a scored table — task ID, pass/fail, tool-match score, keyword score, and turns used. Results land in `agenteval.db` automatically.

To review past runs, `agenteval list` prints a summary table from the database. `agenteval serve` starts the dashboard on `:8000`; the index page lists every run by timestamp and aggregate score, and clicking a run shows the per-task breakdown with the agent's final answer for each task.

To query the dashboard API directly:

```bash
curl http://localhost:8000/api/runs
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                       CLI  (cli.py)                       │
│              agenteval run │ list │ serve                 │
└──────────────┬─────────────────────────────┬─────────────┘
               │                             │
               ▼                             ▼
   ┌───────────────────────┐    ┌───────────────────────┐
   │    AgentRunner        │    │   FastAPI server      │
   │    (runner.py)        │    │   (server.py)         │
   │  Anthropic tool_use   │    │   GET /               │
   │  OpenAI functions     │    │   GET /run/{id}       │
   └──────────┬────────────┘    └───────────┬───────────┘
              │                             │
   ┌──────────┴────────────┐    ┌───────────┴───────────┐
   │   ToolExecutor        │    │   SQLite  (db.py)     │
   │   (tools.py)          │    │   runs + task_results │
   │   calculator          │    └───────────────────────┘
   │   read_file           │
   │   write_file          │    ┌───────────────────────┐
   │   web_search_stub     │    │   Scorers             │
   └──────────┬────────────┘    │   (scorers.py)        │
              │                 │   tool_match · keyword│
   ┌──────────┴────────────┐    │   turn_penalty        │
   │   Task YAML           │    └───────────────────────┘
   │   (schema.py)         │
   └───────────────────────┘
```

## Project structure

```
llm-agent-eval-studio/
├── src/agenteval/       # package source — CLI, runners, scorers, server, DB
│   └── templates/       # Jinja2 HTML templates for the FastAPI dashboard
├── tasks/sample/        # 10 built-in eval tasks in YAML
├── tests/               # pytest suite (34 tests)
├── docs/                # demo gif and static assets
├── scripts/             # dev helpers: install check, demo recording
├── requirements.txt     # pinned runtime dependencies
└── pyproject.toml       # package metadata and entry-point declaration
```

## Adding your own tasks

Create a YAML file anywhere and run it:

```yaml
# tasks/my_tasks/addition.yaml
id: my_addition
prompt: "What is 42 + 58?"
tools_available: [calculator]
expected_tool_calls: [calculator]
expected_output_keywords: ["100"]
max_turns: 2
```

```bash
agenteval run tasks/my_tasks/
```

**Scoring:** `tool_match` (weight 0.5) measures whether the expected tool calls were made in order. `keyword` (weight 0.5) checks that all `expected_output_keywords` appear in the final answer. A `turn_penalty` of 0.1 is subtracted per turn beyond the first, clamped at 0.

## Roadmap

- [ ] LLM-as-judge scorer: use a second model call to assess open-ended answer quality
- [ ] Side-by-side multi-model comparison table in the dashboard
- [ ] Export run results to JSON/CSV for downstream analysis pipelines
- [ ] Streaming support to capture token-level latency as a scored metric
- [ ] GitHub Actions workflow for running the eval suite in CI on every push

## License

MIT — see [LICENSE](LICENSE).

---

Built autonomously by [autodev](https://github.com/RitikPatill/autodev),
a multi-agent orchestrator I designed. Each commit in this repo was
authored by me; the implementation work was performed by Sonnet under
the orchestrator's control. Read the orchestrator's README to see how.
