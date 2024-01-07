from typing import Optional
import nextcord, datetime, asyncio, re

from nextcord.interactions import Interaction
from nextcord.ui.item import Item
from extras import *
from keys import *
from unidecode import unidecode
from nextcord.ext import commands


intents = nextcord.Intents.all()
intents.members = True

bot = commands.Bot(command_prefix = "!", intents =  intents)

guildList = [473511544454512642]
    
@commands.has_permissions(manage_messages=True)
@bot.slash_command(name = "example", description = 'Example',  guild_ids=guildList)
async def example(interaction: nextcord.Interaction):
    pass

@bot.event
async def on_ready():
    print("The bot is running! :3\n")

bot.run(TOKEN)