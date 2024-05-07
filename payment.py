import os
os.chdir("/usr/local/mgr5")

from abc import ABC, abstractmethod
from billmgr.misc import MgrctlXml
import billmgr.db
import billmgr.exception
from enum import Enum
import sys
import xml.etree.ElementTree as ET
import billmgr.logger as logging

MODULE = 'payment'
logging.init_logging('pmtestpayment')
logger = logging.get_logger('pmtestpayment')


def parse_cookies(rawdata):
    from http.cookies import SimpleCookie
    cookie = SimpleCookie()
    cookie.load(rawdata)
    return {k: v.value for k, v in cookie.items()}


# cтатусы платежей в том виде, в котором они хранятся в БД
# см. https://docs.ispsystem.ru/bc/razrabotchiku/struktura-bazy-dannyh#id-Структурабазыданных-payment
class PaymentStatus(Enum):
    NEW = 1
    INPAY = 2
    PAID = 4
    FRAUD = 7
    CANCELED = 9


# перевести платеж в статус "оплачивается"
def set_in_pay(payment_id: str, info: str, externalid: str):
    '''
    payment_id - id платежа в BILLmanager
    info       - доп. информация о платеже от платежной системы
    externalid - внешний id на стороне платежной системы
    '''
    MgrctlXml('payment.setinpay', elid=payment_id, info=info, externalid=externalid)


# перевести платеж в статус "мошеннический"
def set_fraud(payment_id: str, info: str, externalid: str):
    MgrctlXml('payment.setfraud', elid=payment_id, info=info, externalid=externalid)


# перевести платеж в статус "оплачен"
def set_paid(payment_id: str, info: str, externalid: str):
    MgrctlXml('payment.setpaid', elid=payment_id, info=info, externalid=externalid)


# перевести платеж в статус "отменен"
def set_canceled(payment_id: str, info: str, externalid: str):
    MgrctlXml('payment.setcanceled', elid=payment_id, info=info, externalid=externalid)


class PaymentCgi(ABC):
    # основной метод работы cgi
    # абстрактный метод, который необходимо переопределить в конкретной реализации
    @abstractmethod
    def Process(self):
        pass

    def __init__(self):
        self.elid = ""           # ID платежа
        self.auth = ""           # токен авторизации
        self.mgrurl = ""         # url биллинга
        self.pending_page = ""   # url страницы биллинга с информацией об ожидании зачисления платежа
        self.fail_page = ""      # url страницы биллинга с информацией о неуспешной оплате
        self.success_page = ""   # url страницы биллинга с информацией о успешной оплате

        self.payment_params = {}   # параметры платежа
        self.paymethod_params = {} # параметры метода оплаты
        self.user_params = {}      # параметры пользователя

        self.lang = None           # язык используемый у клиента

        # пока поддерживаем только http метод GET
        if os.environ['REQUEST_METHOD'] != 'GET':
            raise NotImplemented

        # по-умолчанию используется https
        if os.environ['HTTPS'] != 'on':
            raise NotImplemented

        # получаем id платежа, он же elid
        input_str = os.environ['QUERY_STRING']
        for key, val in [param.split('=') for param in input_str.split('&')]:
            if key == "elid":
                self.elid = val

        # получаем url к панели
        self.mgrurl =  "https://" + os.environ['HTTP_HOST'] + "/billmgr"
        self.pending_page = f'{self.mgrurl}?func=payment.pending'
        self.fail_page = f'{self.mgrurl}?func=payment.fail'
        self.success_page = f'{self.mgrurl}?func=payment.success'

        # получить cookie
        cookies = parse_cookies(os.environ['HTTP_COOKIE'])
        _, self.lang = cookies["billmgrlang5"].split(':')

        # получить токен авторизации
        self.auth = cookies["billmgrses5"]

        # получить параметры платежа и метода оплаты
        # см. https://docs.ispsystem.ru/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-plateyonyh-sistem#id-Созданиемодулейплатежныхсистем-CGIскриптымодуля
        payment_info_xml = MgrctlXml("payment.info", elid = self.elid, lang = self.lang)
        for elem in payment_info_xml.findall("./payment/"):
            self.payment_params[elem.tag] = elem.text
        for elem in payment_info_xml.findall("./payment/paymethod/"):
            self.paymethod_params[elem.tag] = elem.text
        
        logger.info('paymethod_params= ', self.paymethod_params)  
        logger.info('payment_params= ',self.payment_params)      

        # получаем параметры пользователя
        # получаем с помощью функции whoami информацию о авторизованном пользователе
        # в качестве параметра передаем auth - токен сессии
        user_node = MgrctlXml("whoami", auth = self.auth).find('./user')
        if user_node is None:
            raise billmgr.exception.XmlException("invalid_whoami_result")

        # получаем из бд данные о пользователях
        user_query = billmgr.db.get_first_record(
            " SELECT u.*, IFNULL(c.iso2, 'EN') AS country, a.registration_date"
            " FROM user u"
			" LEFT JOIN account a ON a.id=u.account"
			" LEFT JOIN country c ON c.id=a.country"
			" WHERE u.id = '" +  user_node.attrib['id'] + "'"
        )
        if user_query:
            self.user_params["user_id"] = user_query["id"];
            self.user_params["phone"] = user_query["phone"];
            self.user_params["email"] = user_query["email"];
            self.user_params["realname"] = user_query["realname"];
            self.user_params["language"] = user_query["language"];
            self.user_params["country"] = user_query["country"];
            self.user_params["account_id"] = user_query["account"];
            self.user_params["account_registration_date"] = user_query["registration_date"];


