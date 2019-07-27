import datetime
import json
from io import BytesIO

import requests
from PIL import Image
from modules import Exceptions
from modules import Utils


class Model:

    def __init__(self, username, autoupdate=True):
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
        self.last_update = datetime.datetime.now()
        target = f"https://en.chaturbate.com/api/chatvideocontext/{self.username}"
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36', }
        response = requests.get(target, headers=headers)

        if b"It's probably just a broken link, or perhaps a cancelled broadcaster." in response.content:  # check if models still exists
            return False
        try:
            if response.status_code == 401:
                self.status = "password"
                self.online = True
                return
        except Exception as e:
            Utils.handle_exception(e)
        else:
            response = json.loads(response.content)
            self.status = response["room_status"]

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
