import logging

import structlog
from fastapi import FastAPI

from app.api.routes import chat, feedback, health, menu
from app.config import get_settings

logging_configured = False


def configure_logging() -> None:
    global logging_configured
    if logging_configured:
        return
    settings = get_settings()
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
    )
    logging_configured = True


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="WarmOven AI Ordering Assistant",
        version="0.1.0",
        description="Stage 1: menu Q&A and customer feedback.",
    )

    app.include_router(health.router, tags=["health"])
    app.include_router(menu.router, tags=["menu"])
    app.include_router(feedback.router, tags=["feedback"])
    app.include_router(chat.router, tags=["chat"])

    return app


app = create_app()
