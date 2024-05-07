import billmgr.logger as logging


MODULE = 'Test-pay'
logging.init_logging('pmtestpayment')
logger = logging.get_logger('pmtestpayment')


class PaymentModule:
    @abstractmethod
    def CheckPay(self):
        pass