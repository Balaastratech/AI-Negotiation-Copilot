import logging
import logging.config
from asgi_correlation_id.context import correlation_id
from pythonjsonlogger import jsonlogger

class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = correlation_id.get()
        return True

def get_logging_config(log_level: str = "INFO"):
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "correlation_id": {
                "()": CorrelationIdFilter,
            },
        },
        "formatters": {
            "json": {
                "()": jsonlogger.JsonFormatter,
                "format": "%(asctime)s %(levelname)s [%(name)s] [%(correlation_id)s] %(message)s",
            },
            "frontend_json": {
                "()": jsonlogger.JsonFormatter,
                "format": "%(asctime)s %(levelname)s [%(name)s] [%(correlation_id)s] %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "filters": ["correlation_id"],
                "level": log_level,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/app.log",
                "maxBytes": 1024 * 1024 * 5,  # 5 MB
                "backupCount": 5,
                "formatter": "json",
                "filters": ["correlation_id"],
                "level": log_level,
            },
            "frontend_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/frontend.log",
                "maxBytes": 1024 * 1024 * 5,  # 5 MB
                "backupCount": 5,
                "formatter": "frontend_json",
                "level": log_level,
            },
        },
        "loggers": {
            "frontend": {
                "handlers": ["frontend_file"],
                "level": log_level,
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": log_level,
        },
    }

def setup_logging(log_level: str = "INFO"):
    config = get_logging_config(log_level)
    logging.config.dictConfig(config)

