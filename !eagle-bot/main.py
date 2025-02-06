import disnake
from disnake.ext import commands
import os
import methods
import datetime
import sqlite3
from dotenv import load_dotenv

db = sqlite3.connect("ideas.db")
cursor = db.cursor()

activity = disnake.Activity(
    name="/idea",
    type=disnake.ActivityType.watching,
    state="жароу",
)

bot = commands.Bot(
    intents=disnake.Intents.all(),
    activity=activity,
    default_install_types=disnake.ApplicationInstallTypes.all()
)

os.system('cls')
print("-------------------------------------------")

@bot.event
async def on_ready():
    methods.startprint("BOT")

    cursor.execute("""CREATE TABLE IF NOT EXISTS ideas (
        id int,
        author_id int,
        idea_text text,
        likes int,
        dislikes int,
        voted text,
        answer text
    )""")

    db.commit()

bot.load_extensions('cogs')
load_dotenv("config.env")
token = os.getenv("TOKEN")
bot.run(token)