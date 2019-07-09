# -*- coding: utf-8 -*-
import argparse
import json
import logging
import os
import os.path
import sqlite3
import threading
import time
import urllib.request
import requests
import datetime
from queue import Queue

from concurrent.futures import ThreadPoolExecutor

import telegram
from requests_futures.sessions import FuturesSession
from telegram.error import (BadRequest, ChatMigrated, NetworkError,
                            TelegramError, TimedOut, Unauthorized)
from telegram.ext import CommandHandler, Updater


ap = argparse.ArgumentParser()
ap.add_argument(
    "-k", "--key", required=True, type=str, help="Telegram bot api key. It's required in order to run this bot")
ap.add_argument(
    "-f",
    "--working-folder",
    required=False,
    type=str,
    default=os.getcwd(),
    help="Set the bot's working-folder. Default= ChaturbateBot.py's location")
ap.add_argument(
    "-t",
    "--time",
    required=False,
    type=float,
    default=0.3,
    help="Time wait between every connection made, in seconds. Default=0.3s")
ap.add_argument(
    "-threads",
    required=False,
    type=int,
    default=10,
    help="The number of multiple http connection opened at the same time to check chaturbate. Default=10")
ap.add_argument(
    "-l",
    "--limit",
    required=False,
    type=int,
    default=0,
    help="The maximum number of multiple users a person can follow, 0=unlimited")
ap.add_argument(
    "-r",
    "--remove",
    required=False,
    type=bool,
    default=True,
    help="Should the bot remove from the database anyone whom blocks it? default= true")
ap.add_argument(
    "-sentry",
    required=False,
    type=str,
    default="",
    help="Your sentry personal url")
ap.add_argument(
    "--admin-password",
    required=False,
    type=str,
    default="",
    help="The password to authorize yourself as an admin, disabled by default")
args = vars(ap.parse_args())


updater = Updater(token=args["key"])
dispatcher = updater.dispatcher

bot_path = args["working_folder"]
wait_time = args["time"]
sentry_key = args["sentry"]
http_threads = args["threads"]
user_limit = args["limit"]
auto_remove = args["remove"]
admin_pw = args["admin_password"]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO,filename=os.path.join(bot_path,"program_log.log"))


# enable sentry if sentry_key is passed as an argument
if sentry_key != "":
    import sentry_sdk
    sentry_sdk.init(sentry_key)

    def handle_exception(e: Exception) -> None:
        try:
         sentry_sdk.capture_exception()
        except Exception as e:
            logging.error(e,exc_info=True)
            sentry_sdk.capture_message("Sentry ha failato ad handlare l'exception"+"l'exception avvenuta è "+str(e))

else:

    def handle_exception(e: Exception) -> None:
        logging.error(e,exc_info=True)


def exec_query(query: str) -> None:
    """Executes a db query

    Parameters:

    query (str): The sql query to execute

    """

    # Open database connection
    db = sqlite3.connect(bot_path + '/database.db')
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


def risposta(sender: str, messaggio: str, bot, html: str=False) -> None:
    """Sends a message to a telegram user

    Parameters:

    sender (str): The chat id of the user who will receive the message

    messaggio (str): The message who the user will receive

    bot: telegram bot instance

    html (str): if html markdown should be enabled in the message


    """

    try:
        bot.send_chat_action(chat_id=sender, action="typing")
        if html == True:
            bot.send_message(chat_id=sender, text=messaggio,
                             parse_mode=telegram.ParseMode.HTML)
        else:
            bot.send_message(chat_id=sender, text=messaggio)
    except Unauthorized: #user blocked the bot
        if auto_remove == True:
            logging.info(f"{sender} blocked the bot, he's been removed from the database")
            exec_query(f"DELETE FROM CHATURBATE WHERE CHAT_ID='{sender}'")
    except Exception as e:
        handle_exception(e)


def admin_check(chatid: str) -> bool:
    """Checks if a chatid is present in the admin database

    Parameters:

    chatid (str): The chat id of the user who will be checked

    Returns:
    bool: the logic value of the check

    """

    admin_list = []

    db = sqlite3.connect(bot_path + '/database.db')
    cursor = db.cursor()

    sql = "SELECT * FROM ADMIN"
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            admin_list.append(row[0])
    except Exception as e:
        handle_exception(e)
    finally:
        db.close()

    if str(chatid) not in admin_list:
        return False
    else:
        return True



#region normal functions


def start(bot, update) -> None:
    risposta(
        update.message.chat.id,
        "/add username to add an username to check \n/remove username to remove an username\n(you can use /remove <b>all</b> to remove all models at once) \n/list to see which users you are currently following", bot, html=True
    )


