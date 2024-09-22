import colorlog
import logging

# Create a logger object
logger = colorlog.getLogger(__name__)

# Set the logging level using logging.INFO instead of colorlog.INFO
logger.setLevel(logging.INFO)

# Create a handler and set the formatter with colorlog's ColoredFormatter
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))

# Add the handler to the logger
logger.addHandler(handler)
