import atexit
import mysql.connector
import billmgr.logger
import billmgr.config

from functools import lru_cache
from billmgr.exception import XmlException

logger = billmgr.logger.get_logger("billmgr_db")


@lru_cache(maxsize=64)
def __get_db_con():
    try:
        db_conn = mysql.connector.connect(
            host=billmgr.config.get_param("DBHost"),
            user=billmgr.config.get_param("DBUser"),
            password=billmgr.config.get_param("DBPassword"),
            database=billmgr.config.get_param("DBName"),
            pool_size=10,
            pool_reset_session=False, # Нет поддержки в mysql версии ниже 5.7.2
            autocommit=True
        )

    except mysql.connector.Error as err:
        raise XmlException("db", err) from err
    else:
        atexit.register(db_conn.close)

    return db_conn

def db_execute(query: str, *params):
    logger.extinfo(f"'{query}'", *[f"'{param}'" for param in params])

    with __get_db_con().cursor(buffered=True, dictionary=True) as cur:
        cur.execute(query, params)


def db_query(query: str, *params):
    logger.extinfo(f"'{query}'", *[f"'{param}'" for param in params])

    with __get_db_con().cursor(buffered=True, dictionary=True) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        logger.debug("Query result: %s", rows)
        return rows


def get_first_record(query: str, *params):
    rows = db_query(query, *params)
    if rows:
        return rows[0]

    return None


def query_with_no_records(query: str, *params):
    logger.extinfo(f"'{query}'", *[f"'{param}'" for param in params])

    with __get_db_con().cursor(buffered=True) as cur:
        cur.execute(query, params)


def db_query_dict(query: str, **params):
    log_params = params.copy()
    for param in log_params:
        log_params[param] = f"'{log_params[param]}'"
    if log_params:
        logger.extinfo(f"'{query}'", log_params)
    else:
        logger.extinfo(f"'{query}'")

    with __get_db_con().cursor(buffered=True, dictionary=True) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        logger.debug("Query result: %s", rows)
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
        logger.extinfo(f"'{query}'", log_params)
    else:
        logger.extinfo(f"'{query}'")

    with __get_db_con().cursor(buffered=True) as cur:
        cur.execute(query, params)

def db_query_cursor_dict(query: str, **params):
    log_params = params.copy()
    for param in log_params:
        log_params[param] = f"'{log_params[param]}'"
    if log_params:
        logger.extinfo(f"'{query}'", log_params)
    else:
        logger.extinfo(f"'{query}'")

    cursor = __get_db_con().cursor(buffered=True, dictionary=True)
    cursor.execute(query, params)
    return cursor
