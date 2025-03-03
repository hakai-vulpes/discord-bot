# Add main path to the path to access my libraries
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# Load config
from configparser import ConfigParser
guilds_config = ConfigParser()
guilds_config.read(os.path.join('config', 'guilds.ini'))
guild_id_list = [
    int(section.get('id'))
    for section in guilds_config.values()
    if 'id' in section
]

guilds_with_verification = {
    int(section.get('id')):int(section.get('verification_channel'))
    for section in guilds_config.values()
    if 'id' in section and 'verification_channel' in section
}

import nextcord
from nextcord.ext import commands
from nextcord import Interaction

from src.utils.logs import commands_logger, parse_args

class General(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @nextcord.slash_command(
        name = 'hello',
        description = 'Hacer ping al bot',
        guild_ids = guild_id_list
    )
    async def hello(self, interaction: Interaction):
        '''Say hello to the bot.'''
        
        await interaction.response.send_message('Buenas pendejo :P')
        commands_logger.info(
            '',
            extra={
                'author': interaction.user.name,
                'guild': interaction.guild.id
            }
        )
        

    @commands.Cog.listener()
    async def on_ready(self):
        print('The bot is running! :3\n')


    @commands.Cog.listener()
    async def on_command_error(self, interaction: nextcord.Interaction, error):
        await interaction.followup.send(f'Error del comando. ({error})')


    # @nextcord.slash_command(
    #     name = 'verificar',
    #     description = 'Realizar la verificación del usuario',
    #     guild_ids = guild_idx_list
    # )
    # async def verificar(self, interaction: Interaction, correo: str):
    #     guild_id = interaction.guild.id
    #     channel_id = interaction.channel.id
    #     verification_channel_id = guilds_with_verification.get(guild_id)
    #     if verification_channel_id == channel_id:
    #         pass


def setup(bot: commands.Bot):
    bot.add_cog(General(bot))