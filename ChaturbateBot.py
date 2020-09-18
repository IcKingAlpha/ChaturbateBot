# -*- coding: utf-8 -*-

import datetime
import logging
import threading
import time
from queue import Queue
from typing import List

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Unauthorized
from telegram.ext import CommandHandler, Updater, CallbackQueryHandler

from modules import Exceptions
from modules import Preferences
from modules import Utils
from modules.alchemy import Alchemy, PreferenceUser, ChaturbateUser, Admin
from modules.argparse_code import args as argparse_args
from modules.Model import Model

updater = Updater(token=argparse_args["key"], use_context=True)
dispatcher = updater.dispatcher
bot = updater.bot  # bot class instance

bot_path = argparse_args["working_folder"]
wait_time = argparse_args["time"]
http_threads = argparse_args["threads"]
user_limit = argparse_args["limit"]
auto_remove = Utils.str2bool(argparse_args["remove"])
admin_pw = argparse_args["admin_password"]
logging_file = argparse_args["logging_file"]
Utils.alchemy_instance = Alchemy(argparse_args["database_string"])

logging_level = logging.INFO
if not Utils.str2bool(argparse_args["enable_logging"]):
    logging_level = 99  # stupid workaround not to log -> only creates file

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging_level, filename=logging_file)


def send_message(chatid: str, messaggio: str, bot_p: updater.bot, html: bool = False, markup=None) -> None:
    """
    Sends a message to a telegram user and sends "typing" action


    :param chatid: The chatid of the user who will receive the message
    :param messaggio: The message who the user will receive
    :param bot_p: telegram bot instance
    :param html: Enable html markdown parsing in the message
    :param markup: The reply_markup to use when sending the message
    """

    disable_webpage_preview = not Preferences.get_user_link_preview_preference(
        chatid)  # the setting is opposite of preference

    notification = not Preferences.get_user_notifications_sound_preference(
        chatid)  # the setting is opposite of preference

    try:
        bot_p.send_chat_action(chat_id=chatid, action="typing")
        if html and markup is not None:
            bot_p.send_message(chat_id=chatid, text=messaggio,
                               parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=disable_webpage_preview,
                               reply_markup=markup, disable_notification=notification)
        elif html:
            bot_p.send_message(chat_id=chatid, text=messaggio,
                               parse_mode=telegram.ParseMode.HTML, disable_web_page_preview=disable_webpage_preview,
                               disable_notification=notification)
        elif markup is not None:
            bot_p.send_message(chat_id=chatid, text=messaggio, disable_web_page_preview=disable_webpage_preview,
                               reply_markup=markup, disable_notification=notification)
        else:
            bot_p.send_message(chat_id=chatid, text=messaggio, disable_web_page_preview=disable_webpage_preview,
                               disable_notification=notification)
    except Unauthorized:  # user blocked the bot
        if auto_remove:
            logging.info(f"{chatid} blocked the bot, he's been removed from the database")
            Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(
                chat_id=str(chatid)).delete(synchronize_session=False)
            Preferences.remove_user_from_preferences(chatid)
    except Exception as e:
        Utils.handle_exception(e)


