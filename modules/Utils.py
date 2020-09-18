import datetime
import logging

from modules.alchemy import Alchemy, Admin
from modules.argparse_code import args

bot_path = args["working_folder"]
last_spam_dict = {}
temp_ban_chatid_dict = {}
alchemy_instance: Alchemy


def handle_exception(e: Exception) -> None:
    """

    :param Exception e: The exception to handle
    """
    logging.error(e, exc_info=True)


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1', 'enable', 'enabled'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0', 'disable', 'disabled'):
        return False
    else:
        raise ValueError('Boolean value expected.')


def bool_to_status(value: bool) -> str:
    """
    Checks the bool and returns "Enabled" if True, "Disabled" if False

    :param value: The bool to convert
    :return: "Enabled" if True, "Disabled" if False
    """
    if value:
        return "Enabled"
    else:
        return "Disabled"


def sanitize_username(username: str) -> str:
    """
    Sanitizes an username for http requests

    :param username: The username to sanitize
    :return: The sanitized username
    """
    return username.lower().replace("/", "")


def admin_check(chatid: str) -> bool:
    """
    Checks if user is present in the admin database

    :rtype: bool
    :param str chatid: chatid
    :return: True if admin, False if not
    """
    admin_list = []
    results: Admin = alchemy_instance.session.query(Admin).filter_by(chat_id=str(chatid)).first()

    if results is None:
        return False
    else:
        return True


def set_last_spam_date(chatid: str, date: datetime.datetime):
    last_spam_dict[chatid] = date


def get_last_spam_date(chatid: str) -> (datetime.datetime, None):
    try:
        return last_spam_dict[chatid]
    except KeyError:
        return None


def temp_ban_chatid(chatid: str, ban_time: float):
    temp_ban_chatid_dict[chatid] = datetime.datetime.now() + datetime.timedelta(0, ban_time)


def remove_temp_chatid_ban(chatid: str):
    del temp_ban_chatid_dict[chatid]


def is_chatid_temp_banned(chatid: str) -> bool:
    if chatid in list(temp_ban_chatid_dict.keys()):
        if (datetime.datetime.now() - temp_ban_chatid_dict[chatid]).total_seconds() >= 0:
            remove_temp_chatid_ban(chatid)
            return False
        else:
            return True
    else:
        return False
