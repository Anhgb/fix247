"""
Structured JSON logging with trace ID support.
NFR-10: Log có cấu trúc, trace ID theo đơn.
"""
import logging
import sys
import uuid
from contextvars import ContextVar

import structlog

# Context var for trace ID (set per request)
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    return trace_id_var.get() or str(uuid.uuid4())


def generate_trace_id() -> str:
    tid = str(uuid.uuid4())
    trace_id_var.set(tid)
    return tid


def setup_logging(log_level: str = "INFO") -> None:
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)
