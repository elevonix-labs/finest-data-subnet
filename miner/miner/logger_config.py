import logging
from colorama import Fore, init

# Initialize colorama
init(autoreset=True)

# Custom logging formatter to add colors and emojis
class ColoredFormatter(logging.Formatter):
    COLORS = {
        "CRITICAL": Fore.BLUE,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
    }

    def format(self, record):
        log_level = record.levelname
        color = self.COLORS.get(log_level, Fore.WHITE)
        message = super().format(record)
        return f"{color} {message}"

# Configure logging with color logging for console output
logger = logging.getLogger(__name__)  # Use __name__ to ensure it's module-specific

# Check if the logger already has handlers to avoid adding them multiple times
if not logger.hasHandlers():
    logger.setLevel(logging.INFO)

    # Console handler with colored formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)

    # File handler with standard formatter including time
    file_handler = logging.FileHandler("commit_processing.log", mode="w")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)