def send_image(chatid: str, image, bot_p: updater.bot, html: bool = False, markup=None, caption=None) -> None:
    """
    Sends an image to a telegram user and sends "sending image" action


    :param caption: Photo caption
    :param chatid: The chatid of the user who will receive the message
    :param image: The image to send
    :param bot_p: telegram bot instance
    :param html: Enable html markdown parsing in the message
    :param markup: The reply_markup to use when sending the message
    """

    notification = not Preferences.get_user_notifications_sound_preference(
        chatid)  # the setting is opposite of preference

    try:
        bot_p.send_chat_action(chatid, action="upload_photo")
        if html and markup is not None and caption is not None:
            bot_p.send_photo(chat_id=chatid, photo=image, parse_mode=telegram.ParseMode.HTML, reply_markup=markup,
                             disable_notification=notification, caption=caption)
        elif html and markup is not None:
            bot_p.send_photo(chat_id=chatid, photo=image, parse_mode=telegram.ParseMode.HTML, reply_markup=markup,
                             disable_notification=notification)
        elif markup is not None and caption is not None:
            bot_p.send_photo(chat_id=chatid, photo=image, reply_markup=markup, disable_notification=notification,
                             caption=caption)
        elif html and caption is not None:
            bot_p.send_photo(chat_id=chatid, photo=image, parse_mode=telegram.ParseMode.HTML,
                             disable_notification=notification, caption=caption)
        elif html:
            bot_p.send_photo(chat_id=chatid, photo=image, parse_mode=telegram.ParseMode.HTML,
                             disable_notification=notification)
        elif markup is not None:
            bot_p.send_photo(chat_id=chatid, photo=image, reply_markup=markup, disable_notification=notification)
        elif caption is not None:
            bot_p.send_photo(chat_id=chatid, photo=image, disable_notification=notification, caption=caption)
        else:
            bot_p.send_photo(chat_id=chatid, photo=image, disable_notification=notification)
    except Unauthorized:  # user blocked the bot
        if auto_remove:
            logging.info(f"{chatid} blocked the bot, he's been removed from the database")
            Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(
                chat_id=str(chatid)).delete(synchronize_session=False)
            Preferences.remove_user_from_preferences(chatid)
    except Exception as e:
        Utils.handle_exception(e)


# region normal functions


def start(update, context) -> None:
    global bot
    chatid = update.message.chat_id
    send_message(chatid,
                 """/add - Add a model
/remove - Remove a model
/list - List the models you are following
/stream_image - See a screenshot of a model's live
/settings - Edit your settings""",
                 bot, html=True)


def add(update, context) -> None:
    global bot
    args = context.args
    chatid = update.message.chat_id
    username_message_list = []
    if len(args) < 1:
        send_message(
            chatid,
            "You need to specify an username to follow, use the command like /add <b>username</b>\n You can also add multiple users at the same time by separating them using a comma, like /add <b>username1</b>,<b>username2</b>",
            bot, html=True
        )
        return
    # not lowercase usernames bug the api calls
    if len(args) > 1:
        for username in args:
            if username != "":
                username_message_list.append(Utils.sanitize_username(username).replace(",", ""))
    # len(args)==0 -> only one username or all in one line
    elif "," in args[0].lower():
        for splitted_username in args[0].lower().replace(" ", "").rstrip().split(","):
            if splitted_username != "":
                username_message_list.append(Utils.sanitize_username(splitted_username))
    else:
        username_message_list.append(Utils.sanitize_username(args[0]))

    username_message_list = list(dict.fromkeys(username_message_list))  # remove duplicate usernames

    usernames_in_database = Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(chat_id=str(chatid)).all()

    # 0 is unlimited usernames
    if len(usernames_in_database) + len(username_message_list) > user_limit and (
            Utils.admin_check(chatid) == False != user_limit != 0):
        send_message(chatid,
                     "You are trying to add more usernames than your limit permits, which is " + str(user_limit), bot)
        logging.info(f'{chatid} tried to add more usernames than his limit permits')
        return

    for username in username_message_list:
        model_instance = Model(username)
        if model_instance.status not in ('deleted', 'banned', 'geoblocked', 'canceled', 'error'):
            if username not in usernames_in_database:
                Utils.alchemy_instance.session.add(ChaturbateUser(username=username, chat_id=chatid, online=False))
                Utils.alchemy_instance.session.commit()
                send_message(chatid, f"{username} has been added", bot)
                logging.info(f'{chatid} added {username}')
            else:
                send_message(chatid, f"{username} has already been added", bot)
        elif model_instance.status == 'deleted':
            send_message(chatid, f"{username} has not been added because is deleted", bot)
            logging.info(f"{chatid} could not add {username} because is deleted")
        elif model_instance.status == 'banned':
            send_message(chatid, f"{username} has not been added because is banned", bot)
            logging.info(f"{chatid} could not add {username} because is banned")
        elif model_instance.status == 'geoblocked':
            send_message(chatid, f"{username} has not been added because is geoblocked", bot)
            logging.info(f"{chatid} could not add {username} because is geoblocked")
        elif model_instance.status == 'canceled':
            send_message(chatid, f"{username} was not added because it doesn't exist", bot)
            logging.info(f'{chatid} tried to add {username}, which does not exist')
        elif model_instance.status == 'error':
            send_message(chatid, f"{username} was not added because an error happened", bot)
            logging.info(f'{chatid} could not add {username} because an error happened')


