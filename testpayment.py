import billmgr.logger as logging


MODULE = 'Test-pay'
logging.init_logging('testpayment')
logger = logging.get_logger('testpayment')


from payment import PaymentCgi
from payment.utils import *
from mgr.mgrrpc import *
from mgr.mgrdate import *
from mgr.mgrhash import *
from mgr.mgrstream import *
from stdstd import *


class TestPayment(PaymentCgi):
    def __init__(self):
        super().__init__("Test-pay", "Test-pay")

    def ValidateAuth(self):
        return True

    def Process(self):
        payment_form_param = {
            "ik_ia_u": self.GetServerUrl() + "/mancgi/testpay",
            "ik_suc_u": self.GetSuccessPage(),
            "ik_fal_u": self.GetFailPage(),
            "ik_co_id": self.Method("ik_co_id"),
            "ik_pm_no": self.Payment("id"),
            "ik_cur": str.Upper(self.Currency("iso")),
            "ik_am": self.Payment("amount"),
            "ik_am_ed": "0",
            "ik_desc": self.Payment("description"),
            "ik_ia_m": "POST",
            "ik_suc_m": "GET",
            "ik_fal_m": "GET",
        }

        ik_sign_str = ""
        for k, v in payment_form_param.items():
            ik_sign_str += str(v) + ":"

        ik_sign_str += ":" + self.Method("secret")

        ik_sign = str(mgr_hash.md5(ik_sign_str))

        form_str = """
<html>
<head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
        <link rel="shortcut icon" href="billmgr.ico" type="image/x-icon"/>
        <script language="JavaScript">
                function DoSubmit() {
                        document.interkassaform.submit();
                }
        </script>
</head>
<body onload="DoSubmit()">
        <form name="interkassaform" action="https://sci.interkassa.com/" method="post">
                <input type="hidden" name="ik_sign" value="{ik_sign}">
{form_params}
        </form>
</body>
</html>
""".format(
            ik_sign=ik_sign,
            form_params="\n".join(
                [
                    '<input type="hidden" name="{k}" value="{v}">'.format(k=k, v=v)
                    for k, v in payment_form_param.items()
                ]
            ),
        )

        print(form_str)

InterkassaPayment