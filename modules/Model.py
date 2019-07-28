import datetime
import json
import time
from io import BytesIO

import requests
from PIL import Image
from modules import Exceptions
from modules import Utils
import logging


class Model:

    def __init__(self, username, autoupdate=True):
        self._response = None
        self.__model_image = None
        self.__online = None
        self.__status = None
        self.last_update = None
        self.username = username
        self.autoupdate = autoupdate

        self.update_model_status()

    @property
    def status(self):
        if self.__status is None:
            self.update_model_status()
            return self.__status
        elif (datetime.datetime.now() - self.last_update).total_seconds() > 10 and self.autoupdate:
            self.update_model_status()
        return self.__status

    @status.setter
    def status(self, value):
        self.__status = value

    @property
    def online(self):
        if self.__online is None:
            self.update_model_status()
            return self.__online
        elif (datetime.datetime.now() - self.last_update).total_seconds() > 10 and self.autoupdate:
            self.update_model_status()
        return self.__online

    @online.setter
    def online(self, value):
        self.__online = value

    @property
    def model_image(self):
        self.update_model_image()
        if self.__model_image is None:
            if self.status == "offline":
                raise Exceptions.ModelOffline
            elif self.status == "away":
                raise Exceptions.ModelAway
            elif self.status == ("private" or "hidden"):
                raise Exceptions.ModelPrivate
            elif self.status == "password":
                raise Exceptions.ModelPassword
            else:
                raise Exceptions.ModelNotViewable
        else:
            return self.__model_image

    @model_image.setter
    def model_image(self, value):
        self.__model_image = value

    def update_model_status(self):
        for attempt in range(5):
            # noinspection PyBroadException
            try:
                self.last_update = datetime.datetime.now()
                target = f"https://en.chaturbate.com/api/chatvideocontext/{self.username}"
                headers = {
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36', }
                self._response = requests.get(target, headers=headers)
            except (json.JSONDecodeError, ConnectionError) as e:
                Utils.handle_exception(e)
                logging.info(self.username + " has failed to connect on attempt " + str(attempt))
                time.sleep(1)  # sleep and retry
            except Exception as e:
                Utils.handle_exception(e)
                logging.info(self.username + " has incurred in an unknown exception")
                self.status = "error"
                self.online = False
            else:
                break

        if self._response is None:
            logging.info(self.username + " has failed to connect after all attempts")
            self.status = "error"
            self.online = False
        elif b"It's probably just a broken link, or perhaps a cancelled broadcaster." in self._response.content:  # check if models still exists
            self.status = "error"
            self.online = False
            return
        elif self._response.status_code == 401:
            self._response = json.loads(self._response.content)
            if "Room is deleted" in str(self._response['detail']):
                self.status = "deleted"
            elif "This room has been banned" in str(self._response['detail']):
                self.status = "banned"
            elif "This room is not available to your region or gender." in str(self._response['detail']):
                self.status = "geoblocked"
            elif "This room requires a password" in str(self._response['detail']):
                self.status = "password"
                self.online = True
            else:
                self.online = False
            return
        elif self._response.status_code == (200 and 401):
            logging.error(f'{self.username} got a {self._response.status_code} error')
            self.status = "error"
            self.online = False
            return
        else:
            self._response = json.loads(self._response.content)
            self.status = self._response["room_status"]

        if self.status == "error" or self.status == ("offline" or "away" or "private" or "hidden"):
            self.online = False
        else:
            self.online = True

    def update_model_image(self):
        if self.online and self.status != "password":
            model_image = Image.open(
                BytesIO(requests.get(f'https://roomimg.stream.highwebmedia.com/ri/{self.username}.jpg').content))
            bio = BytesIO()
            bio.name = 'image.jpeg'
            model_image.save(bio, 'JPEG')
            bio.seek(0)
            self.model_image = bio
        else:
            self.model_image = None
