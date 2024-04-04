import nextcord
import os, sys, asyncio, re
from nextcord.ext import commands
from keys import *
from extras import *
cwd = "" if os.getcwd().split("\\")[-1] == "DiscordBot" else "DiscordBot/"

backup()

intents = nextcord.Intents.all()
intents.members = True

extensions = []
#Yo lo tengo ejecutando en una carpeta externa, así que tengo que incluir mi carpeta y la de otros

for filename in os.listdir(cwd + "cogs"):
    if filename.endswith(".py") and filename.capitalize()[0] == filename[0]:
        extensions.append("cogs." + filename[:-3])


bot = commands.Bot(command_prefix = "!", intents =  intents)

# from mycommands import * 
# mycommands(bot)
if __name__ == "__main__":
    for extension in extensions:
        bot.load_extension(extension)
        print("Added " + extension)
else: #No pilla bien el path para ejecutarlo, así que pongo tmb esta cláusula, pero no quito el if else porque creo que debería estar por si se quiere transformar a una librería
    for extension in extensions:
        bot.load_extension(extension)
        print("Added " + extension)

#ESTO BLOQUEA QUE ENVÍE MENSAJES A TODAS PARTES
@bot.event
async def on_message(message):
    if message.guild.id == guild1['guildId'] or message.guild.id == guild2['guildId'] or message.guild.id == guild3['guildId']:
        if message.channel.id in guild1['botChannel'] or message.channel.id in guild2['botChannel'] or message.channel.id in guild3['botChannel']:
            await bot.process_commands(message)



bot.run(TOKEN)