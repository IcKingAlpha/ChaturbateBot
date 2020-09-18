import argparse
import os
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument(
    "-k", "--key", required=True, type=str, help="Telegram bot api key. It's required in order to run this bot")
ap.add_argument(
    "-f",
    "--working-folder",
    required=False,
    type=str,
    default=os.getcwd(),
    help=f"Set the bot's working-folder. Default = {Path.cwd()}")
ap.add_argument(
    "-t",
    "--time",
    required=False,
    type=float,
    default=0.3,
    help="Time wait between every connection made, in seconds. Default = 0.3s")
ap.add_argument(
    "-threads",
    required=False,
    type=int,
    default=10,
    help="The number of multiple http connection opened at the same time to check chaturbate. Default = 10")
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
    default=True,
    help="Should the bot remove from the database anyone whom blocks it? Default = True")
ap.add_argument(
    "--admin-password",
    required=False,
    type=str,
    default="",
    help="The password to authorize yourself as an admin, Default = False")
ap.add_argument(
    "--enable-logging",
    required=False,
    default=True,
    help="Enable or disable logging, Default = True")
ap.add_argument(
    "--logging-file",
    required=False,
    type=str,
    default=str(Path.cwd()/"program_log.log"),
    help=f"Logging file location, Default={Path.cwd()/'program_log.log'}")
ap.add_argument(
    "--database-string",
    required=False,
    type=str,
    default="postgresql://127.0.0.1:5432/ChaturbateBot",
    help=f"Database connection string, default = postgresql://127.0.0.1:5432/ChaturbateBot")
args = vars(ap.parse_args())

