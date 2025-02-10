from typing import Self, Iterable
import os
import datetime, zoneinfo

import nextcord

from configparser import ConfigParser
config = ConfigParser()

config.read(os.path.join('config', 'config.ini'))
timezone = config['DEFAULT']['timezone']

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