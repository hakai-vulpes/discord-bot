import os
from dotenv import load_dotenv
from configparser import ConfigParser

import nextcord
from nextcord.ext import commands

load_dotenv()

guilds_config = ConfigParser()
guilds_config.read(os.path.join('config', 'guilds.ini'))
guild_bot_channel = {
    int(section.get('id')):set(map(int, section.get('bot_channels')[1:-1].split(', ')))
    for section in guilds_config.values()
    if 'id' in section and 'verification_channel' in section
}

TOKEN = os.getenv('DISCORD_TOKEN')

intents = nextcord.Intents.all()
intents.members = True

extensions = []

for filename in os.listdir('cogs'):
    if filename.endswith('.py') and filename.capitalize()[0] == filename[0]:
        extensions.append('cogs.' + filename[:-3])


bot = commands.Bot(command_prefix = '!', intents =  intents)

if __name__ == '__main__':
    for extension in extensions:
        bot.load_extension(extension)
        print('Added ' + extension)


@bot.event
async def on_message(message):
    if message.channel.id in guild_bot_channel.get(message.guild.id, set()):
        await bot.process_commands(message)
        
        
from src.database import DatabaseAccessor
import datetime, asyncio

config = ConfigParser()
config.read(os.path.join('config', 'config.ini'))
db = DatabaseAccessor(config['DB']['path'])
backup_frequency = int(config['DB']['backup_frequency'])

async def automatic_backup():
    '''Manages the backup of the database.'''
    seconds = datetime.timedelta(days=backup_frequency).total_seconds()
    if seconds <= 0: return
    while True:
        db.backup()
        await asyncio.sleep(seconds)


if __name__ == '__main__':
    bot.loop.create_task(automatic_backup())
    bot.run(TOKEN)