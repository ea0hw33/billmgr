import logging
import sys
from enum import Enum
from billmgr import BINARY_NAME


class Level(Enum):
    DEBUG = logging.DEBUG
    EXTINFO = 15
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


def log_level():
    conf_level = Level.EXTINFO.value
    try:
        with open("etc/debug.conf", "r") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                if BINARY_NAME == "":
                    continue
                tmp_line = line.replace("\t", " ")
                if BINARY_NAME in tmp_line:
                    tmp_line = tmp_line.strip()
                    tmp_chunks = tmp_line.strip().rsplit(" ", 1)
                    try:
                        conf_level = int(tmp_chunks[-1])
                    except Exception:
                        pass
    except:
        pass
    # Система логирования в COREmanager устроена немного иначе, поэтому задаем таблицу соответствия
    SUPPORTED_LEVELS = {
        9: Level.DEBUG.value,
        6: Level.EXTINFO.value,
        5: Level.INFO.value,
        4: Level.WARNING.value,
        3: Level.ERROR.value,
        2: Level.CRITICAL.value,
    }
    return SUPPORTED_LEVELS.get(conf_level, Level.EXTINFO.value)


logfile_name = ""


def init_logging(logfile: str):
    logging.addLevelName(Level.EXTINFO.value, Level.EXTINFO.name)
    global logfile_name
    logfile_name = logfile


__loggers = {}


def get_logger(name):
    if name not in __loggers:
        __loggers[name] = Logger(name)
    return __loggers[name]


class Logger:
    def __init__(self, name):
        self.__logger = logging.getLogger(name)
        self.__logger.setLevel(log_level())
        if logfile_name:
            handler = logging.FileHandler(f"/usr/local/mgr5/lib/python/var/logs.log")
        else:
            handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)-15s [%(process)d] %(name)s %(color)s %(levelname)s %(message)s\033[0m"
        )
        handler.setFormatter(formatter)
        self.__logger.addHandler(handler)

    def __log(self, level: int, msg: str, *args):
        COLORS = {
            Level.DEBUG: "\033[1;33m",
            Level.EXTINFO: "\033[1;36m",
            Level.INFO: "\033[1;32m",
            Level.WARNING: "\033[1;35m",
            Level.ERROR: "\033[1;31m",
            Level.CRITICAL: "\033[1;31m",
        }

        self.__logger.log(level.value, msg, *args, extra={"color": COLORS[level]})

    def critical(self, msg, *args):
        self.__log(Level.CRITICAL, msg, *args)

    def error(self, msg, *args):
        self.__log(Level.ERROR, msg, *args)

    def warning(self, msg, *args):
        self.__log(Level.WARNING, msg, *args)

    def info(self, msg, *args):
        self.__log(Level.INFO, msg, *args)

    def extinfo(self, msg, *args):
        self.__log(Level.EXTINFO, msg, *args)

    def debug(self, msg, *args):
        self.__log(Level.DEBUG, msg, *args)
