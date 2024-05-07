#!/usr/bin/env python
import datetime
import re
import sys
import getopt
import xml.etree.ElementTree as ET
import billmgr.logger as logging
import billmgr.db as db
from lib.python.billmgr.thirdparty import requests


MODULE = 'Test-pay'
logging.init_logging('payment')
logger = logging.get_logger('payment')

# Adding PHP include
sys.path.append("/usr/local/mgr5/lib/python/billmgr")
__MODULE__ = "pmTest-pay"

class Cgi:
    def handler(argv):
        longopts = ["command=", "payment=", "amount="]

        try:
            options, _ = getopt.getopt(argv, "", longopts)
        except getopt.GetoptError as err:
            print(str(err))
            sys.exit(2)

        for opt, arg in options:
            if opt == "--command":
                command = arg
                logger.info("command " + arg)

                if command == "config":
                    config_xml = ET.Element("config")
                    feature_node = ET.SubElement(config_xml, "feature")

                    # feature_node.append(ET.Element("refund", "on"))  # If refund supported
                    # feature_node.append(ET.Element("transfer", "on"))  # If transfer supported
                    feature_node.append(ET.Element("redirect", "on"))  # If redirect supported
                    # feature_node.append(ET.Element("noselect", "on"))  # If noselect supported
                    feature_node.append(ET.Element("notneedprofile", "on"))  # If notneedprofile supported

                    feature_node.append(ET.Element("pmtune", "on"))
                    feature_node.append(ET.Element("pmvalidate", "on"))

                    # feature_node.append(ET.Element("crtune", "on"))
                    feature_node.append(ET.Element("crvalidate", "on"))
                    feature_node.append(ET.Element("crset", "on"))
                    feature_node.append(ET.Element("crdelete", "on"))

                    # feature_node.append(ET.Element("rftune", "on"))
                    # feature_node.append(ET.Element("rfvalidate", "on"))
                    # feature_node.append(ET.Element("rfset", "on"))

                    # feature_node.append(ET.Element("tftune", "on"))
                    # feature_node.append(ET.Element("tfvalidate", "on"))
                    # feature_node.append(ET.Element("tfset", "on"))

                    param_node = ET.SubElement(config_xml, "param")
                    param_node.append(ET.Element("payment_script", "/mancgi/qiwipullpayment.php"))

                    print(ET.tostring(config_xml).decode())
                elif command == "pmtune":
                    paymethod_form = ET.fromstring(sys.stdin.read())
                    pay_source = ET.SubElement(paymethod_form, "slist")
                    pay_source.set("name", "pay_source")
                    pay_source.append(ET.Element("msg", "qw"))
                    pay_source.append(ET.Element("msg", "mobile"))
                    sys.stdout.write(ET.tostring(paymethod_form).decode())
                elif command == "pmvalidate":
                    paymethod_form = ET.fromstring(sys.stdin.read())
                    logger.debug(ET.tostring(paymethod_form).decode())

                    API_ID = paymethod_form.find("API_ID").text
                    PRV_ID = paymethod_form.find("PRV_ID").text

                    logger.debug(API_ID)   
                    logger.debug(PRV_ID)

                    if not re.match("^\d+$", API_ID):
                        raise Exception("value", "API_ID", API_ID)

                    if not re.match("^\d+$", PRV_ID):
                        raise Exception("value", "PRV_ID", PRV_ID)

            elif command == "crdelete":
                payment_id = options['payment']
                info = db.get_first_record(f"SELECT info FROM payment WHERE id={payment_id}")

                out = requests.post("https://https://securepay.tinkoff.ru/v2/Init/" + info.payment[0].paymethod[1].PRV_ID + "/bills/" + payment_id,
                                {"status": "rejected"},
                                info.payment[0].paymethod[1].API_ID,
                                info.payment[0].paymethod[1].API_PASSWORD)

                out_xml = ET.fromstring(out)
                if out_xml.result_code == "0" or out_xml.result_code == "210":
                    db.db_execute(f"DELETE FROM payment WHERE id={payment_id}")
            elif command == "crvalidate":
                payment_form = ET.fromstring(sys.stdin.read())

                ok = ET.SubElement(payment_form, "ok")
                ok.set("type", "5")
                ok.text = "/mancgi/qiwipullpayment.php?elid=" + payment_form.payment_id

                print(ET.tostring(payment_form).decode())
            elif command == "crset":
                payment_id = options['payment']
                info = db.get_first_record(f"SELECT info FROM payment WHERE id={payment_id}")

                phone = str(info.payment[0].phone)
                phone = re.sub(r'[^0-9]', '', phone)

                lifetime = datetime.datetime.now()
                if info.payment[0].paymethod[1].autoclearperiod != "":
                    lifetime += datetime.timedelta(days=int(info.payment[0].paymethod[1].autoclearperiod))
                else:
                    lifetime += datetime.timedelta(days=30)

                input_data = {
                    "user": "tel:+" + phone,
                    "amount": str(info.payment[0].paymethodamount),
                    "ccy": str(info.payment[0].currency[1].iso),
                    "pay_source": str(info.payment[0].paymethod[1].pay_source),
                    "prv_name": str(info.payment[0].project.name),
                    "comment": str(info.payment[0].number),
                    "lifetime": lifetime.strftime("%Y-%m-%dT%H:%M:%S"),
                }

                logger.debug(str(input_data))

                out = requests.put("https://qiwi.com/api/v2/prv/" + info.payment[0].paymethod[1].PRV_ID + "/bills/" + payment_id,
                                input_data,
                                info.payment[0].paymethod[1].API_ID,
                                info.payment[0].paymethod[1].API_PASSWORD)

                out_xml = ET.fromstring(out)
                if out_xml.result_code == "0":
                    LocalQuery("payment.setinpay", {"elid": payment_id})
                else:
                    raise Exception("payment_process_error", "", "", {"error_msg": out_xml.description})
            else:
                raise Exception("unknown command")
