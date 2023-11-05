from typing import Any
import os

import logging, logging.handlers
from rich.logging import RichHandler

import yaml

import re
import hashlib
import base64 as b64


_WHITESPACE_RX = re.compile(r"\s")

from .config import Configuration

log = logging.getLogger('util')

def get_package_dir():
    return os.path.dirname(__file__)

def get_package_data_dir():
    return os.path.join(get_package_dir(), '_data')

def load_yaml(filename: str):
    """Load a YAML file."""
    with open(filename) as fp:
        data = yaml.load(fp.read(), Loader=yaml.Loader)

    return data

def save_yaml(data: Any, filename: str):
    """Save data to a YAML file."""
    raise Exception("deprecated!")
    with open(filename, 'w') as fp:
        yaml.dump(
            data,
            fp,
            # default_style='|',
            Dumper=yaml.SafeDumper,
        )


def get_config(filename="config.yaml"):
    """Load YAML configuration from disk."""
    with open(filename) as fp:
        cfg = yaml.load(fp.read(), Loader=yaml.Loader)

    return cfg

def setup_logging(cfg: Configuration):
    """Setup a basic logging mechanism.

    @type  config: dict
    @param config: dict instance with the following keys in section
      C{logging}: C{loglevel}, C{logfile}, C{format}, C{max_size}, C{backup_count}
      and C{use_console}.
    """
    # Create the root logger
    logger = logging.getLogger()

    if logger.handlers:
        msg = "Logging handlers have already been configured. Skipping setup."
        logger.warn(msg)
        return

    log_cfg = cfg.settings["logging"]

    level = log_cfg.get("level", "info")

    if level == 'NONE':
        return

    level = getattr(logging, level.upper())
    logger.setLevel(level)

    filename = log_cfg.get("file", f"default.log")
    format_ = log_cfg.get("format", "%(levelname)-8s - %(message)s")
    datefmt = log_cfg.get("datefmt", "%H:%M:%S")
    bytes_ = log_cfg.get("max_size", 1024)
    backup_count = log_cfg.get("backup_count", 5)

    # Make sure the directory exists
    if os.path.isabs(filename):
        logdir = os.path.dirname(filename)
    else:
        logdir = cfg.log_dir

    if not os.path.exists(logdir):
        os.makedirs(logdir)

    filename = os.path.join(logdir, filename)

    # Create RotatingFileHandler
    rfh = logging.handlers.RotatingFileHandler(
        filename,
        maxBytes=1024 * bytes_,
        backupCount=backup_count
    )
    rfh.setLevel(level)
    rfh.setFormatter(logging.Formatter(format_))
    logger.addHandler(rfh)

    # Check what to do with the console output ...
    if log_cfg["use_console"]:
        # ch = logging.StreamHandler(sys.stdout)
        # ch.setLevel(level)
        # ch.setFormatter(CustomFormatter(format_, datefmt))
        ch = RichHandler(
            rich_tracebacks=False,
            log_time_format=datefmt,
        )

        logger.addHandler(ch)

    # Disable
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    # Finally, capture all warnings using the logging mechanism.
    logging.captureWarnings(True)

    return filename


def log_app_header(name):
    """Write application header to the log."""
    log = logging.getLogger()
    log.info(f"#" * 80)
    log.info(f"#[orange3]{name:^78}[/]#", extra={'markup': True})
    log.info(f"#" * 80)





def base64(s):
    """
    Base64 encode a string, removing all whitespace from the output.
    """
    encoded = b64.encodebytes(s.encode()).decode()
    return _WHITESPACE_RX.sub("", encoded)  # remove all whitespace


def sha256(s):
    """
    Encode a string into its SHA256 hex digest
    """
    return hashlib.sha256(s.encode()).hexdigest()