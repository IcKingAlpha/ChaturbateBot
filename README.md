Status
=============
[![Build Status](https://travis-ci.org/fuomag9/ChaturbateBot.svg?branch=master)](https://travis-ci.org/fuomag9/ChaturbateBot)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/3bab44d73eb5417da2c650ebdb12050f)](https://www.codacy.com/app/fuomag9/ChaturbateBot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=fuomag9/ChaturbateBot&amp;utm_campaign=Badge_Grade)

Why is this repository deprecated?
=============
On the 10/11th of october something changed in the cloudflare configuration of chaturbate.com, which no longer allows me to continously query the APIs, so the bot will no longer work at the time of writing (A fix by querying the pages could be made but judging by how fast the requests get blocked and the ammount of work that would be needed is not something I have time to do now)


What is this?
=============

A python telegram bot to receive a notification whenever an user is online on
chaturbate.com

Requirements
============

Python3 >= 3.6

Requirements written in requirements.txt

Setup
=====

Install requirements in the main folder with
```sh
$ pip install -r requirements.txt 
```

Get a telegram bot api key, you need it in order to be able to communicate with
telegram’s servers.

Running
=======

```sh 
$ python3 ChaturbateBot.py -k yourbotapikey OPTIONAL ARGUMENTS
```
