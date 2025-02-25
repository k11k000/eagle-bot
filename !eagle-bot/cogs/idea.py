import disnake
from disnake.ext import commands
from disnake import TextInputStyle
import time
import methods
import sqlite3
import json
import traceback
from dotenv import load_dotenv
import os

load_dotenv("config.env")
IDEA_CHANNEL_ID = os.getenv("IDEA_CHANNEL_ID")
COOLDOWN = os.getenv("COOLDOWN_IDEA_COMMAND")
if not COOLDOWN:
    print("[?] Не найден COOLDOWN_IDEA_COMMAND в config.env, используется задержка по умолчанию (60 секунд)")
    COOLDOWN = 60

if not IDEA_CHANNEL_ID:
    print("[!] Не найден IDEA_CHANNEL_ID в config.env")
    raise 



class IdeaModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Название идеи",
                placeholder="Введите название вашей идеи",
                custom_id="name",
                style=TextInputStyle.short,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label="Описание идеи",
                placeholder="Опишите вашу идею в нескольких предложениях, указывайте её цель и пользу.",
                custom_id="description",
                style=TextInputStyle.long,
                max_length=2000,
            ),
        ]
        super().__init__(
            title="Подача идеи",
            custom_id="create_idea",
            components=components,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        embed = methods.embed(f"{inter.text_values['name']}", inter.text_values['description'])
        embed.set_author(
            name=inter.author.name,
            icon_url=inter.author.avatar.url,
        )
        embed.add_field(name="👍 Лайки:", value="```0```", inline=True)
        embed.add_field(name="👎 Дизлайки:", value="```0```", inline=True)
        embed.add_field(name="Соотношение 👍/👎", value="░░░░░░░░░░░░░░░░░░░░░░░░░", inline=False)

        channel = inter.guild.get_channel(int(IDEA_CHANNEL_ID))
        message = await channel.send(embed=embed)

        components=[
            disnake.ui.Button(emoji="👍", style=disnake.ButtonStyle.green, custom_id=f"like"),
            disnake.ui.Button(emoji="👎", style=disnake.ButtonStyle.red, custom_id=f"dislike"),
        ]

        await message.edit(components=components)
        await message.create_thread(
            name=f"Обсуждение идеи {inter.author.name}",
            auto_archive_duration=10080,
        )
        with sqlite3.connect("ideas.db") as db:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO ideas VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (message.id, inter.author.id, inter.text_values['name'], inter.text_values['description'], 0, 0, '{}', '')
            )
            db.commit()
        await inter.response.send_message(f"Идея отправлена! \n{message.jump_url}", ephemeral=True)

class Idea(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(description="Подать идею в канал с идеями.")
    @commands.cooldown(1, COOLDOWN, commands.BucketType.user)
    async def idea(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_modal(modal=IdeaModal())

    @idea.error
    async def idea_error(self, inter: disnake.ApplicationCommandInteraction, error):
        if isinstance(error, commands.CommandOnCooldown):
            cooldown_timestamp = int(time.time() + error.retry_after)
            embed = methods.error(f"⏳ Ты сможешь повторно использывать команду <t:{cooldown_timestamp}:R>")
            await inter.response.send_message(embed=embed, ephemeral=True)


    @commands.slash_command(description="Ответить на идею.")
    @commands.default_member_permissions(manage_threads=True, manage_messages=True) # Тут можно настроить права для ответа на идеи
    async def answer(
        self, 
        inter: disnake.ApplicationCommandInteraction, 
        idea_id: str = commands.Param(name='айди', description='Айди сообщения с идеей.'),
        raw_answer: str = commands.Param(name='ответ', description='Ответ на идею.', choices=['Отклонено', 'Принято']),
        reason: str = commands.Param(name='причина', description='Причина ответа. Например: Идея реализована на сервере или Нереализуемо.')
    ):

        try: 
            await inter.response.defer(ephemeral=True)

            channel = inter.guild.get_channel(int(IDEA_CHANNEL_ID))
            message = await channel.fetch_message(idea_id)

            if raw_answer == "Отклонено":
                answer = '❌ Отклонено'
                color = disnake.Colour.from_rgb(252, 200, 200)
            elif raw_answer == 'Принято':
                answer = '✅ Принято'
                color = disnake.Colour.from_rgb(200, 252, 200)

            embed = message.embeds[0]
            embed.remove_field(2)
            embed.add_field(name=answer, value=reason, inline=False)
            embed.color = color
            
            await message.edit(embed=embed, components=[])

            thread = message.thread
            if thread:
                await thread.edit(locked=True)

            with sqlite3.connect("ideas.db") as db:
                cursor = db.cursor()
                cursor.execute("UPDATE ideas SET answer = ? WHERE id = ?", (raw_answer, idea_id))
                db.commit()
                try:
                    authorid = cursor.execute("SELECT author_id FROM ideas WHERE id = ?", (int(idea_id),)).fetchone()[0]
                    author = await inter.guild.fetch_member(authorid)
                    embed = methods.embed("Ты получил ответ на свою идею", f"**{answer}**\n{reason}\n{message.jump_url}")
                    await author.send(embed=embed)
                except:
                    pass

            await inter.edit_original_response(f'Ты успешно ответил на идею {message.jump_url}')
        except:
            embed = methods.error("Указан неверный айди идеи")
            await inter.edit_original_response(embed=embed)

    @commands.Cog.listener("on_button_click")
    async def idea_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id not in ["like", "dislike"]:
                return

        if inter.component.custom_id in ["like", "dislike"]:
            if inter.component.custom_id == "like":
                rating = 1
            else:
                rating = -1

            methods.set_rating(inter.author.id, inter.message.id, rating)
            likes, dislikes = methods.get_rating(inter.message.id)

            embed = inter.message.embeds[0]
            embed.set_field_at(0, name="👍 Лайки:", value=f"```{likes}```", inline=True)
            embed.set_field_at(1, name="👎 Дизлайки:", value=f"```{dislikes}```", inline=True)
            bar = methods.bar_generator(likes, dislikes)
            embed.set_field_at(2, name="Соотношение 👍/👎", value=bar, inline=False)

            await inter.message.edit(embed=embed)

            if inter.component.custom_id == "like":
                message = "Ты проголосовал :thumbsup:"
            else:
                message = "Ты проголосовал :thumbsdown:"

            await inter.send(message, ephemeral=True)


def setup(bot: commands.Bot):
    methods.startprint(__name__)
    bot.add_cog(Idea(bot))