def remove(update, context) -> None:
    global bot
    args = context.args
    chatid = update.message.chat_id
    username_message_list = []
    usernames_in_database = []

    if len(args) < 1:
        send_message(
            chatid,
            "You need to specify an username to follow, use the command like /remove <b>test</b>\n You can also remove multiple users at the same time by separating them using a comma, like /remove <b>username1</b>,<b>username2</b>",
            bot, html=True
        )
        return
    if len(args) > 1:
        for username in args:
            if username != "":
                username_message_list.append(Utils.sanitize_username(username).replace(",", ""))
    # len(args)==0 -> only one username or all in one line
    elif "," in args[0].lower():
        for splitted_username in args[0].lower().replace(" ", "").rstrip().split(","):
            if splitted_username != "":
                username_message_list.append(Utils.sanitize_username(splitted_username))
    else:
        username_message_list.append(Utils.sanitize_username(args[0]))

    usernames_in_database = Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(chat_id=str(chatid)).all()

    if "all" in username_message_list:
        Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(
            chat_id=str(chatid)).all().delete(synchronize_session=False)
        Utils.alchemy_instance.session.commit()
        send_message(chatid, "All usernames have been removed", bot)
        logging.info(f"{chatid} removed all usernames")
    else:
        for username in username_message_list:
            if username in usernames_in_database:
                Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(
                    chat_id=str(chatid), username=str(username)).delete(synchronize_session=False)
                send_message(chatid, f"{username} has been removed", bot)
                logging.info(f"{chatid} removed {username}")
            else:
                send_message(chatid, f"You aren't following {username}", bot)


def list_command(update, context) -> None:
    global bot
    chatid = update.message.chat_id
    output_string = ""

    followed_users = Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(chat_id=chatid).all()
    if followed_users is not None:  # an exception didn't happen

        for user in sorted(followed_users, key=lambda l: l.username):
            user: ChaturbateUser
            output_string += f"{user.username}: "
            if user.online:
                output_string += "<b>online</b>\n"
            else:
                output_string += "offline\n"

    if output_string == "":
        send_message(chatid, "You aren't following any user", bot)
    else:
        send_message(
            chatid, f"You are currently following these {len(followed_users)} users:\n" +
                    output_string, bot, html=True)


def stream_image(update, context) -> None:
    global bot
    args = context.args
    chatid = update.message.chat_id

    if len(args) < 1:
        send_message(chatid,
                     "You didn't specify a model to get the stream image of\nUse the command like this: /stream_image <b>username</b>",
                     bot, html=True)
        return

    username = Utils.sanitize_username(args[0])
    model_instance = Model(username)

    if not Utils.admin_check(chatid):
        if Utils.is_chatid_temp_banned(chatid):
            return
        if Utils.get_last_spam_date(chatid) == None:
            Utils.set_last_spam_date(chatid, datetime.datetime.now())
        elif (datetime.datetime.now() - Utils.get_last_spam_date(chatid)).total_seconds() <= 3:
            Utils.temp_ban_chatid(chatid, 10)
            send_message(chatid, "You have been temporarily banned for spamming, try again later", bot)
            logging.warning(f"Soft banned {chatid} for 10 seconds for spamming image updates")
        else:
            Utils.set_last_spam_date(chatid, datetime.datetime.now())

    try:
        send_image(chatid, model_instance.model_image, bot)
        logging.info(f'{chatid} viewed {username} stream image')

    except Exceptions.ModelPrivate:
        send_message(chatid, f"The model {username} is in private now, try again later", bot)
        logging.warning(f'{chatid} could not view {username} stream image because is private')

    except Exceptions.ModelAway:
        send_message(chatid, f"The model {username} is away, try again later", bot)
        logging.warning(f'{chatid} could not view {username} stream image because is away')

    except Exceptions.ModelPassword:
        send_message(chatid, f"The model {username} cannot be seen because is password protected", bot)
        logging.warning(f'{chatid} could not view {username} stream image because is password protected')

    except (Exceptions.ModelDeleted, Exceptions.ModelBanned, Exceptions.ModelGeoblocked, Exceptions.ModelCanceled,
            Exceptions.ModelOffline):
        send_message(chatid, f"The model {username} cannot be seen because is {model_instance.status}", bot)
        logging.warning(f'{chatid} could not view {username} image update because is {model_instance.status}')

    except Exceptions.ModelNotViewable:
        send_message(chatid, f"The model {username} is not visible", bot)
        logging.warning(f'{chatid} could not view {username} stream image')

    except ConnectionError:
        send_message(chatid, f"The model {username} cannot be seen because of connection issues, try again later", bot)
        logging.warning(f'{chatid} could not view {username} stream image because of connection issues')