def add(bot, update, args) -> None:
    chatid = update.message.chat_id
    username_message_list=[]
    if len(args) < 1:
            risposta(
                chatid,
                "You need to specify an username to follow, use the command like /add <b>username</b>\n You can also add multiple users at the same time by separating them using a comma, like /add <b>username1</b>,<b>username2</b>", bot, html=True
            )
            return
        # not lowercase usernames bug the api calls
    if len(args)>1:
        for username in args:
            if username!="":
                username_message_list.append(username.replace(" ","").replace(",",""))
    # len(args)==0 -> only one username or all in one line
    elif "," in args[0].lower():
        for splitted_username in args[0].lower().replace(" ","").rstrip().split(","):
            if splitted_username!="":
             username_message_list.append(splitted_username)
    else:
        username_message_list.append(args[0].lower())
    
    username_message_list=list(dict.fromkeys(username_message_list)) #remove duplicate usernames
    


    usernames_in_database = []
    db = sqlite3.connect(bot_path + '/database.db')
    cursor = db.cursor()
    # obtain present usernames
    sql = f"SELECT * FROM CHATURBATE WHERE CHAT_ID='{chatid}'"
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            usernames_in_database.append(row[0])
    except Exception as e:
        handle_exception(e)
    finally:
        db.close()


    # 0 is unlimited usernames
    if len(usernames_in_database)+len(username_message_list) > user_limit and (admin_check(chatid) == False != user_limit != 0):
        risposta(chatid,"You are trying to add more usernames than your limit permits, which is "+str(user_limit),bot)
        return

    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36', }
     
    for username in username_message_list:
        try:
            target = f"https://en.chaturbate.com/api/chatvideocontext/{username}"
            response = requests.get(target, headers=headers)

            #check if the response can be actually be parsed
            if b"It's probably just a broken link, or perhaps a cancelled broadcaster." in response.content: #check if models still exists
                risposta(chatid, f"{username} was not added because it doesn't exist", bot)
                return
            else:
                response_json = json.loads(response.content)

            # check for not existing models and errors
            if (("status" in response_json) and ("401" in str(response_json['status'])) and ("This room requires a password" not in str(response_json['detail']))):
    
                if "Room is deleted" in str(response_json['detail']):
    
                    risposta(
                        chatid, username +
                        " has not been added because room has been deleted", bot
                    )
                    logging.info(
                        username+
                        " has not been added because room has been deleted")
                if "This room has been banned" in str(response_json['detail']):
    
                    risposta(
                        chatid, username +
                        " has not been added because has been banned", bot)
                    logging.info(username+
                          " has not been added because has been banned")

            else:
                if username not in usernames_in_database:
                        exec_query(f"INSERT INTO CHATURBATE VALUES ('{username}', '{chatid}', 'F')")
                        if 'detail' in response_json:
                            if "This room requires a password" in str(response_json['detail']):
                                risposta(chatid, username + " uses a password for his/her room, it has been added but tracking could be unstable", bot)
                        else:
                            risposta(chatid, username + " has been added", bot)
                            logging.info(f'{chatid} added {username}')
                else:
                    risposta(chatid, f"{username} has already been added", bot)

        except Exception as e:
            handle_exception(e)
            risposta(chatid, f"{username} was not added because an error happened", bot)


def remove(bot, update, args) -> None:
    logging.info("remove")
    chatid = update.message.chat.id
    username_message_list = []
    usernames_in_database=[]

    if len(args) < 1:
            risposta(
                chatid,
                "You need to specify an username to follow, use the command like /remove <b>test</b>\n You can also remove multiple users at the same time by separating them using a comma, like /remove <b>username1</b>,<b>username2</b>", bot, html=True
            )
            return
    if len(args)>1:
        for username in args:
            if username!="":
                username_message_list.append(username.replace(" ","").replace(",",""))
    # len(args)==0 -> only one username or all in one line
    elif "," in args[0].lower():
        for splitted_username in args[0].lower().replace(" ","").rstrip().split(","):
            if splitted_username!="":
             username_message_list.append(splitted_username)
    else:
        username_message_list.append(args[0].lower())
    
    db = sqlite3.connect(bot_path + '/database.db')
    cursor = db.cursor()
    # obtain usernames in the database
    sql = f"SELECT * FROM CHATURBATE WHERE CHAT_ID='{chatid}'"
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            usernames_in_database.append(row[0])
    except Exception as e:
        handle_exception(e)
    finally:
        db.close()

    if "all" in username_message_list:
        exec_query(
           f"DELETE FROM CHATURBATE WHERE CHAT_ID='{chatid}'")
        risposta(chatid, "All usernames have been removed", bot)
    else:
        for username in username_message_list:
            if username in usernames_in_database:
                exec_query(f"DELETE FROM CHATURBATE WHERE USERNAME='{username}' AND CHAT_ID='{chatid}'")
                risposta(chatid, f"{username} has been removed", bot)
            else:
                risposta(chatid,f"You aren't following {username}", bot)   



