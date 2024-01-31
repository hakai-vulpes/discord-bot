import re, os, datetime, copy, functools, nextcord
import sqlite3 as sql
from unidecode import unidecode
from keys import *

header = ["Categoría", "Descripción", "Día", "Mes", "Año", "Inicio", "Final", "Ubicación"]
currentWorkingDirectory = "" if os.getcwd().split("\\")[-1] == "DiscordBot" else "DiscordBot/"
staffRoles = [1159163038130245773]
guildList = [1150748183106957352, 473511544454512642, 1158900225117794425]

guild1 = {'guildId': 1150748183106957352,
          'botChannel': [1158458710973223002, 1159163614654115871, 1159164191861645474],
          'verificationChannel': 1158762279706308608,
          'verificationReceiverChannel': 1163938979515740201}

guild2 = {'guildId': 473511544454512642, 'botChannel': [473573431405969443]}
guild3 = {'guildId': 1158900225117794425, 'botChannel': [1159056096753881198]}
botId = 1157437526856962141

weekdays = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

mesesDict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}

mesesDict = {
            1:"Ene",
            2:"Feb",
            3:"Mar",
            4:"Abr",
            5:"May",
            6:"Jun",
            7:"Jul",
            8:"Ago",
            9:"Sept",
            10:"Oct",
            11:"Nov",
            12:"Dic"
            }

def logs(func):
    def wrapper(*args, **kwargs):
        print(f'Función {func.__name__}')
        return func(*args, **kwargs)
    return wrapper

def error(error) -> bool:
    print(error or "Error")
    return error or "Error"

def splitTime(inputStr: str) -> str:
    integer = int(inputStr[:-3] + inputStr[-2:])
    string1 = f"{integer:03}"
    return f"{string1[:-2]}:{string1[-2:]}"

def backup(load: bool = False) -> bool:
    lista = [["database.db", "backups/temp.db"],
             ["backups/database-backup1.db", "database.db"],
             ["backups/database-backup2.db", "backups/database-backup1.db"],
             ["backups/temp.db", "backups/database-backup2.db"]] if load else [["backups/database-backup1.db", "backups/database-backup2.db"],
                                                                               ["database.db", "backups/database-backup1.db"]]
    for backup in lista:
        with sql.connect(currentWorkingDirectory + backup[0]) as db0:
            with sql.connect(currentWorkingDirectory + backup[1]) as db1:
                db0.backup(db1)
    if load: return True
    print("Backup was created")
    return True

async def intToStrDate(integer: int) -> str:
    integer = str(integer)
    return f"{'0'*(max(2-len(integer[:-2]),0))}{integer[:-2]}:{integer[-2:]}" if len(integer) > 2 else f"00:{integer}"
async def strDateToInt(strDate: str) -> int:
    return int(strDate[:-3] + strDate[-2:]) if strDate is not None else None

async def parseToSQLParams(evento: dict, union: str = ", ") -> str:
    def helper(param):
        return f"'{param}'" if isinstance(param, str) else param
    return union.join(f"{element[0]} = {helper(element[1])}" for element in evento.items() if element[1] is not None)

# Week calculator
async def fecha(*args) -> int:
    if len(args) != 3:
        raise Exception(f"Expected 3 numbers for a date not {args}")
    followingDate = [arg for arg in args]

    if followingDate[1] == 0:
        followingDate[1] = 12
        followingDate[2] -= 1
    month = {}
    for i in range(1,13):
        match i:
            case 4 | 6 | 9 | 11:
                month[i] = 30
            case 2:
                month[i] = 28
            case other:
                month[i] = 31
    # Leap year handler
    def yearToDays(year):
        if year % 4 == 0:
            return 366
        return 365

    now = datetime.datetime.now()
    weeks = 0
    # Counting days --> converting into weeks
    dayCount = followingDate[0] - now.day
    for i in range(now.month, followingDate[1]):
        dayCount += month[i]
    for i in range(followingDate[1], now.month):
        dayCount -= month[i]
    for i in range(now.year, followingDate[2]):
        dayCount += yearToDays(i)
    for i in range(followingDate[2], now.year):
        dayCount -= yearToDays(i)
    weeks = dayCount // 7 + 1
    return(weeks)

async def procesarfecha(input: str) -> list[int]:
    try:
        fecha = [int(string) for string in re.split(r"[^\d]", input) if string]
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
        return fecha
    except: return False

async def parseToDict(lista: list) -> dict:
    return {clave:valor for clave, valor in zip(header, lista)}

class AnnouncementView(nextcord.ui.View):
    def __init__(self, opciones, callback, timeout: float | None, auto_defer: bool = True, prevent_update: bool = True) -> None:
        super().__init__(timeout=timeout, auto_defer=auto_defer, prevent_update=prevent_update)
        self.opciones = opciones
        self.genericCallback = callback
        self.message = None

        for index, opcion in enumerate(self.opciones):
            button = nextcord.ui.Button(label=opcion, style=nextcord.ButtonStyle.blurple)
            button.callback = self.genericCallback(index)
            self.add_item(button)   

    def registerMessage(self, message: nextcord.Message):
        self.message = message

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message: await self.message.edit(content="(Esta votación ha finalizado)", view=self)