def view_stream_image_callback(update, context):
    username = context.match.string.replace("view_stream_image_callback_", "")
    chatid = update.callback_query.message.chat_id
    messageid = update.callback_query.message.message_id
    if Utils.is_chatid_temp_banned(chatid):
        return
    model_instance = Model(username)

    keyboard = [[InlineKeyboardButton("Watch the live", url=f'http://chaturbate.com/{username}'),
                 InlineKeyboardButton("Update stream image", callback_data='view_stream_image_callback_' + username)]]
    markup = InlineKeyboardMarkup(keyboard)

    try:
        bot.edit_message_media(chat_id=chatid, message_id=messageid,
                               media=telegram.InputMediaPhoto(model_instance.model_image,
                                                              caption=f"{username} is now <b>online</b>!",
                                                              parse_mode=telegram.ParseMode.HTML), reply_markup=markup)


    except Exceptions.ModelPrivate:
        send_message(chatid, f"The model {username} is in private now, try again later", bot)
        logging.warning(f'{chatid} could not view {username} image update because is private')

    except Exceptions.ModelAway:
        send_message(chatid, f"The model {username} is away, try again later", bot)
        logging.warning(f'{chatid} could not view {username} image update because is away')

    except Exceptions.ModelPassword:
        send_message(chatid, f"The model {username} cannot be seen because is password protected", bot)
        logging.warning(f'{chatid} could not view {username} image update because is password protected')

    except (Exceptions.ModelDeleted, Exceptions.ModelBanned, Exceptions.ModelGeoblocked, Exceptions.ModelCanceled,
            Exceptions.ModelOffline):
        keyboard = [[InlineKeyboardButton("Watch the live", url=f'http://chaturbate.com/{username}')]]
        markup = InlineKeyboardMarkup(keyboard)
        bot.edit_message_reply_markup(chat_id=chatid, message_id=messageid,
                                      reply_markup=markup)  # remove update image button
        send_message(chatid, f"The model {username} cannot be seen because is {model_instance.status}", bot)
        logging.warning(f'{chatid} could not view {username} image update because is {model_instance.status}')

    except Exceptions.ModelNotViewable:
        send_message(chatid, f"The model {username} is not visible", bot)
        logging.warning(f'{chatid} could not view {username} image update')

    except ConnectionError:
        send_message(chatid, f"The model {username} cannot be seen because of connection issues, try again later", bot)
        logging.warning(f'{chatid} could not view {username} image update because of connection issues')

    except Exception as e:
        if hasattr(e, 'message'):
            if "Message is not modified" in e.message:
                send_message(chatid, f"This is the latest update of {username}", bot)
                if not Utils.admin_check(chatid):
                    if Utils.get_last_spam_date(chatid) == None:
                        Utils.set_last_spam_date(chatid, datetime.datetime.now())
                    elif (datetime.datetime.now() - Utils.get_last_spam_date(chatid)).total_seconds() <= 3:
                        Utils.temp_ban_chatid(chatid, 25)
                        send_message(chatid, "You have been temporarily banned for spamming, try again later", bot)
                        logging.warning(f"Soft banned {chatid} for 25 seconds for spamming image updates")
                    else:
                        Utils.set_last_spam_date(chatid, datetime.datetime.now())


# endregion

# region settings

settings_menu_keyboard = [[InlineKeyboardButton("Link preview", callback_data='link_preview_menu'),
                           InlineKeyboardButton("Notifications sound", callback_data='notifications_sound_menu')]]


