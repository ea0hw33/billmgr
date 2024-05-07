import warnings
warnings.filterwarnings(action='ignore',message='Python 3.6 is no longer supported')

import base64

from functools import lru_cache
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

import billmgr.config

@lru_cache(maxsize=1)
def _get_decoder():
    with open(billmgr.config.get_param("CryptKey")) as key_file:
         return serialization.load_pem_private_key(
            str.encode(key_file.read()),
            password=None
        )


@lru_cache(maxsize=1)
def _get_encoder():
    return _get_decoder()


def decrypt_value(value: str):
    """
    Декодируем строку, используя приватный ключ
    :param value: строка, которую необходимо расшифровать
    :return: расшифрованная строка
    """
    decryted_value = _get_decoder().decrypt(base64decode_b(value.encode("UTF-8")), padding.PKCS1v15())
    return decryted_value.decode('UTF-8')


def crypt_value(value: str):
    """
    Шифруем строку, используя публичный ключ
    :param value: строка, которую необходимо зашифровать
    :return: зашифрованная строка
    """
    return base64encode(_get_encoder().public_key().encrypt(value.encode('UTF-8'), padding.PKCS1v15()))


def base64decode(value: str):
    """
    Декодирование base64 строки
    :param value: строка, которую необходимо декодировать
    :return: декодированная строка
    """
    return base64decode_b(value).decode('UTF-8')


def base64encode(value: str):
    """
    Кодирование строки в base64
    :param value: строка, которую необходимо закодировать
    :return: закодированная строка
    """
    return base64encode_b(value).decode('UTF-8')


def base64decode_b(value: str):
    """
    Декодирование base64 строки
    :param value: строка, которую необходимо декодировать
    :return: декодированная строка в виде bytes
    """
    if isinstance(value, bytes):
        return base64.b64decode(value)

    return base64.b64decode(value.encode('UTF-8'))


def base64encode_b(value: str):
    """
    Кодирование строки в base64
    :param value: строка, которую необходимо закодировать
    :return: закодированная строка в виде bytes
    """
    if isinstance(value, bytes):
        return base64.b64encode(value)

    return base64.b64encode(value.encode('UTF-8'))


def x509decode(value: str):
    """
    Декодирование x509 строки
    :param value: строка, которую необходимо декодировать
    :return: декодированная строка (csr)
    """
    return x509.load_pem_x509_csr(value.encode('UTF-8'), default_backend())