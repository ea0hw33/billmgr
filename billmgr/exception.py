import billmgr.logger
import xml.etree.ElementTree as ET
import traceback

logger = billmgr.logger.get_logger("billmgr_exception")


def _backtrace():
    return traceback.format_exc()


def log_backtrace():
    """
    Добавляет backtrace в файл логов
    """
    logger.extinfo("%s", _backtrace())


class XmlException(Exception):
    """
    XML исключение
        @param err_type - тип исключения
        @param err_object - объект, действия над которым вызвали исключение, или имя подтипа
        @param err_value - значение
    """

    def __init__(self, err_type: str, err_object="", err_value=""):
        self.params = {}
        self.err_type = err_type
        self.err_object = err_object
        self.err_value = err_value
        self.add_param("value", err_value)

        message = f"Type: '{self.err_type}' Object: '{self.err_object}' Value: '{self.err_value}'"
        super().__init__(message)

        logger.error("%s", message)

    def add_param(self, name: str, value: str):
        self.params[name] = value

    def as_xml(self):
        """
        Получить строку с ошибкой в XML-формат
        :return: ошибка в формате xml
        """
        doc = ET.Element('doc')
        error = ET.SubElement(doc, 'error')
        error.set("type", self.err_type)
        error.set("object", self.err_object)

        for param in self.params:
            param_node = ET.SubElement(error, "param")
            param_node.text = self.params[param]
            param_node.set("name", param)

        return ET.tostring(doc, encoding="unicode")

    def as_module_error(self):
        """
        Получить информацию об ошибке c бэктрейсом для отображения в текущей операции
        :return: подробности ошибки в xml формате
        """
        doc = ET.Element('doc')
        error = ET.SubElement(doc, 'error')
        error.set("type", self.err_type)
        error.set("object", self.err_object)
        error.set("value", self.err_value)
        ET.SubElement(error, 'backtrace').text = _backtrace()

        return ET.tostring(doc, encoding="unicode")