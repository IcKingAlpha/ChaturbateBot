import logging
import sqlite3
import datetime

from modules.argparse_code import args

bot_path = args["working_folder"]
last_spam_dict = {}
temp_ban_chatid_dict = {}


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


def exec_query(query: str, db_path: str = bot_path) -> None:
    """Executes a SQL query

    :param db_path: The database path
    :param query: The SQL query to execute

    """

    # Open database connection
    db = sqlite3.connect(db_path + '/database.db')
    # prepare a cursor object using cursor() method
    cursor = db.cursor()
    # Prepare SQL query to INSERT a record into the database.
    try:
        # Execute the SQL command
        cursor.execute(query)
        # Commit your changes in the database
        db.commit()
    except Exception as e:
        # Rollback in case there is any error
        handle_exception(e)
        db.rollback()
    # disconnect from server
    db.close()


def retrieve_query_results(query: str, db_path: str = bot_path) -> list:
    """
    Returns a list containing the SQL query results

    :param query: The SQL query to execute
    :param db_path: The database path
    :rtype: list
    :return: A list containing the query results
    """
    db = sqlite3.connect(db_path + '/database.db')
    cursor = db.cursor()
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception as e:
        handle_exception(e)
        return []  # return empty list
    finally:
        db.close()


def admin_check(chatid: str) -> bool:
    """
    Checks if user is present in the admin database

    :rtype: bool
    :param str chatid: chatid
    :return: True if admin, False if not
    """
    admin_list = []
    results = retrieve_query_results("SELECT * FROM ADMIN")
    for row in results:
        admin_list.append(row[0])

    if str(chatid) not in admin_list:
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
