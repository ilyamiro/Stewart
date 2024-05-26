import logging

from rich.logging import RichHandler
from rich.traceback import install

# installing rich traceback as default
install()


class Log(logging.Logger):
    """
    Subclass for Stewart Logging System
    """

    def __init__(self):
        super().__init__("Stewart", level=logging.NOTSET)  # Initializing the parent class
        self._setup_logger()  # Setting logger up

    def _setup_logger(self):
        """
        Set logger parameters
        """
        # Using RichHandler from rich 13.6.0 for useful and beautiful logging
        handler = RichHandler(
            log_time_format="%Y-%b-%d %H:%M:%S",  # Setting time format
            markup=True,  # Enable rich mark up for flexible logs
            rich_tracebacks=True  # Enables beautiful tracebacks
        )
        handler.setFormatter(logging.Formatter(fmt="%(message)s"))  # Setting message formatting
        self.addHandler(handler)  # Adding RichHandler

    def info(self, msg, **kwargs):
        """
        Custom info message
        """
        if not self.disabled:
            super().info(msg=f"[bold white]{msg}[/]", **kwargs)

    def warning(self, msg, **kwargs):
        """
        Custom warning message
        """
        super().warning(msg=f"[orange]{msg}[/]", **kwargs)

    def error(self, msg, **kwargs):
        """
        Custom error message
        """
        super().error(msg=f"[bold red]{msg}[/]", **kwargs)

    def debug(self, msg, **kwargs):
        """
        Custom debug message
        """
        if not self.disabled:
            super().debug(f"[blue i]{msg}[i]", **kwargs)

    def disable(self):
        """
        Disable console logging
        """
        self.disabled = True

    def enable(self):
        """
        Enable console logging back to its original state
        """
        self.disabled = False
