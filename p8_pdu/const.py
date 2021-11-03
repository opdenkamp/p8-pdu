""" constant definitions for p8_pdu """
from enum import Enum

__version__ = '0.1.0'
UDP_PORT = 18768


class P8LoginState(Enum):
    NOT_LOGGED_IN = 0
    LOGIN_SENT = 1
    WAITING_PWD_PROMPT = 2
    PWD_SENT = 3
    WAITING_LOGIN = 4
    LOGGED_IN = 5
    WRONG_PASSWORD = 6

