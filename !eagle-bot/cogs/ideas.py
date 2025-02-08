import disnake
from disnake.ext import commands
from disnake import TextInputStyle
import methods
import sqlite3
import json

IDEA_CHANNEL_ID = 1335383057703637164 # тут айди канала с идеями

class IdeaModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Идея и описание идеи",
                placeholder="Формулируйте идею кратко, указывайте её цель и пользу.",
                custom_id="idea",
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
        await inter.response.send_message("Идея отправлена!", ephemeral=True)

        embed = methods.embed(f"Идея {inter.author.name}", inter.text_values['idea'])
        embed.set_thumbnail(url=inter.author.avatar.url)
        embed.add_field(name="Лайков:", value="```0```", inline=True)
        embed.add_field(name="Дизлайков:", value="```0```", inline=True)

        channel = inter.guild.get_channel(IDEA_CHANNEL_ID)
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
                "INSERT INTO ideas VALUES (?, ?, ?, ?, ?, ?, ?)",
                (message.id, inter.author.id, inter.text_values['idea'], 0, 0, '{}', '')
            )
            db.commit()

class Idea(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(description="Подать идею в канал с идеями.")
    async def idea(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_modal(modal=IdeaModal())

    @commands.slash_command(description="Ответить на идею.")
    @commands.default_member_permissions(manage_threads=True, manage_messages=True)
    async def answer(
        self, 
        inter: disnake.ApplicationCommandInteraction, 
        idea_id: str = commands.Param(name='айди', description='Айди сообщения с идеей.'),
        raw_answer: str = commands.Param(name='ответ', description='Ответ на идею.', choices=['Отклонено', 'Принято']),
        reason: str = commands.Param(name='причина', description='Причина ответа. Например: Идея реализована на сервере или Нереализуемо.')
    ):

        try: 
            channel = inter.guild.get_channel(int(IDEA_CHANNEL_ID))
            message = await channel.fetch_message(idea_id)

            if raw_answer == "Отклонено":
                answer = ':x: Отклонено'
            elif raw_answer == 'Принято':
                answer = ':white_check_mark: Принято'

            embed = message.embeds[0]
            embed.remove_field(2)
            embed.add_field(name=answer, value=reason, inline=False)
            
            await message.edit(embed=embed, components=[])

            thread = message.thread
            if thread:
                await thread.edit(locked=True)

            with sqlite3.connect("ideas.db") as db:
                cursor = db.cursor()
                cursor.execute("UPDATE ideas SET answer = ? WHERE id = ?", (raw_answer, idea_id))
                db.commit()

            await inter.send(f'Ты успешно ответил на идею {message.jump_url}', ephemeral=True)
        except:
            embed = methods.error("Указан неверный айди идеи")
            await inter.send(embed=embed, ephemeral=True)

    @commands.Cog.listener("on_button_click")
    async def idea_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id not in ("like", "dislike"):
                return

        if inter.component.custom_id == "like":

            methods.set_rating(inter.author.id, inter.message.id, 1)
            likes, dislikes = methods.get_rating(inter.message.id)

            embed = inter.message.embeds[0]
            embed.clear_fields()
            embed.add_field(name="Лайков:", value=f"```{likes}```", inline=True)
            embed.add_field(name="Дизлайков:", value=f"```{dislikes}```", inline=True)

            await inter.message.edit(embed=embed)
            await inter.response.send_message("Ты проголосовал :thumbsup:", ephemeral=True)

        elif inter.component.custom_id == "dislike":

            methods.set_rating(inter.author.id, inter.message.id, -1)
            likes, dislikes = methods.get_rating(inter.message.id)

            embed = inter.message.embeds[0]
            embed.clear_fields()
            embed.add_field(name="Лайков:", value=f"```{likes}```", inline=True)
            embed.add_field(name="Дизлайков:", value=f"```{dislikes}```", inline=True)

            await inter.message.edit(embed=embed)
            await inter.response.send_message("Ты проголосовал :thumbsdown:", ephemeral=True)


def setup(bot: commands.Bot):
    methods.startprint(__name__)
    bot.add_cog(Idea(bot))