def settings(update, context):
    global bot
    global settings_menu_keyboard
    chatid = update.effective_chat.id

    message_markup = InlineKeyboardMarkup(settings_menu_keyboard)

    Link_preview_setting = Preferences.get_user_link_preview_preference(chatid)
    Link_preview_setting = Utils.bool_to_status(Link_preview_setting)

    Notifications_sound_setting = Preferences.get_user_notifications_sound_preference(chatid)
    Notifications_sound_setting = Utils.bool_to_status(Notifications_sound_setting)

    settings_message = f"Here are your settings:\nLink preview: <b>{Link_preview_setting}</b>\nNotifications: <b>{Notifications_sound_setting}</b>"

    if update.callback_query:
        update.callback_query.edit_message_text(text=settings_message, reply_markup=message_markup,
                                                parse_mode=telegram.ParseMode.HTML)
    else:
        send_message(chatid, settings_message, bot, markup=message_markup, html=True)


def link_preview_callback(update, context):
    query = update.callback_query

    keyboard = [[InlineKeyboardButton("Enable", callback_data='link_preview_callback_True'),
                 InlineKeyboardButton("Disable", callback_data='link_preview_callback_False'),
                 InlineKeyboardButton("Back", callback_data='settings_menu')]]

    markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(text=f"Select an option", reply_markup=markup)


def link_preview_callback_update_value(update, context):
    query = update.callback_query
    chatid = query.message.chat.id

    keyboard = [[InlineKeyboardButton("Settings", callback_data='settings_menu')]]
    keyboard = InlineKeyboardMarkup(keyboard)

    if query.data == "link_preview_callback_True":
        setting = True
    else:
        setting = False

    Preferences.update_link_preview_preference(chatid, setting)
    setting = Utils.bool_to_status(setting)

    logging.info(f'{chatid} has set link preview to {setting}')
    query.edit_message_text(text=f"The link preview preference has been set to <b>{setting}</b>", reply_markup=keyboard,
                            parse_mode=telegram.ParseMode.HTML)


def notifications_sound_callback(update, context):
    query = update.callback_query

    keyboard = [[InlineKeyboardButton("Enable", callback_data='notifications_sound_callback_True'),
                 InlineKeyboardButton("Disable", callback_data='notifications_sound_callback_False'),
                 InlineKeyboardButton("Back", callback_data='settings_menu')]]

    markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(text=f"Select an option", reply_markup=markup)


def notifications_sound_callback_update_value(update, context):
    query = update.callback_query
    chatid = query.message.chat.id

    keyboard = [[InlineKeyboardButton("Settings", callback_data='settings_menu')]]
    keyboard = InlineKeyboardMarkup(keyboard)

    if query.data == "notifications_sound_callback_True":
        setting = True
    else:
        setting = False

    Preferences.update_notifications_sound_preference(chatid, setting)
    setting = Utils.bool_to_status(setting)

    logging.info(f'{chatid} has set notifications sound to {setting}')
    query.edit_message_text(text=f"The notifications sound preference has been set to <b>{setting}</b>",
                            reply_markup=keyboard, parse_mode=telegram.ParseMode.HTML)


# endregion

# region admin functions

def authorize_admin(update, context) -> None:
    global bot
    args = context.args
    chatid = update.message.chat_id

    if len(args) != 1:
        send_message(
            chatid,
            "You need to specify the admin password, use the command like /authorize_admin <b>password</b>", bot,
            html=True
        )
        return
    elif admin_pw == "":
        send_message(
            chatid,
            "The admin is disabled, check your telegram bot configuration", bot
        )
        return
    if Utils.admin_check(chatid):
        send_message(chatid, "You already are an admin", bot)
    elif args[0] == admin_pw:
        Utils.alchemy_instance.session.add(Admin(chatid))
        Utils.alchemy_instance.session.commit()
        send_message(chatid, "Admin enabled", bot)
        send_message(chatid,
                     "Remember to disable the --admin-password if you want to avoid people trying to bruteforce this command",
                     bot)
        logging.info(f"{chatid} got admin authorization")
    else:
        send_message(chatid, "The password is wrong", bot)