# фичи платежного модуля
# полный список можно посмотреть в документации
# https://docs.ispsystem.ru/bc/razrabotchiku/sozdanie-modulej/sozdanie-modulej-plateyonyh-sistem#id-Созданиемодулейплатежныхсистем-Основнойскриптмодуля
FEATURE_REDIRECT = "redirect"               # нужен ли переход в платёжку для оплаты
FEATURE_CHECKPAY = "checkpay"               # проверка статуса платежа по крону
FEATURE_NOT_PROFILE = "notneedprofile"      # оплата без плательщика (позволит зачислить платеж без создания плательщика)
FEATURE_PMVALIDATE = "pmvalidate"           # проверка введённых данных на форме создания платежной системы
FEATURE_PMUSERCREATE = "pmusercreate"       # для ссылки на регистрацию в платежке

# параметры платежного модуля
PAYMENT_PARAM_PAYMENT_SCRIPT = "payment_script" # mancgi/<наименование cgi скрипта>


class PaymentModule(ABC):
    # Абстрактные методы CheckPay и PM_Validate необходимо переопределить в своей реализации
    # см пример реализации в pmtestpayment.py

    # проверить оплаченные платежи
    # реализация --command checkpay
    # здесь делаем запрос в БД, получаем список платежей в статусе "оплачивается"
    # идем в платежку и проверяем прошли ли платежи
    # если платеж оплачен, выставляем соответствующий статус c помощью функции set_paid
    @abstractmethod
    def CheckPay(self):
        pass

    # вызывается для проверки введенных в настройках метода оплаты значений
    # реализация --command pmvalidate
    # принимается xml с веденными на форме значениями
    # если есть некорректные значения, то бросаем исключение billmgr.exception.XmlException
    # если все значение валидны, то ничего не возвращаем, исключений не бросаем
    @abstractmethod
    def PM_Validate(self, xml):
        pass

    def __init__(self):
        self.features = {}
        self.params = {}

    # возращает xml с кофигурацией метода оплаты
    # реализация --command config
    def Config(self):
        config_xml = ET.Element('doc')
        feature_node = ET.SubElement(config_xml, 'feature')
        for key, val in self.features.items():
            ET.SubElement(feature_node, key).text = "on" if val else "off"

        param_node = ET.SubElement(config_xml, 'param')
        for key, val in self.params.items():
            ET.SubElement(param_node, key).text = val

        return config_xml

    def Process(self):
        try:
            # лайтовый парсинг аргументов командной строки
            # ожидаем --command <наименование команды>
            if len(sys.argv) < 3:
                raise billmgr.exception.XmlException("invalid_arguments")

            if sys.argv[1] != "--command":
                raise Exception("invalid_arguments")

            command = sys.argv[2]

            if command == "config":
                xml = self.Config()
                if xml is not None:
                    ET.dump(xml)

            elif command == FEATURE_PMVALIDATE:
                self.PM_Validate(ET.parse(sys.stdin))

            elif command == FEATURE_CHECKPAY:
                self.CheckPay()

        except billmgr.exception.XmlException as exception:
            sys.stdout.write(exception.as_xml())

