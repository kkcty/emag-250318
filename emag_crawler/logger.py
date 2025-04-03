"""日志"""

from pathlib import Path
from sys import stderr

from loguru import logger
from scraper_utils.utils.time_util import now_str


_cwd = Path.cwd()


_ENABLE_DEBUG = True
"""是否控制台输出 DEBUG 级别的日志"""
_ENABLE_FILE = True
"""是否允许日志输出到文件"""

logger.remove()

logger.add(
    stderr,
    format=(
        '[<green>{time:HH:mm:ss}</green>] [<level>{level:.3}</level>] '
        '[<cyan>{name}</cyan>:<cyan>{line}</cyan>] >>> '
        '<level>{message}</level>'
    ),
    filter=lambda record: len(record['extra']) == 0,
    level='DEBUG' if _ENABLE_DEBUG else 'INFO',
)

if _ENABLE_FILE is True:
    _log_dir = _cwd / 'logs/'
    _log_dir.mkdir(exist_ok=True, parents=True)
    _log_file = _log_dir / f'{now_str('%Y_%m_%d-%H_%M_%S')}.log'

    logger.add(
        _log_file,
        format=(
            '[<green>{time:HH:mm:ss}</green>] [<level>{level:.3}</level>] '
            '[<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>] >>> '
            '<level>{message}</level>'
        ),
        filter=lambda record: len(record['extra']) == 0,
        enqueue=True,
    )
