import logging

from gmail_automation.logging_utils import get_logger, setup_logging


def test_setup_logging_writes_file(tmp_path):
    log_file = tmp_path / "out.log"
    root = logging.getLogger()
    old_handlers = root.handlers[:]
    try:
        setup_logging(level="DEBUG", log_file=log_file)
        logger = get_logger(__name__)
        logger.info("hello")
        logger.debug("world")
        logging.shutdown()
        content = log_file.read_text()
        assert "hello" in content and "world" in content
    finally:
        root.handlers.clear()
        root.handlers.extend(old_handlers)
        root.setLevel(logging.WARNING)
