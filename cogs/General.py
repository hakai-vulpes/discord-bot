import sys, os
from configparser import ConfigParser

# Add main path to the path to access my libraries
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption

from src.utils.logs import commands_logger, parse_args

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


class VotingView(nextcord.ui.View):

    def __init__(
            self,
            options,
            timeout: float | None,
            auto_defer: bool = True,
            prevent_update: bool = True
        ) -> None:

        super().__init__(
            timeout=timeout,
            auto_defer=auto_defer,
            prevent_update=prevent_update
        )
        self.options = options
        self.message: nextcord.PartialMessage = None
        self.votes = {}

        for index, option in enumerate(self.options):
            button = nextcord.ui.Button(label=option, style=nextcord.ButtonStyle.blurple)
            button.callback = self.button_callback(index)
            self.add_item(button)   


    def register_message(self, message: nextcord.Message):
        '''Registers the message that the view is attached to.'''
        
        self.message = message


    async def on_timeout(self) -> None:
        '''Disables the buttons when the view times out.'''
        
        for item in self.children:
            item.disabled = True
            
        if self.message:
            await self.message.edit(
                content="(Esta votación ha finalizado)",
                view=self
            )
    
    
    def button_callback(self, index: int):
        '''Returns a callback function for the button at the given index.'''
        
        async def wrapper(interaction: nextcord.Interaction):
            if not self.message:
                return None
            
            previous_vote = self.votes.get(interaction.user)
            if previous_vote == index:
                return None
            
            self.votes[interaction.user] = index
            embed = interaction.message.embeds[0]
            title, text = embed.title, embed.description
            text_index = text[::-1].index('\n\n')
            options_text, rest = text[-text_index:], text[:-text_index]

            options = []
            for option in options_text.split('\n'):
                colon_index = option.index(': ')
                options.append([
                    option[:colon_index + 2],
                    option[colon_index + 2: -7],
                    ' voto/s'
                ])

            options[index][1] = str(1 + int(options[index][1]))
            if previous_vote is not None:
                options[previous_vote][1] = str(int(options[index][1]) - 1)
            options_output = '\n'.join(''.join(option) for option in options)

            await self.message.edit(
                embed=nextcord.Embed(
                    title=title,
                    description=rest+options_output,
                    color=0xff6700
                )
            )
                
                
        return wrapper


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


    @commands.has_guild_permissions(manage_messages=True)
    @nextcord.slash_command(
        name = 'votacion',
        description = 'Anuncio con votación asociada',
        guild_ids=guild_id_list
    )
    async def voting(
        self,
        interaction: nextcord.Interaction,
        title: str,
        text: str,
        options: str,
        timeout: float = None
    ):
        '''
        Create a voting message with the given title, text, options and 
        timeout.
        '''

        args_input = parse_args(
            title=title,
            text=text,
            options=options,
            timeout=timeout
        )
        commands_logger.info(
            args_input,
            extra={
                'author': interaction.user.name,
                'guild': interaction.guild.id
            }
        )

        if timeout is not None: timeout = float(timeout)
        options = options.split(',')
        options_str = '\n'
        for option in options:
            options_str += f'\n{option}: 0 voto/s'
        embed = nextcord.Embed(
            title=f'***{title}***',
            description=text+options_str, color=0xff6700)

        
        view = VotingView(options, timeout)

        sent_message = await interaction.response.send_message(embed=embed, view=view)
        view.register_message(sent_message)
    

def setup(bot: commands.Bot):
    bot.add_cog(General(bot))