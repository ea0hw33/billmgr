import json
import os
import subprocess
import xml.etree.ElementTree as ET

import billmgr.db
from billmgr.exception import XmlException
from billmgr import BINARY_NAME
from billmgr.logger import get_logger

MODULE = "billmgr_misc"

def MgrctlXml(func: str, **kwargs):
    """
    Вызов mgrctl для billmgr, возвращает результат в xml
        @func - функция для вызова
        @kwargs - набор параметров для передачи в ф-цию
    """
    kwargs["out"] = "xml"

    command = [
        "sbin/mgrctl",
        "-m",
        "billmgr",
        func,
        *[f"{k}={v}" for k, v in kwargs.items()],
    ]

    get_logger(MODULE).debug(f'Run command `{" ".join(command)}`')

    result = subprocess.run(
        command,
        cwd="/usr/local/mgr5",
        env=dict(
            os.environ, SSH_CONNECTION=BINARY_NAME
        ),  # заменяем локальный IP на название обработчика
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout = result.stdout.decode().strip(" \n\t")
    stderr = result.stderr.decode().strip(" \n\t")

    get_logger(MODULE).debug(
        f"Return code: {result.returncode}"
        "\nstdout: " + stdout + "\nstderr: " + stderr
    )

    if result.returncode != 0:
        raise XmlException("process", "not_zero_code", stderr)

    xml = ET.fromstring(stdout)

    error = xml.find('./error')
    if error is not None and 'type' in error.attrib and 'object' in error.attrib:
        raise XmlException(error.attrib['type'], error.attrib['object'])
    if error is not None and 'type' in error.attrib:
        raise XmlException(error.attrib['type'])

    return xml


def Mgrctl(func: str, **kwargs):
    """
    Вызов mgrctl для billmgr, возвращает результат в json
        @func - функция для вызова
        @kwargs - набор параметров для передачи в ф-цию
    """
    kwargs["out"] = "bjson"

    command = [
        "sbin/mgrctl",
        "-m",
        "billmgr",
        func,
        *[f"{k}={v}" for k, v in kwargs.items()],
    ]

    get_logger(MODULE).debug(f'Run command `{" ".join(command)}`')

    result = subprocess.run(
        command,
        cwd="/usr/local/mgr5",
        env=dict(
            os.environ, SSH_CONNECTION=BINARY_NAME
        ),  # заменяем локальный IP на название обработчика
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout = result.stdout.decode().strip(" \n\t")
    stderr = result.stderr.decode().strip(" \n\t")

    get_logger(MODULE).debug(
        f"Return code: {result.returncode}"
        "\nstdout: " + stdout + "\nstderr: " + stderr
    )

    if result.returncode != 0:
        raise XmlException("process", "not_zero_code", stderr)

    response = json.loads(stdout)
    if "error" in response:
        raise XmlException("process", "error", stdout)

    return response