def list_command(bot, update) -> None:
    chatid = update.message.chat.id
    username_list = []
    online_list = []
    username_dict = {}
    followed_users = ""
    db = sqlite3.connect(bot_path + '/database.db')
    cursor = db.cursor()
    sql = f"SELECT * FROM CHATURBATE WHERE CHAT_ID='{chatid}'"

    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            username_list.append(row[0])
            online_list.append(row[2])
    except Exception as e:
        handle_exception(e)
    else:  # else means that the code will get executed if an exception doesn't happen

        for x in range(0, len(username_list)):
            # dictionary with usernames and online_status
            username_dict.update({username_list[x]: online_list[x]})

        for username in sorted(username_dict):
            followed_users += username + ": "
            if username_dict[username] == "T":
                followed_users += "<b>online</b>\n"
            else:
                followed_users += "offline\n"
    finally:
        db.close()
    if followed_users == "":
        risposta(chatid, "You aren't following any user", bot)
    else:
        risposta(
            chatid, f"You are currently following these {len(username_list)} users:\n" +
            followed_users, bot, html=True)

#endregion

#region admin functions

def authorize_admin(bot, update, args) -> None:

    chatid = update.message.chat_id
    if len(args) != 1:
        risposta(
            chatid,
            "You need to specify the admin password, use the command like /authorize_admin <b>password</b>", bot, html=True
        )
        return
    elif admin_pw == "":
        risposta(
            chatid,
            "The admin is disabled, check your telegram bot configuration", bot
        )
        return
    if admin_check(chatid):
        risposta(chatid, "You already are an admin", bot)
    elif args[0] == admin_pw:
        exec_query(f"""INSERT INTO ADMIN VALUES ({chatid})""")
        risposta(chatid, "Admin enabled", bot)
        risposta(chatid, "Remember to disable the --admin-password if you want to avoid people trying to bruteforce this command", bot)
        logging.info(f"{chatid} got admin authorization")
    else:
        risposta(chatid, "The password is wrong", bot)


def send_message_to_everyone(bot, update, args) -> None:
    chatid = update.message.chat.id

    if admin_check(chatid) == False:
        risposta(chatid, "You're not authorized to do this", bot)
        return

    chatid_list = []
    message = ""
    start_time=datetime.datetime.now()


    logging.info(f"{chatid} started sending a message to everyone")

    sql = "SELECT DISTINCT CHAT_ID FROM CHATURBATE"
    try:
        db = sqlite3.connect(bot_path + '/database.db')
        cursor = db.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            chatid_list.append(row[0])
    except Exception as e:
        handle_exception(e)
    finally:
        db.close()

    for word in args:
        message += word+" "
    message = message[:-1]

    for x in chatid_list:
        risposta(x, message, bot)
    logging.info(f"{chatid} finished sending a message to everyone, took {(datetime.datetime.now()-start_time).total_seconds()} seconds")


#endregion

#region threads

