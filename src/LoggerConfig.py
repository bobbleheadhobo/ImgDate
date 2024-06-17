import logging

def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup as many loggers as you want"""

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Check if the logger already has handlers to prevent duplication
    if not logger.hasHandlers():
        handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        stream_handler = logging.StreamHandler()
        logger.addHandler(stream_handler)

    return logger
