import logging

from modules import Utils
from modules.alchemy import PreferenceUser


def user_has_preferences(chatid: str) -> bool:
    """
    Checks
     if user exists in the preferences table

    :param chatid: The chatid of the user who will be tested
    :return: True if it exists, False if it doesn't exist
    """
    results = Utils.alchemy_instance.session.query(PreferenceUser).filter_by(chat_id=str(chatid)).first()
    if results is None:
        return False
    else:
        return True


def add_user_to_preferences(chatid: str) -> None:
    """
    Add user to the preference table

    :param chatid: The chatid of the user who will be tested
    """
    Utils.alchemy_instance.session.add(PreferenceUser(chat_id=str(chatid)))
    Utils.alchemy_instance.session.commit()
    logging.info(f'{chatid} has been added to preferences')


def remove_user_from_preferences(chatid: str) -> None:
    """
    Remove the chatid from the preference table

    :param chatid: The chatid of the user who will be removed
    """
    user: PreferenceUser = Utils.alchemy_instance.session.query(PreferenceUser).filter_by(chat_id=str(chatid)).first()
    Utils.alchemy_instance.session.delete(user)
    Utils.alchemy_instance.session.commit()
    logging.info(f'{chatid} has been removed from preferences')


def update_link_preview_preference(chatid: str, value: bool) -> None:
    """
    Update the link_preview preference of the user

    :param chatid: The chatid of the user who will be tested
    :param value: The boolean value that will be converted to int and inserted in the table
    """
    if not user_has_preferences(chatid):
        add_user_to_preferences(chatid)

    user: PreferenceUser = Utils.alchemy_instance.session.query(PreferenceUser).filter_by(chat_id=str(chatid)).first()
    user.link_preview = value
    Utils.alchemy_instance.session.commit()


def get_user_link_preview_preference(chatid: str) -> bool:
    """
    Retrieve the link_preview preference of the user

    :param chatid: The chatid of the user who will be tested
    :return: The boolean value of the preference
    """
    if not user_has_preferences(chatid):
        add_user_to_preferences(chatid)

    return Utils.alchemy_instance.session.query(PreferenceUser).filter_by(chat_id=str(chatid)).first().link_preview


def update_notifications_sound_preference(chatid: str, value: bool) -> None:
    """
    Update the notifications preference of the user

    :param chatid: The chatid of the user who will be tested
    :param value: The boolean value that will be converted to int and inserted in the table
    """
    if not user_has_preferences(chatid):
        add_user_to_preferences(chatid)

    user: PreferenceUser = Utils.alchemy_instance.session.query(PreferenceUser).filter_by(chat_id=str(chatid)).first()
    user.notifications_sound = value
    Utils.alchemy_instance.session.commit()


def get_user_notifications_sound_preference(chatid: str) -> bool:
    """
    Retrieve the notifications preference of the user

    :param chatid: The chatid of the user who will be tested
    :return: The boolean value of the preference
    """
    if not user_has_preferences(chatid):
        add_user_to_preferences(chatid)

    return Utils.alchemy_instance.session.query(PreferenceUser).filter_by(chat_id=str(chatid)).first().notifications_sound
