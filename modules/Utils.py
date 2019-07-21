import json
import logging
import sqlite3

import requests

from modules.Argparse_chaturbatebot import args

bot_path = args["working_folder"]


def handle_exception(e: Exception) -> None:
    """

    :param Exception e: The exception to handle
    """
    logging.error(e, exc_info=True)


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ValueError('Boolean value expected.')


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


def is_model_viewable(model: str) -> bool:
    """
    Checks if you can see the model live (without any privilege)

    :param string model: The model's name
    :rtype: bool
    """
    target = f"https://en.chaturbate.com/api/chatvideocontext/{model}"
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36', }
    response = requests.get(target, headers=headers)

    if b"It's probably just a broken link, or perhaps a cancelled broadcaster." in response.content:  # check if models still exists
        return False
    else:
        response = json.loads(response.content)

    if "status" not in response and response != "error":
        if response["room_status"] == "offline" or response["room_status"] == "away" or response["room_status"] == "private" or response["room_status"] == "hidden":
            return False
    elif "status" in response:  # avoid keyerror
        if response["status"] == 401:
            return False
    elif response == "error":
        return False
    return True
