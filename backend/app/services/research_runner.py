"""Creates research runs and launches them as in-process background tasks."""

from __future__ import annotations

import asyncio
import functools
import uuid

import httpx

from app.db.models import ResearchRunRow
from app.services.document_fetcher import default_client, fetch_document
from app.services.llm.factory import EffectiveLLMConfig
from app.services.research_workflow import ResearchInput, ResearchWorkflow
from app.services.source_search import TavilySearch
from app.state import AppState


async def create_run(state: AppState, inp: ResearchInput, cfg: EffectiveLLMConfig) -> None:
    async with state.db.session() as session:
        session.add(
            ResearchRunRow(
                id=inp.run_id,
                status="queued",
                stage=None,
                input_text=inp.query,
                submitted_url=inp.submitted_url,
                intended_use_case=inp.intended_use_case,
                integration_context=inp.integration_context.value,
                additional_context=inp.additional_context,
                refresh_of_slug=inp.refresh_of_slug,
                events=[],
                sources=[],
                llm_provider=cfg.provider_id,
                llm_model=cfg.model,
                llm_source=cfg.source,
            )
        )
        await session.commit()


async def _execute(state: AppState, inp: ResearchInput, cfg: EffectiveLLMConfig) -> None:
    settings = state.settings
    async with default_client() as http, httpx.AsyncClient(timeout=20.0, trust_env=False) as search_http:
        search = (
            TavilySearch(settings.tavily_api_key.get_secret_value(), client=search_http)
            if settings.tavily_api_key and settings.search_configured
            else None
        )
        workflow = ResearchWorkflow(
            db=state.db,
            settings=settings,
            llm=cfg.build(),  # key stays inside this task's memory; never persisted
            llm_meta=(cfg.provider_id, cfg.model),
            search=search,
            fetch=functools.partial(fetch_document, client=http),
        )
        await workflow.run(inp)


def launch(state: AppState, inp: ResearchInput, cfg: EffectiveLLMConfig) -> None:
    task = asyncio.create_task(_execute(state, inp, cfg), name=f"research-{inp.run_id}")
    state.tasks.add(task)
    task.add_done_callback(state.tasks.discard)


def new_run_id() -> str:
    return str(uuid.uuid4())
