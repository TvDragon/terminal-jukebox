import logging
import re

logger = logging.getLogger(__name__)

def setup():
    if logger.handlers:
        return
    
    f_handler = logging.FileHandler("terminal-jukebox.log", encoding='utf-8')
    f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    f_handler.setFormatter(f_format)
    logger.addHandler(f_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False    # Prevents propagation of info to stdout/stderr in terminal

def log_msg(message: str) -> None:
    "Write a message the file logger."
    logger.info(message)

def log_warn(message: str) -> None:
    logger.warning(message)

def log_error(message: str) -> None:
    logger.error(message)