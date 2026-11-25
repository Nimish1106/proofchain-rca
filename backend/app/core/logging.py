import logging


def configure_logging(app_env: str) -> None:
    """
    Configure application-wide logging.
    """
    log_level = (
        logging.DEBUG
        if app_env == "development"
        else logging.INFO
    )
    logging.basicConfig(
        level=log_level,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a named application logger.
    """
    return logging.getLogger(name)
