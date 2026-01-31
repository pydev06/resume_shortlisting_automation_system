import logging
import sys
from .config import get_settings


def setup_logging():
    settings = get_settings()
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("resume_shortlisting")
    return logger


logger = logging.getLogger("resume_shortlisting")
