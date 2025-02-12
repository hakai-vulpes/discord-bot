from typing import Self, Iterable, Literal
from unidecode import unidecode
import os
import datetime, zoneinfo

import nextcord

from configparser import ConfigParser
config = ConfigParser()

config.read(os.path.join('config', 'config.ini'))
timezone = config['DEFAULT']['timezone']
weekdays_abbr = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
weekdays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

class Event:
    
    def __init__(
        self,
        category: str,
        description: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        location: str,
        guild_id: int,
    ) -> None:
        
        self.category    = category
        self.description = description
        self.start_time  = start_time.astimezone(zoneinfo.ZoneInfo(timezone))
        self.end_time    = end_time.astimezone(zoneinfo.ZoneInfo(timezone))
        self.location    = location
        self.guild_id    = guild_id


    def __eq__(self, other: Self) -> bool:
        return (
            self.category    == other.category    and
            self.description == other.description and
            self.start_time  == other.start_time  and
            self.end_time    == other.end_time    and
            self.location    == other.location    and
            self.guild_id    == other.guild_id
        )
    

    def __hash__(self):
        return hash((
            self.category,
            self.description,
            self.start_time,
            self.end_time,
            self.location,
            self.guild_id,
        ))


    def __str__(self) -> str:
        return (
            'Event\n\t'
            f'Category: {self.category}\n\t'
            f'Description: {self.description}\n\t'
            f'Start: {self.start_time}\n\t'
            f'End: {self.end_time}\n\t'
            f'Location: {self.location}\n\t'
            f'Guild ID: {self.guild_id}'
        )


    def __repr__(self) -> str:
        return (
            'Event('
                f'category={self.category}, '
                f'description={self.description}, '
                f'start={self.start_time}, '
                f'end={self.end_time}, '
                f'location={self.location}, '
                f'guild_id={self.guild_id}'
            ')'
        )
    

    def to_tuple(self) -> tuple:
        return (
            self.category,
            self.description,
            self.start_time,
            self.end_time,
            self.location,
            self.guild_id,
        )
    
    @classmethod
    def from_scheduled_event(cls, event: nextcord.ScheduledEvent) -> Self:
        '''Create an Event object from a ScheduledEvent object.'''
        
        return cls(
            category    = event.name,
            description = event.description,
            start_time  = event.start_time,
            end_time    = event.end_time,
            location    = event.metadata.location,
            guild_id    = event.guild.id,
        )
    
    @classmethod
    def fetch_scheduled_events(cls, guild: nextcord.Guild) -> Iterable[Self]:
        '''Fetch all scheduled events from a guild.'''
        events = guild.scheduled_events
        return (cls.from_scheduled_event(event) for event in events)
    
    
    def fetch(self, guild: nextcord.Guild) -> nextcord.ScheduledEvent | None:
        '''Gets the corresponding scheduled event from the guild.'''
        
        events = guild.scheduled_events
        if guild.id != self.guild_id:
            return None
        
        for event in events:
            if self == self.from_scheduled_event(event):
                return event

        return None
    
    
    async def schedule(self, guild: nextcord.Guild) -> bool:
        '''Create the scheduled event.'''
        
        if self.fetch(guild) or guild.id != self.guild_id:
            return False
        
        await guild.create_scheduled_event(
            name        = self.category,
            description = self.description,
            start_time  = self.start_time,
            end_time    = self.end_time,
            metadata    = nextcord.EntityMetadata(location = self.location),
            entity_type = nextcord.ScheduledEventEntityType.external,
        )
        return True
    
    
    async def unschedule(self, guild: nextcord.Guild) -> bool:
        '''Delete the scheduled event.'''
        
        event = self.fetch(guild)
        if not event:
            return False
        
        await event.delete()
        return True
    
    
    async def reschedule(self, guild: nextcord.Guild, old_event: Self) -> bool:
        '''Modify the scheduled event.'''
        
        if self.fetch(guild) or guild.id != self.guild_id:
            return False
        
        event = old_event.fetch(guild)
        if not event:
            return False

        await event.edit(
            name        = self.category,
            description = self.description,
            start_time  = self.start_time,
            end_time    = self.end_time,
            metadata    = nextcord.EntityMetadata(location=self.location),
        )

        return True
    

    # Embed Display
    _color_to_emoji = {
        'green': '🟢',
        'yellow': '🟡',
        'orange': '🟠',
        'red': '🔴',
        'gray': '🔒', # Gray = Closed
    }
    def _time_str(
            self,
            color: Literal['green', 'yellow', 'orange', 'red', 'gray'] = 'green',
        ) -> str:

        start_time, end_time = self.start_time, self.end_time
        duration = (end_time - start_time).days + 1
        now = datetime.datetime.now().astimezone(zoneinfo.ZoneInfo(timezone))

        if duration > 14 or (end_time - now).days // 365 >= 1:
            # Long format
            # {emoji} 10/12/2029
            # at 10:30 {op_emoji}
            if now < start_time:
                return (
                    f'🔒 {start_time.day:02}/{start_time.month:02}/{start_time.year}\n'
                    f'at {start_time.strftime("%H:%M")} 🔓'
                )
            else:
                emoji = Event._color_to_emoji[color]
                return (
                    f'{emoji} {end_time.day:02}/{end_time.month:02}/{end_time.year}\n'
                    f'at {end_time.strftime("%H:%M")} 🔒'
                )

        if end_time.day - start_time.day == 0:
            # Short format
            # Lunes 10/12
            #  10:30 - 12:30
            if color == 'orange' or color == 'red':
                return (
                    f'"{weekdays[start_time.weekday()]}" {end_time.day:02}/{end_time.month:02}\n'
                    f' {start_time.strftime("%H:%M")} - {end_time.strftime("%H:%M")}'
                )
             
            return (
                f'{weekdays[start_time.weekday()]} {end_time.day:02}/{end_time.month:02}\n'
                f' {start_time.strftime("%H:%M")} - {end_time.strftime("%H:%M")}'
            )
            
        else:   
            # Medium format
            # L-10/12  M-11/12
            #  10:30    12:30
            return (
                f'{weekdays_abbr[start_time.weekday()]}-{start_time.day:02}/{start_time.month:02}  '
                f'{weekdays_abbr[end_time.weekday()]}-{end_time.day:02}/{end_time.month:02}\n'
                f' {start_time.strftime("%H:%M")}    {end_time.strftime("%H:%M")}'
            )
            pass
    
    def _red_embed_value(self) -> str:
        '''Generate a red embed value for events that occur in a single day.'''
        return (
            '```ml\n'
            f'  {unidecode(self.description.title())}\n'
            + self._time_str(color='red') +
            '```'
        )

    def _orange_embed_value(self) -> str:
        '''Generate an orange embed value for events that occur in a single day.'''
        return (
            f'```prolog\n  {unidecode(self.description.title())}\n'
            + self._time_str(color='orange') +
            '```'
        )

    def _yellow_embed_value(self) -> str:
        '''Generate a yellow embed value for events that occur in a single day.'''
        return (
            f'```asciidoc\n>  {self.description} :: \n'
            + self._time_str(color='yellow') +
            '```'
        )

    def _green_embed_value(self) -> str:
        '''Generate a green embed value for events that occur in a single day.'''
        return (
            f'```md\n> {self.description}\n'
            + self._time_str(color='green') +
            '```'
        )

    def _gray_embed_value(self) -> str:
        '''Generate a gray embed value for events that occur in a single day.'''
        return (
            f'```ini\n #{self.description}\n'
            + self._time_str(color='gray') +
            '```'
        )

    def prep_embed(self) -> tuple[str, str]:
        '''Prepare the title and value for the embed.'''

        now = datetime.datetime.now().astimezone(zoneinfo.ZoneInfo(timezone))
        start_time, end_time = self.start_time, self.end_time
        
        duration = (end_time - start_time).days + 1
        time_until = (
            end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            - now.replace(hour=0, minute=0, second=0, microsecond=0)
        ).days
        
        title = f'{months[end_time.month - 1]} {end_time.day:02}  —  **{self.category}**'
        title = f'**{self.category}**'

        if duration > 14 and now < start_time:
            return '🔒 ' + title, self._gray_embed_value()



        if time_until > 14:
            return '🟢 ' + title, self._green_embed_value()
        if time_until > 7:
            return '🟡 ' + title, self._yellow_embed_value()
        if time_until > 2:
            return '🟠 ' + title, self._orange_embed_value()
        if time_until >= 0:
            return '🔴 ' + title, self._red_embed_value()
        return '🔒 ' + title, self._gray_embed_value()
    

# async def actualizarEventosExtra(interaction: nextcord.Interaction, dbpath: str) -> None:
#         actualizarDB(dbpath)
#         calendarioLista = getCalendarioFromDB(dbpath)
#         eventos = interaction.guild.scheduled_events
#         for evento in eventos:
#             if not await isEventInCalendar(evento, calendarioLista):
#                 await evento.delete()
#         for evento in calendarioLista:
#             if not await isEventScheduled(interaction.guild, evento):
#                 await createEvent(interaction.guild, evento)
#         await deleteDupedEvents(interaction.guild)