import enum
import json
import os
import random
import string
import subprocess
import urllib.parse
import billmgr.crypto
import billmgr.db
import billmgr.logger

from datetime import datetime
from collections import namedtuple
from functools import lru_cache
from billmgr.exception import XmlException
from billmgr import BINARY_NAME

logger = billmgr.logger.get_logger("billmgr_misc")


@lru_cache(maxsize=1)
def __get_measures_relations():
    measures_relations = {}

    measures_query = billmgr.db.db_query(
        "SELECT m1.intname as cur_measure, m1.relation, m2.intname AS less_measure "
        "FROM measure m1 "
        "LEFT JOIN measure m2 on m1.lessmeasure=m2.id")

    for relation_row in measures_query:
        measures_relations[relation_row["cur_measure"]] = (relation_row["less_measure"], relation_row["relation"])
        logger.debug("%s = %s * %s", relation_row["cur_measure"], relation_row["relation"], relation_row["less_measure"])

    return measures_relations


def Mgrctl(func: str, **kwargs):
    """
    Вызов mgrctl для billmgr
        @func - функция для вызова
        @kwargs - набор параметров для передачи в ф-цию
    """
    kwargs["out"] = "bjson"

    command = [
        "sbin/mgrctl",
        "-m",
        "billmgr",
        func,
        *[f'{k}={v}' for k, v in kwargs.items()],
    ]

    logger.debug(f'Run command `{" ".join(command)}`')

    result = subprocess.run(
        command,
        cwd="/usr/local/mgr5",
        env=dict(os.environ, SSH_CONNECTION=BINARY_NAME),  # заменяем локальный IP на название обработчика
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout = result.stdout.decode().strip(' \n\t')
    stderr = result.stderr.decode().strip(' \n\t')

    logger.debug(f'Return code: {result.returncode}'
                 '\nstdout: ' + stdout +
                 '\nstderr: ' + stderr)

    if result.returncode != 0:
        raise XmlException("process", "not_zero_code", stderr)

    response = json.loads(stdout)
    if "error" in response:
        raise XmlException("process", "error", stdout)

    return response


def get_item_processingmodule(item):
    return billmgr.db.db_query("SELECT processingmodule FROM item WHERE id = %s", item)[0]['processingmodule']


def iteminfo(iid: int):
    return billmgr.db.db_query(
        "SELECT it.intname, pm.module, i.id, i.remoteid, i.parent, i.processingmodule, i.lastpricelist, "
        "p.intname as pricelist_intname, i.pricelist, i.period, i.status, i.expiredate, i.opendate, "
        "i.account AS account_id, a.name AS account_name, p.project, i.cost, "
        "i.autosuspend, i.employeesuspend, i.abusesuspend "
        "FROM item i "
        "LEFT JOIN account a ON a.id = i.account "
        "JOIN pricelist p on p.id=i.pricelist "
        "JOIN itemtype it on it.id=p.itemtype "
        "LEFT JOIN processingmodule pm on pm.id=i.processingmodule "
        "WHERE i.id = %s", iid)[0]


def itemparams(iid: int, alias: dict = None):
    def __replace_name(param: str):
        return (alias or {}).get(param, param)

    itemparams_rows = billmgr.db.db_query("SELECT intname, value FROM itemparam WHERE item = %s", iid)
    itemcryptedparam_rows = billmgr.db.db_query("SELECT intname, value FROM itemcryptedparam WHERE item= %s", iid)

    return {
        **{__replace_name(x["intname"]): x["value"] for x in itemparams_rows},
        **{__replace_name(x["intname"]): billmgr.crypto.decrypt_value(x["value"]) for x in itemcryptedparam_rows}
    }


def itemips(iid: int, where_statement: list = None, private_ip : bool = False):
    args = [iid]
    where_condition = f"WHERE item.id=%s AND itemtype.intname='{'privateip' if private_ip else 'ip'}'"

    for w in where_statement or []:
        where_condition += f" AND {w[0]}"
        args += w[1]

    ip_query_str = "SELECT ip.id, ip.name " \
                   "FROM ip " \
                   "JOIN item addon ON ip.item=addon.id " \
                   "JOIN item ON addon.parent=item.id " \
                   "JOIN pricelist ON addon.pricelist=pricelist.id " \
                  f"JOIN itemtype ON pricelist.itemtype=itemtype.id {where_condition}"

    return billmgr.db.db_query(ip_query_str, *args)


def itemaddons(iid: int):
    class AddonTypes(enum.Enum):
        atUnknown = "0"
        atBoolean = "1"
        atInteger = "2"
        atEnum = "3"

    class BillTypes(enum.Enum):
        btUnknown = "0"
        btNone = "1"
        btOrdered = "2"
        btStat = "3"
        btCompound = "4"
        btCalc = "5"
        btManual = "10"

    TRIAL = "-100"

    addonmaxtrial = "IFNULL(a.addonmaxtrial, p.addonmaxtrial)"
    is_trial = "(SELECT period FROM item WHERE id=i.id) = " + TRIAL

    addons = billmgr.db.db_query(
       "SELECT DISTINCT "
            "t.intname, @tmp_value := "
           f"IF(p.addontype = {AddonTypes.atEnum.value}, IFNULL(ie.intname, pe.intname), "
              f"IF(p.addontype = {AddonTypes.atBoolean.value}, IFNULL(a.boolvalue, p.addonbool), "
                 f"IF(p.billtype = {BillTypes.btStat.value}, IFNULL(a.addonmax, p.addonmax), "
                     "IF(a.intvalue IS NULL, IF(a.addonlimit IS NULL, IFNULL(p.addonlimit, 0), a.addonlimit), "
                        "IF(a.addonlimit IS NULL, IFNULL(p.addonlimit, 0) + IFNULL(a.intvalue, 0), IFNULL(a.addonlimit, 0) + IFNULL(a.intvalue, 0)))))) AS not_trial_value, "
           f"IF({is_trial} AND p.addontype = {AddonTypes.atInteger.value} AND {addonmaxtrial} IS NOT NULL AND {addonmaxtrial} < @tmp_value, {addonmaxtrial}, @tmp_value) AS value, "
           f"IF(p.addontype = {AddonTypes.atInteger.value}, m.intname, '') AS measure, "
            "IFNULL(a.enumerationitem, p.enumerationitem) as enumerationitem, p.addontype AS pricelist_addontype, p.intname AS pricelist_intname "
        "FROM pricelist p "
        "JOIN item i ON i.id = %s "
        "LEFT JOIN item a on a.pricelist = p.id and a.parent = i.id "
        "LEFT JOIN itemtype t on p.itemtype = t.id "
        "LEFT JOIN enumerationitem ie on a.enumerationitem = ie.id "
        "LEFT JOIN enumerationitem pe on p.enumerationitem=pe.id "
        "LEFT JOIN measure m on m.id=p.measure "
        "WHERE p.parent = i.pricelist "
          "AND p.active = 'on' "
         f"AND p.billtype!={BillTypes.btCompound.value} "
         f"AND p.billtype!={BillTypes.btManual.value} "
          "AND (p.compound IS NULL OR a.id IS NOT NULL)"
        ,
        iid
    )

    addon_values = {}
    Addon = namedtuple("Addon", "value measuere")
    for addon in addons:
        intname = addon["pricelist_intname"] or addon["intname"]
        addon_values[intname] = Addon(addon["value"], addon["measure"])

    return addon_values


@lru_cache(maxsize=16)
def get_module_params(module: int):
    moduleparams_rows = billmgr.db.db_query(
        "SELECT intname, value FROM processingparam WHERE processingmodule = %s", module)
    modulecryptedparams_rows = billmgr.db.db_query(
        "SELECT intname, value FROM processingcryptedparam WHERE processingmodule = %s", module)

    return {
        **{x["intname"]: x["value"] for x in moduleparams_rows},
        **{x["intname"]: billmgr.crypto.decrypt_value(x["value"]) for x in modulecryptedparams_rows}
    }


@lru_cache(maxsize=8)
def get_relation(from_measure: str, to_measure: str):
    """
    Ищет отношение между переданными единицами измерения
    Поиск производится от большей единицы измерения к меньшей

    :param from_measure: исходная единица измерения
    :param to_measure: целевая единица измерения
    :return: отношения между единицами измерения
    """

    def _look_relation(measure1, measure2):
        measures_rel = __get_measures_relations()
        relation = 1
        current_measure = measure1

        while True:
            less_measure = measures_rel.get(current_measure)
            if less_measure is None:  # не нашли единицу измерения
                return None

            less_measure_name, less_measure_relation = less_measure
            if less_measure_name is None:  # дошли до самой маленькой единицы измерения - значит отношение отсутствует
                return None

            relation *= int(less_measure_relation)
            if less_measure_name == measure2:
                return relation

            current_measure = less_measure_name

    if from_measure == to_measure:
        return 1

    measure_relation = _look_relation(from_measure, to_measure)
    if measure_relation is not None:
        return measure_relation

    measure_relation = _look_relation(to_measure, from_measure)
    if measure_relation is not None:
        return 1 / measure_relation

    raise XmlException("no_relation", from_measure, to_measure)


def sync_itemtype_param(module: int, param_name: str, param_values: dict):
    param_id = billmgr.db.db_query(
        "SELECT itp.id "
        "FROM itemtype it "
        "LEFT JOIN itemtypeparam itp ON itp.itemtype=it.id "
        "WHERE it.intname='vds' AND itp.intname = %s", param_name)[0]["id"]

    billing_param_values = billmgr.db.db_query(
        "SELECT itpv.id, itpv.intname "
        "FROM itemtype it "
        "JOIN itemtypeparam itp ON itp.itemtype=it.id "
        "JOIN itemtypeparamvalue itpv ON itpv.itemtypeparam=itp.id "
        "JOIN processingmodule2itemtypeparamvalue pm2itpv ON "
        "pm2itpv.itemtypeparamvalue = itpv.id AND pm2itpv.processingmodule = %s "
        "WHERE it.intname='vds' AND itp.id = %s "
        "GROUP BY itpv.id", module, param_id)

    billing_param_values_dict = {param["intname"]: param["id"] for param in billing_param_values}

    for delete_value in set(billing_param_values_dict) - set(param_values):
        Mgrctl("itemtype.param.value.processing.suspend", elid=module, plid=billing_param_values_dict[delete_value])

    locale_names = billmgr.db.db_query("SELECT IF(langcode='en', 'name', CONCAT('name_', langcode)) AS name FROM locale")
    for add_value in set(param_values) - set(billing_param_values_dict):
        Mgrctl("itemtype.param.value.sync",
               itemtype="vds",
               module=module,
               param=param_name,
               value=add_value,
               disablepricelists="on",
               **{name["name"]: param_values[add_value] for name in locale_names})

    # for update_value in (param for param in set(param_values) ^ set(billing_param_values_dict)):
    #     logger.info("Update %s", update_value)


def save_param(iid: int, param: str, value: str, crypted: bool = False):
    """
    Добавить параметр в услугу
    :param iid: идентификатор услуги
    :param param: имя параметра
    :param value: значение параметра
    :param crypted: значение должно быть зашифрованно
    """
    logger.info("item#%d: Save %sparam '%s=%s'", iid, "crypted " if crypted else "", param, value)
    Mgrctl("service.saveparam",
           sok="ok",
           elid=iid,
           **{param: value},
           crypted="on" if crypted else "off")


def drop_param(iid: int, param: str):
    """
    Удалить параметр у услуги
    :param iid: идентификатор услуги
    :param param: имя параметра
    """
    logger.info("item#%d: Drop param '%s'", iid, param)
    Mgrctl("service.dropparam",
           sok="ok",
           elid=iid,
           name=param)


def set_service_status(iid: int, status: str):
    """
    Установить статус услуги
    :param iid: идентификатор услуги
    :param status: статус
    """
    logger.info("item#%d: Set status '%s'", iid, status)
    Mgrctl("service.setstatus",
           elid=iid,
           service_status = status,
           sok="ok")


def set_service_expiredate(iid: int, date: str):
    """
    Установить дату окончания действия услуги
    :param iid: идентификатор услуги
    :param date: дата окончания действия
    """
    logger.info("item#%d: Set expiredate '%s'", iid, date)
    Mgrctl("service.setexpiredate",
           elid=iid,
           expiredate = date,
           sok="ok")


def insert_stat(iid: int, stat_date: datetime, param: str, value: str, measure: str, summarize_duplication: bool = True):
    query = billmgr.db.get_first_record("SELECT id FROM measure m WHERE m.intname = %s", measure)
    measure_id = ""
    if query:
        measure_id = query["id"]
    else:
        measure_id = "null"

    duplication = ""
    if summarize_duplication:
        duplication = "value + "

    query = billmgr.db.query_with_no_records_dict(
        "INSERT INTO itemstat(item, statdate, param, value, measure)"
                "VALUES(%(item)s, %(statdate)s, %(param)s, %(value)s, %(measure)s)"
            "ON DUPLICATE KEY UPDATE param = %(param)s, value = " + duplication + " %(value)s, measure = %(measure)s",
        item = str(iid),
        statdate = stat_date.strftime("%Y-%m-%d"),
        param = param,
        value = value,
        measure = measure_id,
        duplication = duplication
        )


def save_ip(ip_id: int, ip: str, netmask: str = "", gateway: str = "", domain: str=""):
    new_ip_id = Mgrctl(
        "service.ip.add",
        sok="ok",
        elid=ip_id,
        ip=ip,
        mask=netmask,
        gateway=gateway,
        domain=domain
    )["model"]["ip.id"]

    return new_ip_id

def commit_ip(ip_id):
    Mgrctl("service.ip.add.commit", sok="ok", elid=ip_id)

def del_ip(ip_id):
    Mgrctl("service.ip.del", sok="ok", elid=ip_id)


def save_runningoperation_error(runningoperation: int, error: str):
    Mgrctl("runningoperation.edit", sok="ok", elid=runningoperation, errorxml=error)


def postopen(iid: int, **kwargs):
    logger.info("Postopen %d", iid)
    Mgrctl("vds.open", elid=iid, sok="ok", **kwargs)


def postreopen(iid: int, **kwargs):
    logger.info("Postreopen %d", iid)
    Mgrctl("service.postreopen", elid=iid, sok="ok", **kwargs)


def postopeninterrupt(iid: int, **kwargs):
    logger.info("Postopeninterrupt %d", iid)
    Mgrctl("service.postopeninterrupt", elid=iid, sok="ok", **kwargs)


def postprolong(iid: int, **kwargs):
    logger.info("Postopen %d", iid)
    Mgrctl("service.postprolong", elid=iid, sok="ok", **kwargs)


def postclose(iid: int):
    logger.info("Postclose %d", iid)
    Mgrctl("service.postclose", elid=iid, sok="ok")


def poststat(iid: int, date: str):
    logger.info("Poststat %d %s", iid, date)
    Mgrctl("service.poststat", elid=iid, date=date)


def postsetparam(iid: int):
    logger.info("Postsetparam %d", iid)
    Mgrctl("service.postsetparam", elid=iid, sok="ok")


def postresume(iid: int):
    logger.info("Postresume %d", iid)
    Mgrctl("service.postresume", elid=iid, sok="ok")


def postsuspend(iid: int):
    logger.info("Postsuspend %d", iid)
    Mgrctl("service.postsuspend", elid=iid, sok="ok")


def poststart(iid: int):
    logger.info("Poststart %d", iid)
    Mgrctl("service.poststart", elid=iid, sok="ok")


def postreboot(iid: int):
    logger.info("Postreboot %d", iid)
    Mgrctl("service.postreboot", elid=iid, sok="ok")


def posthardreboot(iid: int):
    logger.info("Posthardreboot %d", iid)
    Mgrctl("service.posthardreboot", elid=iid, sok="ok")


def set_manual_rerun(runningoperation: int, **kwargs):
    Mgrctl("runningoperation.setmanual", elid=runningoperation, sok="ok", **kwargs)


def create_manual_task(iid: int, runningoperation: int, command: str, **kwargs):
    set_manual_rerun(runningoperation)

    task_type = Mgrctl("task.gettype", operation=command, item=iid)["model"]["task_type"]
    if task_type:
        Mgrctl("task.edit", item=iid, runningoperation=runningoperation, type=task_type, sok="ok", **kwargs)



def random_string(length: int):
    return "".join(random.Random().sample(string.ascii_letters + string.digits, length))


def get_server_url(iid: int):
    billurl = billmgr.db.db_query(
        "SELECT p.billurl "
        "FROM item i "
        "JOIN pricelist pl ON pl.id = i.pricelist "
        "JOIN project p ON p.id = pl.project "
        "WHERE i.id= %s", iid)[0]["billurl"]

    if not billurl:
        billurl = billmgr.db.db_query("SELECT billurl FROM project WHERE IFNULL(billurl, '') != '' LIMIT 1")[0]["billurl"]

    if billurl.endswith("/billmgr"):
        billurl = billurl.rsplit("/", 1)[0]

    return billurl


def url_encode(text: str):
    return urllib.parse.quote_plus(text)

def generate_domain(iid: int):
    DEFAULT_TEMPLATE = "@USERNAME@.example.com"
    template = billmgr.db.get_first_record(
        "SELECT IFNULL(plp.value, %s) as tmpl, u.name, it.intname "
        "FROM item i "
        "JOIN user u ON u.account = i.account "
        "JOIN pricelist pl ON pl.id = i.pricelist "
        "JOIN itemtype it ON it.id = pl.itemtype "
        "LEFT JOIN pricelistparam plp ON plp.intname = 'freedomain' AND pl.id = plp.pricelist "
        "WHERE i.id = %s", DEFAULT_TEMPLATE, iid)

    domain = template["tmpl"]
    return domain.replace("@USERNAME@", template["name"].strip().split("@")[0])\
                 .replace("@TYPE@", template["intname"])\
                 .replace("@ID@", str(iid))