def send_message_to_everyone(update, context) -> None:
    global bot
    args = context.args
    chatid = update.message.chat_id

    if not Utils.admin_check(chatid):
        send_message(chatid, "You're not authorized to do this", bot)
        return

    chatid_list = []
    message = ""
    start_time = datetime.datetime.now()

    logging.info(f"{chatid} started sending a message to everyone")

    chatid_list = Utils.alchemy_instance.session.query(PreferenceUser).filter_by(chat_id=str(chatid)).all()

    for word in args:
        message += f"{word} "
    message = message[:-1]

    for x in chatid_list:
        send_message(x.chat_id, message, bot)
    logging.info(
        f"{chatid} finished sending a message to everyone, took {(datetime.datetime.now() - start_time).total_seconds()} seconds")


def active_users(update, context) -> None:
    global bot
    chatid = update.message.chat_id
    if not Utils.admin_check(chatid):
        send_message(chatid, "You're not authorized to do this", bot)
        return

    users_count = Utils.alchemy_instance.session.query(PreferenceUser).filter_by(chat_id=str(chatid)).count()
    send_message(chatid, f"The active users are {users_count}", bot)


def active_models(update, context) -> None:
    global bot
    chatid = update.message.chat_id
    if not Utils.admin_check(chatid):
        send_message(chatid, "You're not authorized to do this", bot)
        return

    models_count = Utils.alchemy_instance.session.query(ChaturbateUser.username).distinct().count()
    send_message(chatid, f"The active models are {models_count}", bot)


# endregion

# region threads

def check_online_status() -> None:
    global bot

    def update_status() -> None:
        username_list = []
        chat_and_online_dict = {}

        # create a dictionary with usernames and online using distinct

        username_list = Utils.alchemy_instance.session.query(ChaturbateUser.username).distinct().all()

        # obtain chatid
        for username in username_list:
            results: List[ChaturbateUser] = Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(
                username=username).all()
            chat_and_online_dict[username] = results  # assign (chatid,online) to every model

        # Threaded function for queue processing.
        def crawl(q, model_instances_dict):
            while not q.empty():
                username = Utils.sanitize_username(q.get()[1].username)
                model_instance = Model(username, autoupdate=False)
                model_instance.update_model_status()
                try:
                    model_instance.update_model_image()
                except Exception:
                    model_instance.model_image = None  # set to None just to be secure Todo: this may be extra

                model_instances_dict[username] = model_instance
                # signal to the queue that task has been processed
                q.task_done()
            return True

        q = Queue(maxsize=0)
        # Populating Queue with tasks
        model_instances_dict = {}

        # load up the queue with the username_list to fetch and the index for each job (as a tuple):
        for index, value in enumerate(username_list):
            # need the index and the username in each queue item.
            q.put((index, value))

            # Starting worker threads on queue processing
        for i in range(http_threads):
            worker = threading.Thread(target=crawl, args=(q, model_instances_dict), daemon=True)
            worker.start()
            time.sleep(wait_time)  # avoid server spamming by time-limiting the start of requests

        # now we wait until the queue has been processed
        q.join()

        for username in username_list:
            model_instance = model_instances_dict[username]
            keyboard_with_link_preview = [
                [InlineKeyboardButton("Watch the live", url=f'http://chaturbate.com/{username}'),
                 InlineKeyboardButton("Update stream image", callback_data='view_stream_image_callback_' + username)]]
            keyboard_without_link_preview = [
                [InlineKeyboardButton("Watch the live", url=f'http://chaturbate.com/{username}')]]
            markup_with_link_preview = InlineKeyboardMarkup(keyboard_with_link_preview)
            markup_without_link_preview = InlineKeyboardMarkup(keyboard_without_link_preview)

            try:

                if model_instance.status != "error":
                    for chatid_tuple in chat_and_online_dict[username]:
                        chat_id = chatid_tuple.chat_id
                        db_status = chatid_tuple.online

                        if model_instance.online and db_status == False:

                            if model_instance.status in {"away", "private", "hidden",
                                                         "password"}:  # assuming the user knows the password
                                Utils.alchemy_instance.session.query(ChaturbateUser).filter(
                                    ChaturbateUser.username == username and ChaturbateUser.chat_id == chat_id).update(
                                    {ChaturbateUser.online: True}, synchronize_session=False)
                                send_message(chat_id,
                                             f"{username} is now <b>online</b>!\n<i>No link preview can be provided</i>",
                                             bot, html=True,
                                             markup=markup_without_link_preview)
                            else:
                                Utils.alchemy_instance.session.query(ChaturbateUser).filter(
                                    ChaturbateUser.username == username and ChaturbateUser.chat_id == chat_id).update(
                                    {ChaturbateUser.online: True}, synchronize_session=False)

                                if Preferences.get_user_link_preview_preference(
                                        chat_id) and model_instance.model_image is not None:
                                    send_image(chat_id, model_instance.model_image, bot,
                                               markup=markup_with_link_preview,
                                               caption=f"{username} is now <b>online</b>!", html=True)
                                else:
                                    send_message(chat_id, f"{username} is now <b>online</b>!", bot, html=True,
                                                 markup=markup_without_link_preview)

                        elif model_instance.online == False and db_status:
                            Utils.alchemy_instance.session.query(ChaturbateUser).filter(
                                ChaturbateUser.username == username and ChaturbateUser.chat_id == chat_id).update(
                                {ChaturbateUser.online: False}, synchronize_session=False)
                            send_message(chat_id, f"{username} is now <b>offline</b>", bot, html=True)

                        if model_instance.status == "deleted":
                            Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(username=username,
                                                                                           chat_id=chat_id).delete(
                                synchronize_session=False)
                            send_message(chat_id, f"{username} has been removed because room has been deleted", bot)
                            logging.info(f"{username} has been removed from {chat_id} because room has been deleted")

                        elif model_instance.status == "banned":
                            Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(username=username,
                                                                                           chat_id=chat_id).delete(
                                synchronize_session=False)
                            send_message(chat_id, f"{username} has been removed because room has been banned", bot)
                            logging.info(f"{username} has been removed from {chat_id} because has been banned")

                        elif model_instance.status == "canceled":
                            Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(username=username,
                                                                                           chat_id=chat_id).delete(
                                synchronize_session=False)
                            send_message(chat_id, f"{username} has been removed because room has been canceled", bot)
                            logging.info(f"{username} has been removed from {chat_id} because has been canceled")

                        elif model_instance.status == "geoblocked":
                            Utils.alchemy_instance.session.query(ChaturbateUser).filter_by(username=username,
                                                                                           chat_id=chat_id).delete(
                                synchronize_session=False)
                            send_message(chat_id,
                                         f"{username} has been removed because of geoblocking",
                                         bot)
                            logging.info(f"{username} has been removed from {chat_id} because of geoblocking")

            except Exception as e:
                Utils.handle_exception(e)

    while 1:
        try:
            update_status()
        except Exception as e:
            Utils.handle_exception(e)


