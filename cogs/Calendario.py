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
        fecha = [int(string) for string in re.split(r'[^\d]', date) if string]
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
    return datetime.datetime(*date, *time)

weekdays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


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
        # Events spanning multiple days are not yet supported
        for thrice, event in enumerate(event for event in calendar if event.end_time.day - event.start_time.day == 0):
            embed_value = ''
            timedelta = event.start_time - datetime.datetime.now().astimezone(zoneinfo.ZoneInfo(timezone))
            start_time = event.start_time
            start, end = start_time.strftime('%H:%M'), event.end_time.strftime('%H:%M')
            weeks_until = timedelta.days // 7

            if weeks_until == 0: # Red
                embed_value = f'''```ml\n[{start}-{end}]\n  {unidecode(event.description.title())} ({weekdays[start_time.weekday()]})```'''
            elif weeks_until == 1: # Orange
                embed_value = f'''```prolog\n[{start}-{end}]\n  {unidecode(event.description.title())} ({weekdays[start_time.weekday()]})```'''
            elif weeks_until == 2: # Yellow
                embed_value = f'''```asciidoc\n[{start}-{end}]\n>  {event.description} ({weekdays[start_time.weekday()]}) :: ```'''
            elif weeks_until > 2: # Green
                embed_value = f'''```md\n[{start}-{end}]\n> {event.description} ({weekdays[start_time.weekday()]})```'''
            else: # Gray
                embed_value = f'''```ini\n#[{start}-{end}]\n #{event.description} ({weekdays[start_time.weekday()]})```'''
            embedName = f'{thrice + 1}. {months[start_time.month - 1]} {start_time.day:02}  —  **{event.category}**'
            embed_list.append([embedName, embed_value])
            if thrice % 3 == 2:
                pass

        # Count to consider automatic line breaking in event description
        # Old spaghetti code, can't bother fixing it
        name_lengths_list, name_lengths_list_extra, value_lenghts_list = [], [], []
        linebreak_counter = 0
        for index, name_value_list in enumerate(embed_list):
            if index % 3 == 0 and index != 0:
                linebreak_counter = 0
                linebreak_counter += 0
                linebreak_counter += max(value_lenghts_list)
                for jndex, name_value_list_changer in enumerate(embed_list[index-3:index]):
                    _, valueChanger = name_value_list_changer
                    embed_list[jndex + index-3][1] = embed_list[jndex + index-3][1][:-3] + '\n ' * (linebreak_counter - (value_lenghts_list[jndex])) + '```'
                    embed_list[jndex + index-3][0] = embed_list[jndex + index-3][0] + ' ' * 2 * (title_length - name_lengths_list_extra[jndex])+ '-' * (title_length - 1) * (max(name_lengths_list) - (name_lengths_list[jndex]))
                name_lengths_list, name_lengths_list_extra, value_lenghts_list = [], [], []
            if name_value_list[1]:
                name, value = name_value_list
            else:
                continue
            # Title
            title_length = 37 if name_value_list in embed_list[(len(embed_list)-1)//3*3:] and len(embed_list) % 3 != 0 else 27
            name_lengths_list.append(len(name)//title_length + 1)
            name_lengths_list_extra.append(len(name)%title_length)
            # Decription
            character_counter = -1
            linebreak_counter2 = 1
            linelength = 29 if name_value_list in embed_list[(len(embed_list)-1)//3*3:] and len(embed_list) % 3 != 0 else 18
            for word in re.split(' ', re.findall(r'[\n]+([\w\-\(\)>:# ]+)', value)[0]):
                if len(word) <= linelength:
                    character_counter += 1 + len(word)
                    if character_counter > linelength:
                        character_counter = len(word)
                        linebreak_counter2 += 1
                else:
                    character_counter = len(word)
                    linebreak_counter2 += 1
                    while character_counter > linelength:
                        character_counter -= linelength
                        linebreak_counter2 += 1
                    
            value_lenghts_list.append(linebreak_counter2)

        linebreak_counter = 0
        linebreak_counter += 0
        linebreak_counter += max(value_lenghts_list)
        for jndex, name_value_list_changer in enumerate(embed_list[(len(embed_list)-1)//3*3:]):
            _, valueChanger = name_value_list_changer
            embed_list[jndex + (len(embed_list)-1)//3*3][1] = embed_list[jndex + (len(embed_list)-1)//3*3][1][:-3] + '\n ' * (linebreak_counter - (value_lenghts_list[jndex])) + '```'
            embed_list[jndex + (len(embed_list)-1)//3*3][0] = embed_list[jndex + (len(embed_list)-1)//3*3][0] + ' ' * 2 * (title_length - name_lengths_list_extra[jndex]) + '-' * (title_length - 1) * (max(name_lengths_list) - (name_lengths_list[jndex]))
        name_lengths_list, name_lengths_list_extra, value_lenghts_list = [], [], []

        # Generate the embed
        for thrice, name_value_list in enumerate(embed_list):
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
                ).astimezone(zoneinfo.ZoneInfo(timezone))
            if fecha_final or hora_final:
                end_time = process_date(
                    fecha_final or old_event.end_time.strftime('%d/%m/%Y'),
                    hora_final  or old_event.end_time.strftime('%H:%M')
                ).astimezone(zoneinfo.ZoneInfo(timezone))
                
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