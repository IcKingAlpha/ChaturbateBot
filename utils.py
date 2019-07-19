import logging
import sqlite3
import os

bot_path = os.getcwd()


def handle_exception(e: Exception) -> None:
    """

    :param Exception e: The exception to handle
    """
    logging.error(e, exc_info=True)


def exec_query(query: str, db_path: str = bot_path) -> None:
    """Executes a db query

    :param str db_path: The database path
    :param str query: The sql query to execute

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
