import sys, os
import sqlite3 as sql
#Añado el directorio de main al path para acceder a mis librerías
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import nextcord
from nextcord import Interaction, SlashOption
from nextcord.ext import commands

import re, asyncio, datetime
from unidecode import unidecode
from extras import *
from helpers.eventmanager import *


class Calendario(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_any_role(staffRoles)
    @nextcord.slash_command(name = 'agregar', description = 'Agregar un evento al calendario', guild_ids = guildList)#, help = 'Uso: !agregar "<categoría>" "<descripción>" <DD/MM/AAAA> <hh:mm-hh:mm>\nEjemplo: !agregar examen "álgebra lineal" 23/10/2023 9:00-11:00')
    async def agregar(self, interaction: Interaction, categoría: str, descripción: str, fecha: str, hora_inicio: str = "0:00", hora_final: str = "23:59", ubicación: str = ""):
        print("Comando agregar")
        if ubicación == "": ubicación = "ETSISI - UPM"
        else: ubicación += " - ETSISI - UPM"
        #Input handler
        try:
            if not (fecha := await procesarfecha(fecha)):
                await interaction.response.send_message(error("Fecha en formato incorrecto: <DD/MM/YY>"))
                return False
        except:
            await interaction.response.send_message(error("Error de argumentos"))
            return False
        hora_inicio, hora_final = await strDateToInt(hora_inicio), await strDateToInt(hora_final)
        
        evento = [categoría, descripción, fecha[0], fecha[1], fecha[2], hora_inicio, hora_final, ubicación]
        evento = await parseToDict(evento)
        if not await putEventInDB(evento, currentWorkingDirectory + "database.db"):
            await interaction.response.send_message("Ha habido un error, puede que este evento ya exista...")
            return False
        
        await interaction.response.send_message(f"Evento añadido ({evento})")
        await createEvent(interaction.guild, evento)
        await actualizarEventosExtra(interaction, currentWorkingDirectory + "database.db")

    @nextcord.slash_command(name = 'calendario', description = 'Mostrar el calendario.', guild_ids = guildList)
    async def calendario(self, interaction: Interaction):
        print("Comando calendario")
        titlelength = 27
        #Sacar los datos de la DB ordenados
        await actualizarEventosExtra(interaction, currentWorkingDirectory + "database.db")
        calendario = await calendarioOrdenado(currentWorkingDirectory + "database.db")

        #Generar embed y normalizar los recuadros
        calendarioEmbed = nextcord.Embed(title="***CALENDARIO DE EVENTOS***", color=0xff6700)
        embedList = list()
        for thrice, evento in enumerate(calendario):
            print(evento["Inicio"], evento["Final"])
            embedValue = ""
            if await fecha(evento["Día"],evento["Mes"],evento["Año"]) == 1:
                embedValue = f'''```ml\n[{splitTime(evento["Inicio"])}-{splitTime(evento["Final"])}]\n  {unidecode(evento["Descripción"].title())} ({weekdays[datetime.datetime(evento["Año"],evento["Mes"],evento["Día"]).weekday()]})```'''
            elif await fecha(evento["Día"],evento["Mes"],evento["Año"]) == 2:
                embedValue = f'''```prolog\n[{splitTime(evento["Inicio"])}-{splitTime(evento["Final"])}]\n  {unidecode(evento["Descripción"].title())} ({weekdays[datetime.datetime(evento["Año"],evento["Mes"],evento["Día"]).weekday()]})```'''
            elif await fecha(evento["Día"],evento["Mes"],evento["Año"]) == 3:
                embedValue = f'''```asciidoc\n[{splitTime(evento["Inicio"])}-{splitTime(evento["Final"])}]\n>  {evento["Descripción"]} ({weekdays[datetime.datetime(evento["Año"],evento["Mes"],evento["Día"]).weekday()]}) :: ```'''
            elif await fecha(evento["Día"],evento["Mes"],evento["Año"]) > 3:
                embedValue = f'''```md\n[{splitTime(evento["Inicio"])}-{splitTime(evento["Final"])}]\n> {evento["Descripción"]} ({weekdays[datetime.datetime(evento["Año"],evento["Mes"],evento["Día"]).weekday()]})```'''
            else:
                embedValue = f'''```ini\n#[{splitTime(evento["Inicio"])}-{splitTime(evento["Final"])}]\n #{evento["Descripción"]} ({weekdays[datetime.datetime(evento["Año"],evento["Mes"],evento["Día"]).weekday()]})```'''
            embedName = f"{thrice + 1}. {mesesDict[evento['Mes']]} {evento['Día']:02}  —  **{evento['Categoría']}**"
            embedList.append([embedName, embedValue])
            if thrice % 3 == 2:
                pass
        #Count to consider automatic line breaking
        nameLengthsList, nameLengthsListExtra, valueLengthsList = [], [], []
        linebreakCounter = 0
        for index, nameValueList in enumerate(embedList):
            if index % 3 == 0 and index != 0:
                linebreakCounter = 0
                linebreakCounter += 0
                linebreakCounter += max(valueLengthsList)
                for jndex, nameValueListChanger in enumerate(embedList[index-3:index]):
                    _, valueChanger = nameValueListChanger
                    embedList[jndex + index-3][1] = embedList[jndex + index-3][1][:-3] + "\n " * (linebreakCounter - (valueLengthsList[jndex])) + "```"
                    embedList[jndex + index-3][0] = embedList[jndex + index-3][0] + " " * 2 * (titlelength - nameLengthsListExtra[jndex])+ "-" * (titlelength - 1) * (max(nameLengthsList) - (nameLengthsList[jndex]))
                print(linebreakCounter, valueLengthsList, nameLengthsList, nameLengthsListExtra)
                nameLengthsList, nameLengthsListExtra, valueLengthsList = [], [], []
            if nameValueList[1]:
                name, value = nameValueList
            else:
                continue
            # Title
            titlelength = 37 if nameValueList in embedList[(len(embedList)-1)//3*3:] and len(embedList) % 3 != 0 else 27
            nameLengthsList.append(len(name)//titlelength + 1)
            nameLengthsListExtra.append(len(name)%titlelength)
            # Decription
            characterCounter = -1
            linebreakCounter2 = 1
            linelength = 29 if nameValueList in embedList[(len(embedList)-1)//3*3:] and len(embedList) % 3 != 0 else 18
            for word in re.split(" ", re.findall(r"[\n]+([\w\-\(\)>:# ]+)", value)[0]):
                if len(word) <= linelength:
                    characterCounter += 1 + len(word)
                    if characterCounter > linelength:
                        characterCounter = len(word)
                        linebreakCounter2 += 1
                else:
                    characterCounter = len(word)
                    linebreakCounter2 += 1
                    while characterCounter > linelength:
                        characterCounter -= linelength
                        linebreakCounter2 += 1
                    
            valueLengthsList.append(linebreakCounter2)
        linebreakCounter = 0
        linebreakCounter += 0
        linebreakCounter += max(valueLengthsList)
        for jndex, nameValueListChanger in enumerate(embedList[(len(embedList)-1)//3*3:]):
            _, valueChanger = nameValueListChanger
            embedList[jndex + (len(embedList)-1)//3*3][1] = embedList[jndex + (len(embedList)-1)//3*3][1][:-3] + "\n " * (linebreakCounter - (valueLengthsList[jndex])) + "```"
            embedList[jndex + (len(embedList)-1)//3*3][0] = embedList[jndex + (len(embedList)-1)//3*3][0] + " " * 2 * (titlelength - nameLengthsListExtra[jndex]) + "-" * (titlelength - 1) * (max(nameLengthsList) - (nameLengthsList[jndex]))
        print(linebreakCounter, valueLengthsList, nameLengthsList, nameLengthsListExtra)
        nameLengthsList, nameLengthsListExtra, valueLengthsList = [], [], []


        for thrice, nameValueList in enumerate(embedList):
            name, value = nameValueList
            calendarioEmbed.add_field(name=name, value=value, inline = True)
            if thrice % 3 == 2:
                calendarioEmbed.add_field(name="\u00ad", value="\u00ad", inline = False)

        await interaction.response.send_message(embed = calendarioEmbed)

    @commands.has_any_role(staffRoles)
    @nextcord.slash_command(name = 'modificar', description = 'Modifica un evento del calendario', guild_ids = guildList) # help = 'Uso: !modificar <índice (cronológicamente)> "<categoría>" "<descripción>" <DD/MM/AAAA> <hh:mm-hh:mm>\nEjemplo: !modificar 3 - - 23/10/2023 9:00-11:00, para modificar sólo fecha y hora.')
    async def modificar(self, interaction: Interaction,
                        índice: int, categoría: str = None, descripción: str = None, fecha: str = None, hora_inicio: str = None, hora_final: str = None, ubicación: str = None):
        print("Comando modificar")
        #Input handler
        if ubicación is not None: ubicación += " - ETISISI - UPM"
        if fecha is not None:
            if not (fecha := await procesarfecha(fecha)):
                await interaction.response.send_message(error("Fecha en formato incorrecto: <DD/MM/YY>"))
                return False
        else: fecha = [None, None, None]

        índice -= 1
        args = [categoría, descripción, fecha[0], fecha[1], fecha[2], hora_inicio, hora_final, ubicación]
        args = await parseToDict(args)
        evento = (await calendarioOrdenado(currentWorkingDirectory + "database.db"))[índice]
        newEvent = {clave:argumento or valor for clave, argumento, valor  in zip(header, args.values(), evento.values())}

        await editEvent(interaction.guild, evento, newEvent)
        args.update({"Inicio": await strDateToInt(args["Inicio"]),"Final": await strDateToInt(args["Final"])})
        evento.update({"Inicio": await strDateToInt(evento["Inicio"]),"Final": await strDateToInt(evento["Final"])})
        with sql.connect(currentWorkingDirectory + "database.db") as db:
            cursor = db.cursor()
            cursor.execute(f"UPDATE Events SET {await parseToSQLParams(args)} WHERE {await parseToSQLParams(evento, ' AND ')}")

        await actualizarEventosExtra(interaction, currentWorkingDirectory + "database.db")
        #Feedback
        await interaction.response.send_message(f"Evento modificado ({newEvent})")

    @commands.has_any_role(staffRoles)
    @nextcord.slash_command(name = 'eliminar', description = 'Elimina un evento del calendario', guild_ids = guildList) # help = 'Uso: !eliminar <índice (cronológicamente)>\nEjemplo: !eliminar 3, para eliminar el tercer evento más cercano')
    async def eliminar(self, interaction: Interaction, índice: int):
        print("Comando eliminar")
        índice -= 1
        evento = (await calendarioOrdenado(currentWorkingDirectory + "database.db"))[índice]
                
        #Eliminar el evento
        await deleteEvent(interaction.guild, evento)
        await interaction.response.send_message(f"Evento eliminado ({evento})")
        evento.update({"Inicio": await strDateToInt(evento["Inicio"]),"Final": await strDateToInt(evento["Final"])})
        await removeEventFromDB(evento, currentWorkingDirectory + "database.db")

        await actualizarEventosExtra(interaction, currentWorkingDirectory + "database.db")

    @commands.has_any_role(staffRoles)
    @nextcord.slash_command(name = 'loadbackup', description = 'Recuperar la última copia de seguridad', guild_ids = guildList)# help = 'Uso: !loadbackup, si se usa tres veces seguidas se vuelve a la versión más nueva.')
    async def loadbackup(self, interaction: Interaction):
        if backup(True):
            await interaction.response.send_message("Copia de seguridad cargada")
        else:
            await interaction.response.send_message("Ha habido un error inesperado cargando las copias de seguridad")
        #Actualizar calendario
        await actualizarEventosExtra(interaction, currentWorkingDirectory + "database.db")

    @commands.has_any_role(staffRoles)
    @nextcord.slash_command(name = 'actualizareventos', description = 'Actualiza todos los eventos de Discord con los eventos del calendario', guild_ids = guildList)
    async def actualizareventos(self, interaction: Interaction):
        calendarioLista = await getCalendarioFromDB(currentWorkingDirectory + "database.db")
        eventos = interaction.guild.scheduled_events
        for evento in eventos:
            if not await isEventInCalendar(evento, calendarioLista):
                await evento.delete()
        for evento in calendarioLista:
            if not await isEventScheduled(interaction.guild, evento):
                await createEvent(interaction.guild, evento)

        await interaction.response.send_message("Eventos actualizados correctamente")

    @commands.has_any_role(staffRoles)
    @nextcord.slash_command(name = "anuncio", description = 'Anuncio con votación asociada',  guild_ids=guildList)
    async def announcement(self, interaction: nextcord.Interaction, title: str, text: str, opciones: str, timeout: float = None):
        if timeout is not None: timeout = float(timeout)
        opciones = opciones.split("/")
        opcionesS = "\n"
        for opcion in opciones:
            opcionesS += f"\n{opcion}: 0 voto/s"
        embedeshito = nextcord.Embed(title=f"***{title}***", description=text+opcionesS, color=0xff6700)

        users = {}
        def genericCallback(index):
            nonlocal users
            async def specificCallback(interaction: nextcord.Interaction):
                previousVote = None
                if hash(interaction.user) in users: previousVote = users[hash(interaction.user)]
                if previousVote == index: return None
                users[hash(interaction.user)] = index

                embed = interaction.message.embeds[0]
                title, text = embed.title, embed.description
                textIndex = text[::-1].index("\n\n")
                optionsText, rest = text[-textIndex:], text[:-textIndex]

                options = []
                for option in optionsText.split("\n"):
                    colonIndex = option.index(": ")
                    options.append([option[:colonIndex + 2], option[colonIndex + 2: -7], " voto/s"])
                options[index][1] = str(1 + int(options[index][1]))
                if previousVote is not None: options[previousVote][1] = str(int(options[index][1]) - 1)
                optionsOutput = "\n".join("".join(option) for option in options)

                await sent_message.edit(embed=nextcord.Embed(title=title, description=rest+optionsOutput, color=0xff6700))
            return specificCallback
        vieweshita = AnnouncementView(opciones, genericCallback, timeout)

        sent_message = await interaction.response.send_message(embed=embedeshito, view=vieweshita)
        vieweshita.registerMessage(sent_message)




#Cargar el módulo de Calendario
def setup(bot):
    bot.add_cog(Calendario(bot))