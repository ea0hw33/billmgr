import atexit
import os.path
import warnings

warnings.filterwarnings(action="ignore", message="Python 3.6 is no longer supported")
import mysql.connector  # noqa: E402
from functools import lru_cache  # noqa: E402
from mysql.connector.errors import ProgrammingError as DBDriverException  # noqa: E402

import billmgr.config  # noqa: E402
from billmgr.exception import XmlException  # noqa: E402
from billmgr.logger import get_logger  # noqa: E402


MODULE = "billmgr_db"


@lru_cache(maxsize=64)
def __get_db_con():
    try:
        host = billmgr.config.get_param("DBHost")
        unix_socket = None
        if host == "localhost":
            unix_socket = next(
                filter(
                    lambda s: os.path.exists(s),
                    [
                        "/var/run/mysqld/mysqld.sock",
                        "/var/lib/mysql/mysql.sock",
                        "/tmp/mysql.sock",
                    ],
                ),
                None,
            )

        db_conn = mysql.connector.connect(
            host=host,
            unix_socket=unix_socket,
            user=billmgr.config.get_param("DBUser"),
            password=billmgr.config.get_param("DBPassword"),
            database=billmgr.config.get_param("DBName"),
            pool_size=10,
            pool_reset_session=False,  # Не поддерживается в mysql ниже 5.7.2
            autocommit=True,
            # use_pure=True, иначе могут быть проблемы при подключении через Python C Extension
            # при использовании на сервере СУБД из сторонних репозиториев
            use_pure=True
        )

    except mysql.connector.Error as err:
        raise XmlException("db", err) from err
    else:
        atexit.register(db_conn.close)

    return db_conn


def db_query(query: str, *params):
    get_logger(MODULE).extinfo(f"'{query}'", *[f"'{param}'" for param in params])

    with __get_db_con().cursor(buffered=True, dictionary=True) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        get_logger(MODULE).debug("Query result: %s", rows)
        return rows


def get_first_record(query: str, *params):
    rows = db_query(query, *params)
    if rows:
        return rows[0]

    return None


def query_with_no_records(query: str, *params):
    get_logger(MODULE).extinfo(f"'{query}'", *[f"'{param}'" for param in params])

    with __get_db_con().cursor(buffered=True) as cur:
        cur.execute(query, params)


def db_query_dict(query: str, **params):
    log_params = params.copy()
    for param in log_params:
        log_params[param] = f"'{log_params[param]}'"
    if log_params:
        get_logger(MODULE).extinfo(f"'{query}'", log_params)
    else:
        get_logger(MODULE).extinfo(f"'{query}'")

    with __get_db_con().cursor(buffered=True, dictionary=True) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        get_logger(MODULE).debug("Query result: %s", rows)
        return rows


def get_first_record_dict(query: str, **params):
    rows = db_query_dict(query, **params)
    if rows:
        return rows[0]

    return None


def query_with_no_records_dict(query: str, **params):
    log_params = params.copy()
    for param in log_params:
        log_params[param] = f"'{log_params[param]}'"
    if log_params:
        get_logger(MODULE).extinfo(f"'{query}'", log_params)
    else:
        get_logger(MODULE).extinfo(f"'{query}'")

    with __get_db_con().cursor(buffered=True) as cur:
        cur.execute(query, params)


def db_query_cursor_dict(query: str, **params):
    log_params = params.copy()
    for param in log_params:
        log_params[param] = f"'{log_params[param]}'"
    if log_params:
        get_logger(MODULE).extinfo(f"'{query}'", log_params)
    else:
        get_logger(MODULE).extinfo(f"'{query}'")

    cursor = __get_db_con().cursor(buffered=True, dictionary=True)
    cursor.execute(query, params)
    return cursor


def escape_value(val: str):
    return __get_db_con().converter.escape(val)


def escape_and_quote_value(val: str):
    return "'" + escape_value(val) + "'"
