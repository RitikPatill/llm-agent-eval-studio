from __future__ import annotations

import argparse
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from agenteval.db import init_db, insert_run, insert_task_result, list_runs
from agenteval.runner import AgentRunner, TaskResult
from agenteval.schema import load_task

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agenteval", description="LLM agent eval framework")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run all tasks in a directory")
    run_p.add_argument("tasks_dir", help="Directory containing *.yaml task files")
    run_p.add_argument("--provider", default="anthropic", choices=["anthropic", "openai"])
    run_p.add_argument("--model", default=None, help="Model ID (default: from env)")
    run_p.add_argument("--db", default="agenteval.db", help="SQLite database path")
    run_p.set_defaults(func=cmd_run)

    list_p = sub.add_parser("list", help="List past runs")
    list_p.add_argument("--db", default="agenteval.db", help="SQLite database path")
    list_p.set_defaults(func=cmd_list)

    return parser


def cmd_run(args: argparse.Namespace) -> None:
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())

    yaml_files = sorted(Path(args.tasks_dir).glob("*.yaml"))
    if not yaml_files:
        console.print(f"[yellow]No *.yaml files found in {args.tasks_dir}[/yellow]")
        return

    runner = AgentRunner(provider=args.provider, model=args.model)

    table = Table(title=f"agenteval run — {args.provider}/{runner.model}", show_footer=False)
    table.add_column("Task ID", style="cyan")
    table.add_column("Tools Made")
    table.add_column("Score", justify="right")
    table.add_column("Turns", justify="right")
    table.add_column("Pass", justify="center")

    results: list[TaskResult] = []

    for yaml_path in yaml_files:
        try:
            task = load_task(yaml_path)
            result = runner.run(task)
        except Exception as exc:
            console.print(f"[red]ERROR on {yaml_path.name}: {exc}[/red]")
            from agenteval.schema import TaskDefinition
            task_id = yaml_path.stem
            result = TaskResult(
                task_id=task_id,
                provider=args.provider,
                model=runner.model,
                passed=False,
                score=0.0,
                tool_calls_made=[],
                final_output=f"ERROR: {exc}",
                turns_used=0,
                score_breakdown={},
            )

        results.append(result)
        pass_text = Text("PASS", style="bold green") if result.passed else Text("FAIL", style="bold red")
        table.add_row(
            result.task_id,
            ", ".join(result.tool_calls_made) or "—",
            f"{result.score:.2f}",
            str(result.turns_used),
            pass_text,
        )

    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    avg_score = sum(r.score for r in results) / total_count if total_count else 0.0

    table.add_row(
        Text("TOTAL", style="bold"),
        "",
        Text(f"{avg_score:.2f}", style="bold"),
        "",
        Text(f"{passed_count}/{total_count}", style="bold"),
    )
    console.print(table)

    conn = init_db(args.db)
    insert_run(
        conn,
        run_id=run_id,
        provider=args.provider,
        model=runner.model,
        tasks_dir=str(args.tasks_dir),
        started_at=started_at,
        total_tasks=total_count,
        passed_tasks=passed_count,
        aggregate_score=avg_score,
    )
    for result in results:
        insert_task_result(conn, run_id, result)
    conn.close()

    console.print(f"Run [bold]{run_id}[/bold] saved to [bold]{args.db}[/bold]")


def cmd_list(args: argparse.Namespace) -> None:
    conn = init_db(args.db)
    rows = list_runs(conn)
    conn.close()

    table = Table(title="agenteval — past runs", show_footer=False)
    table.add_column("Run ID", style="cyan")
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Tasks Dir")
    table.add_column("Started At")
    table.add_column("Passed/Total", justify="right")
    table.add_column("Avg Score", justify="right")

    if not rows:
        console.print("[yellow]No runs found.[/yellow]")
        return

    for row in rows:
        table.add_row(
            row["run_id"][:8],
            row["provider"],
            row["model"],
            row["tasks_dir"],
            row["started_at"][:19],
            f"{row['passed_tasks']}/{row['total_tasks']}",
            f"{row['aggregate_score']:.2f}",
        )

    console.print(table)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)
