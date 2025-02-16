import sys, os
from itertools import islice
from configparser import ConfigParser

import re, datetime, logging, zoneinfo
from unidecode import unidecode

import nextcord
from nextcord import Interaction, SlashOption
from nextcord.ext import commands

from src.utils.logs import commands_logger, parse_args
from src.database import Event, DatabaseAccessor

EMBED_VALUE_WIDTH_3 = 17
EMBED_VALUE_WIDTH_2 = 26

EMBED_TITLE_WIDTH_3 = 348
EMBED_TITLE_WIDTH_2 = 530

# Is the size that fits the best the size relationships in embeds
DISCORD_FONT_SIZE = 32

# Add main path to the path to access my libraries
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# Load config
config = ConfigParser()
config.read(os.path.join('config', 'config.ini'))
timezone = config['DEFAULT'].get('timezone') or 'Europe/Madrid'

guilds_config = ConfigParser()
guilds_config.read(os.path.join('config', 'guilds.ini'))
guild_id_list = [
    int(section.get('id')) for section in guilds_config.values() if 'id' in section
]

# Load database
db = DatabaseAccessor(config['DB']['path'])

# Add some helper functions
def fill_date(date: str) -> tuple[int, int, int]:
    try:
        fecha = [int(string) for string in re.split(r'[^\da-zA-Z]', date) if string]
        now = datetime.datetime.now()
        if len(fecha) == 1:
            if now.day <= fecha[0]: fecha.append(now.month)
            elif now.month != 12: fecha.append(now.month + 1)
            else:
                fecha.append(1)
                fecha.append(now.year + 1)

        if len(fecha) == 2:
            if now.month < fecha[1]: fecha.append(now.year)
            elif now.month == fecha[1] and now.day <= fecha[0]: fecha.append(now.year)
            else: fecha.append(now.year + 1)

        if len(fecha) == 3:
            fecha.reverse() # (year, month, day)
            return tuple(fecha)
        
        raise ValueError(f'Invalid date format.')
        
    except:
        raise ValueError(f'Invalid date format.')


hour_rx = re.compile(r'^(?P<hour>[0-2]?[0-9]).?(?P<minutes>[0-5][0-9])$')
shortened_hour_rx = re.compile(r'^(?P<hour>[0-2]?[0-9])$')
def process_time(time: str) -> tuple[int, int]:
    if match := hour_rx.match(time):
        return int(match.group('hour')), int(match.group('minutes'))
    if match := shortened_hour_rx.match(time):
        return int(match.group('hour')), 0
    
    raise ValueError('Invalid hour format.')


def process_date(
    date: str,
    time: str,
) -> datetime.datetime:
    
    date = fill_date(date)
    time = process_time(time)
    return datetime.datetime(*date, *time).astimezone(zoneinfo.ZoneInfo(timezone))

weekdays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def count_lines_mono(text: str, width: int) -> int:
    '''Count the number of lines in a monospaced text with a given width limit.'''
    lines = 1
    i = 0
    word = 0
    for letter in text:
        if letter == '\n':
            i = 0
            word = 0
            lines += 1
            continue
        
        if letter == ' ':
            word = 0
            
        if width == i:
            if not word:
                i = 1
                lines += 1
            else:
                word += letter != ' '
                if word > width:
                    i = 1
                    word = 1
                    lines += 1

                else:
                    i = word
                    lines += 1

        else:
            word += letter != ' '
            i += 1
    
    return lines


from PIL import ImageFont
def get_font_size(font_path: str, text: str):
    font = ImageFont.truetype(font_path, DISCORD_FONT_SIZE)
    size = font.getbbox(text)
    return size[2] - size[0]

