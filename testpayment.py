#!/usr/bin/python3

import json
import requests
import payment
import sys

import billmgr.logger as logging
import keypairdb

MODULE = 'payment'
logging.init_logging('testpayment')
logger = logging.get_logger('testpayment')

class TestPaymentCgi(payment.PaymentCgi):
    
    def __init__(self, *args, **kwargs):
        self.remote_url = "https://securepay.tinkoff.ru/v2/Init"
        super(TestPaymentCgi, self).__init__(*args, **kwargs)
        
    
    def get_url_for_paying(self):
        
        data = {
        "TerminalKey": "TinkoffBankTest",
        "Amount": int(float(self.payment_params['paymethodamount']))*100,
        "OrderId": int(self.elid)*97,
        "Description": "Пополнение счета",
        "Token": self.auth,
        "DATA": {
            "Email": "sdf@gmail.com",
        },
        "Receipt": {
            "Email": "a@test.ru",
            "Phone": "+79031234567",
            "Taxation": "osn",
            "Items": [
            {
                "Name": "Пополнение счета",
                "Price": int(float(self.payment_params['paymethodamount']))*100,
                "Quantity": 1,
                "Amount": int(float(self.payment_params['paymethodamount']))*100,
                "Tax": "vat0"
            }
            ]
        }
        }
        logger.info(data)
        
        response = requests.post(self.remote_url,json = data)
        json_data = json.loads(response.text)
        
        return json_data
    
    def Process(self):
        # необходимые данные достаем из self.payment_params, self.paymethod_params, self.user_params
        # здесь для примера выводим параметры метода оплаты (self.paymethod_params) и платежа (self.payment_params) в лог
        logger.info(f"paymethod_params = {self.paymethod_params}")
        logger.info(f"payment_params = {self.payment_params}")
        logger.info(self.elid, self.auth, self)

        # переводим платеж в статус оплачивается
        payment.set_in_pay(self.elid, '', 'external_' + self.elid)

        json_data = self.get_url_for_paying()
        keypairdb.add_pair(self.elid,json_data['PaymentId'])
        
        logger.info(json_data)
        # url для перенаправления c cgi
        # здесь, в тестовом примере сразу перенаправляем на страницу BILLmanager
        # должны перенаправлять на страницу платежной системы
        redirect_url = json_data['PaymentURL'];
        # redirect_url = self.pending_page;
        # redirect_url = "https://securepayments.tinkoff.ru/ClKM0Bco"

        # формируем html и отправляем в stdout
        # таким образом переходим на redirect_url
        payment_form =  "<html>\n";
        payment_form += "<head><meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>\n"
        payment_form += "<link rel='shortcut icon' href='billmgr.ico' type='image/x-icon' />"
        payment_form += "	<script language='JavaScript'>\n"
        payment_form += "		function DoSubmit() {\n"
        payment_form += "			window.location.assign('" + redirect_url + "');\n"
        payment_form += "		}\n"
        payment_form += "	</script>\n"
        payment_form += "</head>\n"
        payment_form += "<body onload='DoSubmit()'>\n"
        payment_form += "</body>\n"
        payment_form += "</html>\n";

        logger.info(payment_form)
        sys.stdout.write(payment_form)


TestPaymentCgi().Process()
