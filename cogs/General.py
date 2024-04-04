import sys, os
#Añado el directorio de main al path para acceder a mis librerías
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption

from extras import *
from helpers.alumnos import alumno


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(name = 'hello', description = "Probando slash commands", guild_ids = guildList)
    async def hello(self, interaction: Interaction):
        snitch.info(f"por {interaction.user.name}")
        print("Comando hello 1")
        await interaction.response.send_message("Buenas pendejo :P")
    

    @commands.Cog.listener()
    async def on_ready(self):
        print("The bot is running! :3\n")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await ctx.send(f"Error del comando. ({error})")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild.id == guild1['guildId'] and message.channel.id == guild1['verificationChannel'] and message.author.id != botId:
            channel = self.bot.get_channel(guild1['verificationReceiverChannel'])
            if result := await alumno(message.content):
                await channel.send(f"{message.author.name} se ha identificado: {result}")
            else:
                await channel.send(f'De {message.author.name}: Ningún resultado para: "{message.content}"')
            await message.delete()
    

def setup(bot):
    bot.add_cog(General(bot))