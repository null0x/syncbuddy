import logging

logger = logging.getLogger("SyncMate")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()  
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)