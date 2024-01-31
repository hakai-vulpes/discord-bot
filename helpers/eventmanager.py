
from extras import *
from helpers.dbmanager import *

async def createEvent(guild: nextcord.Guild, event: dict) -> None:
    me = await guild.fetch_member("1157437526856962141")
    pfp = me.avatar
    name, description = event["Categoría"], event["Descripción"]
    location = event["Ubicación"]
    startTime = datetime.datetime(event["Año"], event["Mes"], event["Día"], int(event["Inicio"][:-3]) - 1, int(event["Inicio"][-2:]))
    endTime = datetime.datetime(event["Año"], event["Mes"], event["Día"], int(event["Final"][:-3]) - 1, int(event["Final"][-2:]))
    now = datetime.datetime.now()
    if startTime < now or endTime < startTime or endTime < now:
        return None
    await guild.create_scheduled_event(name = name,
                                       metadata = nextcord.EntityMetadata(location = location),
                                       description = description,
                                       start_time = startTime,
                                       end_time = endTime, 
                                       entity_type = nextcord.ScheduledEventEntityType.external,
                                       image = pfp)

async def isEventScheduled(guild: nextcord.Guild, inputEvent: dict) -> None:
    events = guild.scheduled_events
    eventsDict = list()

    for event in events:
        day, month, year = event.start_time.day, event.start_time.month, event.start_time.year
        startTime, endTime = f"{event.start_time.hour + 1}:{event.start_time.minute:02}", f"{event.end_time.hour + 1}:{event.end_time.minute:02}"
        eventsDict.append(dict(zip(["Categoría", "Descripción", "Día", "Mes", "Año", "Inicio", "Final", "Ubicación"],
                                   [event.name, event.description, day, month, year, startTime, endTime, event.location])))

    return inputEvent in eventsDict

async def isEventInCalendar(event: nextcord.ScheduledEvent, calendar: list[dict]) -> bool:
    calendar = calendar.copy()
    day, month, year = event.start_time.day, event.start_time.month, event.start_time.year
    startTime, endTime = f"{event.start_time.hour + 1}:{event.start_time.minute:02}", f"{event.end_time.hour + 1}:{event.end_time.minute:02}"
    event = dict(zip(["Categoría", "Descripción", "Día", "Mes", "Año", "Inicio", "Final", "Ubicación"],
                               [event.name, event.description, day, month, year, startTime, endTime, event.location]))

    return event in calendar

async def fetchEvent(guild: nextcord.Guild, inputEvent: dict) -> nextcord.ScheduledEvent | None:
    events = guild.scheduled_events

    eventDict = dict()
    for event in events:
        day, month, year = event.start_time.day, event.start_time.month, event.start_time.year
        startTime, endTime = f"{event.start_time.hour + 1}:{event.start_time.minute:02}", f"{event.end_time.hour + 1}:{event.end_time.minute:02}"
        eventDict = (dict(zip(["Categoría", "Descripción", "Día", "Mes", "Año", "Inicio", "Final", "Ubicación"],
                                   [event.name, event.description, day, month, year, startTime, endTime, event.location])))
        if inputEvent == eventDict:
            return event

async def deleteEvent(guild: nextcord.Guild, event: dict) -> bool:
    a = await fetchEvent(guild, event)
    if a: 
        await a.delete()
        return True
    return False


async def editEvent(guild: nextcord.Guild, event: dict, newEvent: dict) -> bool:
    a = await fetchEvent(guild, event)
    if a: 
        name, description, location = newEvent["Categoría"], newEvent["Descripción"], newEvent["Ubicación"]
        startTime = datetime.datetime(newEvent["Año"], newEvent["Mes"], newEvent["Día"], int(newEvent["Inicio"][:-3]) - 1, int(newEvent["Inicio"][-2:]))
        endTime = datetime.datetime(newEvent["Año"], newEvent["Mes"], newEvent["Día"], int(newEvent["Final"][:-3]) - 1, int(newEvent["Final"][-2:]))
        await a.edit(name = name, description = description, start_time = startTime, end_time = endTime, metadata = nextcord.EntityMetadata(location = location))
        return True
    return False

async def actualizarEventosExtra(interaction: nextcord.Interaction, dbpath: str) -> None:
        await actualizarDB(dbpath)
        calendarioLista = await getCalendarioFromDB(dbpath)
        eventos = interaction.guild.scheduled_events
        for evento in eventos:
            if not await isEventInCalendar(evento, calendarioLista):
                await evento.delete()
        for evento in calendarioLista:
            if not await isEventScheduled(interaction.guild, evento):
                await createEvent(interaction.guild, evento)