from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router
from app.config import settings
from app.runtime import ApplicationServices

import os
import sys

from app.logging_utils import PerRequestFileHandler

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

# --- Configure Per-Request Chat Pipeline Log Files ---
# Every request used to be appended to one shared chat_pipeline.log, which made it
# hard to follow a single request's Step 1 -> 6 trace among concurrent traffic.
# Each request now gets its own file at logs/requests/<request_id>.log instead -
# see app/logging_utils.py for how request_id is propagated via a contextvar.
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
REQUEST_LOGS_DIR = os.path.join(LOGS_DIR, "requests")

chat_file_handler = PerRequestFileHandler(REQUEST_LOGS_DIR)
chat_file_handler.setLevel(logging.INFO)
chat_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

# Attach exclusively to chat services, stream service, llm client, and endpoints to capture all Step 1 -> 6 pipeline logs
for logger_name in ["app.services.chat_service", "app.services.stream_service", "app.api.endpoints", "app.llm.llm_client"]:
    target_logger = logging.getLogger(logger_name)
    # Remove existing file handlers if any to avoid duplicate entries during hot reload
    target_logger.handlers = [h for h in target_logger.handlers if not isinstance(h, PerRequestFileHandler)]
    target_logger.addHandler(chat_file_handler)
    target_logger.propagate = True

logger.info("Per-request chat pipeline logs initialized at: %s/<request_id>.log", REQUEST_LOGS_DIR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    services = ApplicationServices.build(settings)
    app.state.services = services
    logger.info("Application starting up. Checking vector stores and database...")
    try:
        # Check and auto-sync business knowledge from business_knowledge.json on startup
        knowledge_count = services.knowledge_service.count()
        if knowledge_count == 0:
            logger.info("Business knowledge store is empty, running auto-sync from %s...", settings.knowledge_file_path)
            k_result = services.knowledge_service.sync_knowledge(force_reset=False)
            logger.info("Auto-sync knowledge result: %s", k_result)
        else:
            logger.info("Business knowledge store contains %d indexed chunks.", knowledge_count)

        # Check and auto-sync SQL examples from sql_examples.json on startup
        sql_examples_count = services.sql_examples_service.count()
        if sql_examples_count == 0:
            logger.info("SQL examples store is empty, running auto-sync from %s...", settings.sql_examples_file_path)
            sql_result = services.sql_examples_service.sync_sql_examples(force_reset=False)
            logger.info("Auto-sync SQL examples result: %s", sql_result)
        else:
            logger.info("SQL examples store contains %d indexed examples.", sql_examples_count)

        # Check ClickHouse connection
        if services.clickhouse_client.ping():
            logger.info("ClickHouse connection verified successfully.")
        else:
            logger.warning("ClickHouse is not reachable at startup.")
    except Exception as e:
        logger.warning("Startup initialization warning: %s", e)
    yield
    logger.info("Application shutting down.")



app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=settings.cors_origin_list != ["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs", "health": "/api/health"}