# endregion


dispatcher.add_handler(CommandHandler(('start', 'help'), start))
dispatcher.add_handler(CommandHandler('add', add))
dispatcher.add_handler(CommandHandler('remove', remove))
dispatcher.add_handler(CommandHandler('list', list_command))
dispatcher.add_handler(CommandHandler('stream_image', stream_image))
dispatcher.add_handler(CommandHandler('settings', settings))
dispatcher.add_handler(CallbackQueryHandler(link_preview_callback, pattern='link_preview_menu'))
dispatcher.add_handler(CallbackQueryHandler(link_preview_callback_update_value,
                                            pattern='link_preview_callback_True|link_preview_callback_False'))
dispatcher.add_handler(CallbackQueryHandler(notifications_sound_callback, pattern='notifications_sound_menu'))
dispatcher.add_handler(CallbackQueryHandler(notifications_sound_callback_update_value,
                                            pattern='notifications_sound_callback_True|notifications_sound_callback_False'))
dispatcher.add_handler(CallbackQueryHandler(settings, pattern='settings_menu'))
dispatcher.add_handler(CallbackQueryHandler(view_stream_image_callback, pattern='view_stream_image_callback_'))
dispatcher.add_handler(CommandHandler('authorize_admin', authorize_admin))
dispatcher.add_handler(CommandHandler('send_message_to_everyone', send_message_to_everyone))
dispatcher.add_handler(CommandHandler('active_users', active_users))
dispatcher.add_handler(CommandHandler('active_models', active_models))

logging.info('Starting models checking thread...')
threading.Thread(target=check_online_status, daemon=True).start()

logging.info('Starting telegram polling thread...')
updater.start_polling()
updater.idle()
