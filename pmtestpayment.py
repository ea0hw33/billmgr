#!/usr/bin/python3
import hashlib
import json
import requests
import payment
import billmgr.db
import billmgr.exception

import billmgr.logger as logging
import keypairdb

import xml.etree.ElementTree as ET

MODULE = 'payment'
logging.init_logging('pmtestpayment')
logger = logging.get_logger('pmtestpayment')

class TestPaymentModule(payment.PaymentModule):
    def __init__(self):
        super().__init__()

        self.remote_url = "https://securepay.tinkoff.ru/v2/GetState"
        self.features[payment.FEATURE_CHECKPAY] = True
        self.features[payment.FEATURE_REDIRECT] = True
        self.features[payment.FEATURE_NOT_PROFILE] = True
        self.features[payment.FEATURE_PMVALIDATE] = True

        self.params[payment.PAYMENT_PARAM_PAYMENT_SCRIPT] = "/mancgi/testpayment"


    # в тестовом примере валидация проходит успешно, если
    # Идентификатор терминала = TinkoffBankTest, пароль терминала = TinkoffBankTest
    def PM_Validate(self, xml : ET.ElementTree):
        logger.info("run pmvalidate")

        # мы всегда можем вывести xml в лог, чтобы изучить, что приходит :)
        logger.info(f"xml input: {ET.tostring(xml.getroot(), encoding='unicode')}")

        terminalkey_node = xml.find('./terminalkey')
        terminalpsw_node = xml.find('./terminalpsw')
        terminalkey = terminalkey_node.text if terminalkey_node is not None else ''
        terminalpsw = terminalpsw_node.text if terminalpsw_node is not None else ''

        if terminalkey != 'TinkoffBankTest' or terminalpsw != 'TinkoffBankTest':
            raise billmgr.exception.XmlException('wrong_terminal_info')


    # в тестовом примере получаем необходимые платежи
    # и переводим их все в статус 'оплачен'
    def CheckPay(self):
        logger.info("run checkpay")

        # получаем список платежей в статусе оплачивается
        # и которые используют обработчик pmtestpayment
        payments = billmgr.db.db_query(f'''
            SELECT p.id FROM payment p
            JOIN paymethod pm
            WHERE module = 'pmtestpayment' AND p.status = {payment.PaymentStatus.INPAY.value}
        ''')
        

        for p in payments:
            logger.info(p)
            paymentid = keypairdb.get_pair_by_elid(p['id'])[1]
            logger.info(paymentid)
            token = "TinkoffBankTest" + paymentid + "TinkoffBankTest"
            
            data = {
            "TerminalKey": "TinkoffBankTest",
            "PaymentId": paymentid,
            "Token": str(hashlib.sha256(token.encode()).hexdigest())
            }
            
            
            response = requests.post(self.remote_url, json=data)
            json_data = json.loads(response.text)
            
            logger.info(json_data)
            
            if json_data['Status'] == "CONFIRMED":
                logger.info(f"change status for payment {p['id']}")
                payment.set_paid(p['id'], '', f"external_{p['id']}")


TestPaymentModule().Process()
