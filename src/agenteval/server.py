from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from agenteval.db import get_run, init_db, list_runs, list_task_results_for_run


def create_app(db_path: str = "agenteval.db") -> FastAPI:
    app = FastAPI(title="AgentEval Dashboard")
    app.state.db_path = db_path
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        conn = sqlite3.connect(app.state.db_path)
        conn.row_factory = sqlite3.Row
        runs = list_runs(conn)
        conn.close()
        return templates.TemplateResponse(
            request, "index.html", {"runs": runs}
        )

    @app.get("/run/{run_id}", response_class=HTMLResponse)
    async def run_detail(request: Request, run_id: str) -> HTMLResponse:
        conn = sqlite3.connect(app.state.db_path)
        conn.row_factory = sqlite3.Row
        run = get_run(conn, run_id)
        if run is None:
            conn.close()
            return HTMLResponse(
                content="<h1>404 — Run not found</h1><p><a href='/'>Back to runs</a></p>",
                status_code=404,
            )
        task_results = list_task_results_for_run(conn, run_id)
        conn.close()
        return templates.TemplateResponse(
            request, "run_detail.html", {"run": run, "task_results": task_results}
        )

    return app