def check_online_status() -> None:
    global updater
    bot = updater.bot
    while (1):
        

        username_list = []
        online_dict = {}
        chatid_dict = {}

        # create a dictionary with usernames and online using distinct
        sql = "SELECT DISTINCT USERNAME,ONLINE FROM CHATURBATE"
        try:
            db = sqlite3.connect(bot_path + '/database.db')
            cursor = db.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            for row in results:
                online_dict[row[0]]=row[1]
                #username row0
                #online row1
        except Exception as e:
            handle_exception(e)
        finally:
            db.close()
        
        #create username_list
        for username in online_dict.keys():
            username_list.append(username)
        



        # obtain chatid
        for username in username_list:
                chatid_list = []
                sql = f"SELECT CHAT_ID FROM CHATURBATE WHERE USERNAME='{username}'"
                try:
                            db = sqlite3.connect(bot_path + '/database.db')
                            cursor = db.cursor()
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            for row in results:
                                chatid_list.append(row[0])
                except Exception as e:
                            handle_exception(e)
                finally:
                            db.close()
                chatid_dict[username]=chatid_list            


        # Threaded function for queue processing.
        def crawl(q, response_dict):
            while not q.empty():
                work = q.get()                      #fetch new work from the Queue

                for attempt in range(5): #try to connect 5 times as there are a lot of network disruptions
                    try:
                        username=work[1]
                        target = f"https://en.chaturbate.com/api/chatvideocontext/{username.lower()}"
                        headers = {
                            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36', }
                        response = requests.get(target, headers=headers)

                        if b"It's probably just a broken link, or perhaps a cancelled broadcaster." in response.content: #check if models still exists
                            logging.info(username.lower()+" is not a model anymore, removing from db")
                            exec_query(f"DELETE FROM CHATURBATE WHERE USERNAME='{username}'")
                            response_dict[username] = "error" #avoid processing the failed model
                        else:
                            response_json = json.loads(response.content)
                            response_dict[username] = response_json #response[username]=status
    

    
                    except (json.JSONDecodeError,ConnectionError) as e:
                        handle_exception(e)
                        logging.info(username.lower()+" has failed to connect on attempt "+str(attempt))
                        time.sleep(1) #sleep and retry              
                    except Exception as e:
                        handle_exception(e)
                        response_dict[username] = "error"
                    
                    else:
                        break

                #signal to the queue that task has been processed
                q.task_done()
            return True

        q = Queue(maxsize=0)
        #Populating Queue with tasks
        response_dict = {}

        #load up the queue with the username_list to fetch and the index for each job (as a tuple):
        for i in range(len(username_list)):
            #need the index and the url in each queue item.
            q.put((i,username_list[i]))    
        
        #Starting worker threads on queue processing
        for i in range(http_threads):
            
            worker = threading.Thread(target=crawl, args=(q,response_dict), daemon=True)
            worker.start()
            time.sleep(wait_time)  #avoid server spamming by time-limiting the start of requests
        
        #now we wait until the queue has been processed
        q.join()
        
        
            
        

        for username in username_list:
            response=response_dict[username]
            
            try:

                if ("status" not in response
                        and response != "error"):
                    if (response["room_status"] == "offline"):

                        if online_dict[username] == "T" :
                            exec_query(
                                f"UPDATE CHATURBATE SET ONLINE='F' WHERE USERNAME='{username}'")

                            for y in chatid_dict[username]:
                                risposta(y, f"{username} is now offline", bot)


                    elif online_dict[username] == "F":

                            exec_query(
                                f"UPDATE CHATURBATE SET ONLINE='T' WHERE USERNAME='{username}'")

                            for y in chatid_dict[username]:    
                                risposta(y, f"{username} is now online! You can watch the live here: http://chaturbate.com/{username}", bot)

                            


                elif response != "error":
                    if "401" in str(response['status']):
                        if "This room requires a password" in str(response['detail']): #assuming the user knows the password

                            if (online_dict[username] == "F"):

                                exec_query(f"UPDATE CHATURBATE SET ONLINE='T' WHERE USERNAME='{username}'")
                                
                                for y in chatid_dict[username]:    
                                    risposta(y, f"{username} is now online! You can watch the live here: http://chaturbate.com/{username}", bot)

                        if "Room is deleted" in str(response['detail']):
                            exec_query(f"DELETE FROM CHATURBATE WHERE USERNAME='{username}'")
                            for y in chatid_dict[username]:
                                risposta(y, f"{username} has been removed because room has been deleted", bot)
                            logging.info(f"{username} has been removed because room has been deleted")

                        if "This room has been banned" in str(response['detail']):
                            exec_query(f"DELETE FROM CHATURBATE WHERE USERNAME='{username}'")
                            for y in chatid_dict[username]:
                                risposta(y, f"{username} has been removed because room has been deleted", bot)
                            logging.info(f"{username} has been removed because has been banned")

                        if "This room is not available to your region or gender." in str(response['detail']):
                            exec_query(f"DELETE FROM CHATURBATE WHERE USERNAME='{username}'")
                            for y in chatid_dict[username]:
                                risposta(y, f"{username} has been removed because of geoblocking, I'm going to try to fix this soon", bot)
                            logging.info(f"{username} has been removed because of blocking")          
            except Exception as e:
                handle_exception(e)




start_handler = CommandHandler(('start', 'help'), start)
dispatcher.add_handler(start_handler)

add_handler = CommandHandler('add', add, pass_args=True)
dispatcher.add_handler(add_handler)

remove_handler = CommandHandler('remove', remove, pass_args=True)
dispatcher.add_handler(remove_handler)

list_handler = CommandHandler('list', list_command)
dispatcher.add_handler(list_handler)

authorize_admin_handler = CommandHandler(
    'authorize_admin', authorize_admin, pass_args=True)
dispatcher.add_handler(authorize_admin_handler)

send_message_to_everyone_handler = CommandHandler(
    'send_message_to_everyone', send_message_to_everyone, pass_args=True)
dispatcher.add_handler(send_message_to_everyone_handler)

#endregion

# default table creation
exec_query("""CREATE TABLE IF NOT EXISTS CHATURBATE (
        USERNAME  CHAR(60) NOT NULL,
        CHAT_ID  CHAR(100),
        ONLINE CHAR(1))""")

# admin table creation
exec_query("""CREATE TABLE IF NOT EXISTS ADMIN (
        CHAT_ID  CHAR(100))""")


threading.Thread(target=check_online_status,daemon=True).start()

updater.start_polling()
updater.idle()