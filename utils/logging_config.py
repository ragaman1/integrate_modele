#utils/logging_config.py
import logging

def setup_logging():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
        level=logging.INFO
    )
    return logging.getLogger(__name__)

logger = setup_logging()