bold_rx = re.compile(r'(?<!\\)\*\*(.*?)\*\*')
font_path = ['gg sans Regular.ttf', 'gg sans Bold.ttf']
font_path = [os.path.join('fonts', path) for path in font_path]
def count_lines(text: str, width: int) -> int:
    '''Count the number of lines in a text with a given width limit.'''
    # Collect the bold characters
    end = 0
    bold_characters: list[bool] = []
    clean_text = []
    while match := bold_rx.search(text, pos=end):
        # Register bold segment and the segment just before
        start = match.start()
        bold_characters.extend([False] * (start - end))
        clean_text.append(text[end:start])
        end = match.end()
        bold_characters.extend([True] * (end - start - 4))
        clean_text.append(text[start+2:end-2])

    # Last segment
    bold_characters.extend([False] * (len(text) - end))
    clean_text.append(text[end:])

    clean_text = ''.join(clean_text)
    text = text.replace('**', '')

    # Count the lines
    lines = 1
    word = 0
    i = 0
    for b, letter in zip(bold_characters, text):
        if letter == '\n':
            i = 0
            word = 0
            lines += 1
            continue
        
        letter_size = get_font_size(font_path[b], letter)
        i += letter_size
        if letter == ' ':
            word = 0

        if i > width:
            if not word:
                i = letter_size
                lines += 1

            else:
                if letter != ' ':
                    word += letter_size
                    
                if word > width:
                    i = letter_size
                    word = letter_size
                    lines += 1

                else:
                    i = word
                    lines += 1
                    
        elif letter != ' ':
            word += letter_size

    return lines

TITLE_FILLER = '_'
TITLE_FILLER_SIZE = get_font_size(font_path[False], TITLE_FILLER)
TITLE_FILLER = '\\' + TITLE_FILLER # Escape the filler character

