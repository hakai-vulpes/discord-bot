
from extras import *
from helpers.dbmanager import *
mytimezone = pytz.timezone('Europe/Madrid')
utc = pytz.utc
now = utc.localize(datetime.datetime.utcnow())

async def createEvent(guild: nextcord.Guild, event: dict) -> None:
    me = await guild.fetch_member("1157437526856962141")
    pfp = me.avatar
    name, description = event["Categoría"], event["Descripción"]
    location = event["Ubicación"]
    start = mytimezone.localize(datetime.datetime(event["Año"], event["Mes"], event["Día"], int(event["Inicio"][:-3]), int(event["Inicio"][-2:])))
    end = mytimezone.localize(datetime.datetime(event["Año"], event["Mes"], event["Día"], int(event["Final"][:-3]), int(event["Final"][-2:])))
    start = start.astimezone(utc)
    end = end.astimezone(utc)

    if start < now or end < start or end < now:
        return None
    await guild.create_scheduled_event(name = name,
                                       metadata = nextcord.EntityMetadata(location = location),
                                       description = description,
                                       start_time = start,
                                       end_time = end, 
                                       entity_type = nextcord.ScheduledEventEntityType.external,
                                       image = pfp)

async def isEventScheduled(guild: nextcord.Guild, inputEvent: dict) -> None:
    events = guild.scheduled_events
    eventsDict = list()

    for event in events:
        start = utc.localize(datetime.datetime(event.start_time.year, event.start_time.month, event.start_time.day, event.start_time.hour, event.start_time.minute))
        end = utc.localize(datetime.datetime(event.start_time.year, event.start_time.month, event.start_time.day, event.end_time.hour, event.end_time.minute))
        start = start.astimezone(mytimezone)
        end = end.astimezone(mytimezone)

        startTime, endTime = f"{start.hour:02}:{start.minute:02}", f"{end.hour:02}:{end.minute:02}"
        eventsDict.append(dict(zip(["Categoría", "Descripción", "Día", "Mes", "Año", "Inicio", "Final", "Ubicación"],
                                   [event.name, event.description, start.day, start.month, start.year, startTime, endTime, event.location])))

    return inputEvent in eventsDict

async def isEventInCalendar(event: nextcord.ScheduledEvent, calendar: list[dict]) -> bool:
    start = utc.localize(datetime.datetime(event.start_time.year, event.start_time.month, event.start_time.day, event.start_time.hour, event.start_time.minute))
    end = utc.localize(datetime.datetime(event.start_time.year, event.start_time.month, event.start_time.day, event.end_time.hour, event.end_time.minute))
    start = start.astimezone(mytimezone)
    end = end.astimezone(mytimezone)
    
    startTime, endTime = f"{start.hour:02}:{start.minute:02}", f"{end.hour:02}:{end.minute:02}"
    event = dict(zip(["Categoría", "Descripción", "Día", "Mes", "Año", "Inicio", "Final", "Ubicación"],
                               [event.name, event.description, start.day, start.month, start.year, startTime, endTime, event.location]))
    return event in calendar

async def fetchEvent(guild: nextcord.Guild, inputEvent: dict) -> nextcord.ScheduledEvent | None:
    events = guild.scheduled_events

    eventDict = dict()
    for event in events:
        start = utc.localize(datetime.datetime(event.start_time.year, event.start_time.month, event.start_time.day, event.start_time.hour, event.start_time.minute))
        end = utc.localize(datetime.datetime(event.start_time.year, event.start_time.month, event.start_time.day, event.end_time.hour, event.end_time.minute))
        start = start.astimezone(mytimezone)
        end = end.astimezone(mytimezone)
        startTime, endTime = f"{start.hour:02}:{start.minute:02}", f"{end.hour:02}:{end.minute:02}"
    
        eventDict = (dict(zip(["Categoría", "Descripción", "Día", "Mes", "Año", "Inicio", "Final", "Ubicación"],
                                   [event.name, event.description, start.day, start.month, start.year, startTime, endTime, event.location])))
        if inputEvent == eventDict:
            return event

async def deleteEvent(guild: nextcord.Guild, event: dict) -> bool:
    a = await fetchEvent(guild, event)
    if a: 
        await a.delete()
        return True
    return False

async def editEvent(guild: nextcord.Guild, event: dict, newEvent: dict) -> bool:
    print(newEvent)
    a = await fetchEvent(guild, event)
    if a: 
        name, description, location = newEvent["Categoría"], newEvent["Descripción"], newEvent["Ubicación"]
        start = mytimezone.localize(datetime.datetime(newEvent["Año"], newEvent["Mes"], newEvent["Día"], int(newEvent["Inicio"][:-3]), int(newEvent["Inicio"][-2:])))
        end = mytimezone.localize(datetime.datetime(newEvent["Año"], newEvent["Mes"], newEvent["Día"], int(newEvent["Final"][:-3]), int(newEvent["Final"][-2:])))
        start = start.astimezone(utc)
        end = end.astimezone(utc)
        await a.edit(name = name, description = description, start_time = start, end_time = end, metadata = nextcord.EntityMetadata(location = location))
        return True
    return False

async def deleteDupedEvents(guild: nextcord.Guild) -> None:
    events = guild.scheduled_events
    eventsTuples = [(event.name, event.description, event.start_time, event.end_time) for event in events]
    instancedEvents = set()
    for i in range(len(eventsTuples)):
        if eventsTuples[i] in instancedEvents:
            await events[i].delete()
        else:
            instancedEvents.add(eventsTuples[i])

async def actualizarEventosExtra(interaction: nextcord.Interaction, dbpath: str) -> None:
        actualizarDB(dbpath)
        calendarioLista = getCalendarioFromDB(dbpath)
        eventos = interaction.guild.scheduled_events
        for evento in eventos:
            if not await isEventInCalendar(evento, calendarioLista):
                await evento.delete()
        for evento in calendarioLista:
            if not await isEventScheduled(interaction.guild, evento):
                await createEvent(interaction.guild, evento)
        await deleteDupedEvents(interaction.guild)