class Calendario(commands.Cog):
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @commands.has_guild_permissions(manage_events=True)
    @nextcord.slash_command(
        name = 'agregar',
        description = 'Agregar un evento al calendario',
        guild_ids = guild_id_list
    )#, help = 'Uso: !agregar '<categoría>' '<descripción>' <DD/MM/AAAA> <hh:mm-hh:mm>\nEjemplo: !agregar examen 'álgebra lineal' 23/10/2023 9:00-11:00')
    async def add(
        self,
        interaction: Interaction,
        categoría: str,
        descripción: str,
        fecha_inicio: str,
        hora_inicio: str = None,
        fecha_final: str = None,
        hora_final: str = None,
        ubicación: str = None
    ):
        '''Put an event in the calendar.'''
        
        await interaction.response.defer()
        # Parse args for logging
        args_input = parse_args(
            categoría=categoría,
            descripción=descripción,
            fecha_inicio=fecha_inicio,
            hora_inicio=hora_inicio,
            fecha_final=fecha_final,
            hora_final=hora_final,
            ubicación=ubicación
        )
        commands_logger.info(
            args_input,
            extra={
                'author': interaction.user.name,
                'guild': interaction.guild.id
            }
        )
        ubicación = 'ETSISI - UPM' if not ubicación else ubicación

        try: 
            start_time = process_date(
                fecha_inicio,
                hora_inicio or '0:00'
            )
            end_time = process_date(
                fecha_final or fecha_inicio,
                hora_final or '23:59'
            )
            if start_time > end_time:
                raise ValueError('Invalid time range. The event cannot start after it ends.')
            
        except ValueError as e:
            await interaction.followup.send(str(e))
            return False

        event = Event(
            category=categoría,
            description=descripción,
            start_time=start_time,
            end_time=end_time,
            location=ubicación,
            guild_id=interaction.guild.id
        )

        if not db.put_event(event):
            await interaction.followup.send(
                'Ha habido un error, puede que este evento ya exista...'
            )
            return False
        
        await event.schedule(interaction.guild)        
        await interaction.followup.send(
            f'In: /agregar {args_input}\n\n'
            f'Out: Evento añadido ({event.to_tuple()})'
        )
        db.sync(Event.fetch_scheduled_events(interaction.guild), interaction.guild.id)


    @nextcord.slash_command(
        name = 'calendario',
        description = 'Mostrar el calendario',
        guild_ids = guild_id_list
    )
    async def calendar(self, interaction: Interaction):
        '''Show the calendar.'''

        await interaction.response.defer()
        commands_logger.info(
            '',
            extra={
                'author': interaction.user.name,
                'guild': interaction.guild.id
            }
        )
        db.sync(Event.fetch_scheduled_events(interaction.guild), interaction.guild.id)

        title_length = 27
        calendar = [*db.get_calendar(interaction.guild.id)]
        if len(calendar) == 0:
            await interaction.followup.send('No hay eventos programados.')
            return

        # Normalize text fields for the embed
        # Working with alignment in Discord is harder than centering a div
        # this makes the boxes look good enough, but it is bad code.
        calendar_embed = nextcord.Embed(title='***CALENDARIO DE EVENTOS***', color=0xff6700)
        embed_list = list()
        for index, event in enumerate(calendar):
            title, value = event.prep_embed()
            title = f'{index + 1}. ' + title
            embed_list.append([title, value])

        # Align the embeds
        alligned_embeds = []
        for row in range(0, len(embed_list), 3):
            if row + 3 <= len(embed_list):
                # Three elements in the row
                title_lengths = [
                    *map(
                        lambda x: count_lines(x[0], EMBED_TITLE_WIDTH_3),
                        embed_list[row:row+3]
                    )
                ]
                value_lengths = [
                    *map(
                        lambda x: count_lines_mono(x[1], EMBED_VALUE_WIDTH_3),
                        embed_list[row:row+3]
                    )
                ]
                max_title_length = max(title_lengths)
                max_value_length = max(value_lengths)

                for i, embed in enumerate(embed_list[row:row+3]):
                    if title_lengths[i] != max_title_length:
                        embed[0] = (
                            embed[0]
                            + '\n' * (max_title_length - title_lengths[i])
                            + TITLE_FILLER * (EMBED_TITLE_WIDTH_3//TITLE_FILLER_SIZE)
                        )
                    if value_lengths[i] != max_value_length:
                        embed[1] = (
                            embed[1][:-3] 
                            + '\n ' * (max_value_length - value_lengths[i])
                            + '```'
                        )
                    alligned_embeds.append(embed)
                    
            elif row + 2 == len(embed_list):
                # Two element in the row
                title_lengths = [
                    *map(
                        lambda x: count_lines(x[0], EMBED_TITLE_WIDTH_2),
                        embed_list[row:row+2]
                    )
                ]
                value_lengths = [
                    *map(
                        lambda x: count_lines_mono(x[1], EMBED_VALUE_WIDTH_2),
                        embed_list[row:row+2]
                    )
                ]
                max_title_length = max(title_lengths)
                max_value_length = max(value_lengths)

                for i, embed in enumerate(embed_list[row:row+2]):
                    if title_lengths[i] != max_title_length:
                        embed[0] = (
                            embed[0]
                            + '\n' * (max_title_length - title_lengths[i])
                            + TITLE_FILLER * (EMBED_TITLE_WIDTH_2//TITLE_FILLER_SIZE)
                        )
                    if value_lengths[i] != max_value_length:
                        embed[1] = (
                            embed[1][:-3] 
                            + '\n ' * (max_value_length - value_lengths[i])
                            + '```'
                        )
                    alligned_embeds.append(embed)

            else:
                for embed in embed_list[row:]:
                    alligned_embeds.append(embed)

        # Generate the embed
        for thrice, name_value_list in enumerate(alligned_embeds):
            name, value = name_value_list
            calendar_embed.add_field(name=name, value=value, inline = True)
            if thrice % 3 == 2:
                calendar_embed.add_field(name='\u00ad', value='\u00ad', inline = False)

        await interaction.followup.send(embed = calendar_embed)


    @commands.has_guild_permissions(manage_events=True)
    @nextcord.slash_command(
        name = 'modificar',
        description = 'Modifica un evento del calendario',
        guild_ids = guild_id_list
    ) # help = 'Uso: !modificar <índice (cronológicamente)> '<categoría>' '<descripción>' <DD/MM/AAAA> <hh:mm-hh:mm>\nEjemplo: !modificar 3 - - 23/10/2023 9:00-11:00, para modificar sólo fecha y hora.')
    async def modify(
        self,
        interaction: Interaction,
        índice: int,
        categoría: str = None,
        descripción: str = None,
        fecha_inicio: str = None,
        hora_inicio: str = None,
        fecha_final: str = None,
        hora_final: str = None,
        ubicación: str = None
    ):
        '''Edit an event in the calendar.'''

        await interaction.response.defer()

        # Parse args for logging
        args_input = parse_args(
            índice=índice,
            categoría=categoría,
            descripción=descripción,
            fecha_inicio=fecha_inicio,
            hora_inicio=hora_inicio,
            fecha_final=fecha_final,
            hora_final=hora_final,
            ubicación=ubicación
        )
        commands_logger.info(
            args_input,
            extra={
                'author': interaction.user.name,
                'guild': interaction.guild.id
            }
        )

        index = índice - 1
        old_event = next(islice(db.get_calendar(interaction.guild.id), index, None))
        start_time = end_time = None
        try:
            if fecha_inicio or hora_inicio:
                start_time = process_date(
                    fecha_inicio or old_event.start_time.strftime('%d/%m/%Y'),
                    hora_inicio  or old_event.start_time.strftime('%H:%M')
                )
            if fecha_final or hora_final:
                end_time = process_date(
                    fecha_final or old_event.end_time.strftime('%d/%m/%Y'),
                    hora_final  or old_event.end_time.strftime('%H:%M')
                )
                
            if (start_time or old_event.start_time) > (end_time or old_event.end_time):
                raise ValueError('Invalid time range. The event cannot start after it ends.')

        except ValueError as e:
            await interaction.followup.send(str(e))
            return False
        
        changes = [*map(bool, [categoría, descripción, start_time, end_time, ubicación])]
        new_event = Event(
            category    = categoría   or old_event.category,
            description = descripción or old_event.description,
            start_time  = start_time  or old_event.start_time,
            end_time    = end_time    or old_event.end_time,
            location    = ubicación   or old_event.location,
            guild_id    = interaction.guild.id
        )
        await new_event.reschedule(interaction.guild, old_event)

        db.edit_event(old_event, new_event)

        await interaction.followup.send(
            f'In: /modificar {args_input}\n\n'
            f'Out: Evento {índice} modificado ('
                f'{tuple(p for p, changed in zip(old_event.to_tuple(), changes) if changed)}'
                ' -> '
                f'{tuple(p for p, changed in zip(new_event.to_tuple(), changes) if changed)}'
            ')'
        )
        db.sync(Event.fetch_scheduled_events(interaction.guild), interaction.guild.id)


    @commands.has_guild_permissions(manage_events=True)
    @nextcord.slash_command(
        name = 'eliminar',
        description = 'Elimina un evento del calendario',
        guild_ids = guild_id_list
    ) # help = 'Uso: !eliminar <índice (cronológicamente)>\nEjemplo: !eliminar 3, para eliminar el tercer evento más cercano')
    async def remove(self, interaction: Interaction, índice: int):
        '''Delete an event from the calendar.'''

        await interaction.response.defer()
        args_input = parse_args(índice=índice)
        commands_logger.info(
            args_input,
            extra={
                'author': interaction.user.name,
                'guild': interaction.guild.id
            }
        )
        
        index = índice - 1
        event = next(islice(db.get_calendar(interaction.guild.id), index, None))
                
        #Eliminar el evento
        await event.unschedule(interaction.guild)
        db.remove_event(event)
        
        await interaction.followup.send(
            f'In: /eliminar {args_input}\n'
            f'Out: Evento {índice} eliminado ({event.to_tuple()})'
        )

        db.sync(Event.fetch_scheduled_events(interaction.guild), interaction.guild.id)


    @commands.has_guild_permissions(administrator=True)
    @nextcord.slash_command(
        name = 'backup',
        description = 'Crear una nueva copia de seguridad',
        guild_ids = guild_id_list
    )
    async def backup(self, interaction: Interaction):
        '''Create a new backup of the database.'''
        
        await interaction.response.defer()
        commands_logger.info(
            '',
            extra={
                'author': interaction.user.name,
                'guild': interaction.guild.id
            }
        )
        
        db.backup()
        await interaction.followup.send('Copia de seguridad creada.')



#Cargar el módulo de Calendario
def setup(bot: commands.Bot):
    bot.add_cog(Calendario(bot))