import re, os, datetime, copy, functools, nextcord, pytz, logging
import sqlite3 as sql
from nextcord.utils import MISSING
from unidecode import unidecode
from PIL import ImageFont
from keys import *




snitch = logging.getLogger("snitch")
snitch.setLevel(logging.INFO)
handler = logging.FileHandler("logs.log", "a")
handler.setFormatter(logging.Formatter("%(asctime)s: /%(funcName)s %(message)s"))
snitch.addHandler(handler)

debugger = logging.getLogger("debugger")
debugger.setLevel(logging.DEBUG)
handler = logging.Handler()
handler.setFormatter(logging.Formatter("/%(funcName)s: %(message)s"))
debugger.addHandler(handler)

header = ["Categoría", "Descripción", "Día", "Mes", "Año", "Inicio", "Final", "Ubicación"]
cwd = "" if os.getcwd().split("\\")[-1] == "DiscordBot" else f".{os.sep}DiscordBot{os.sep}"
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

hourPattern = re.compile(r"^[0-2][0-9]:[0-5][0-9]$")
shortenedHourPattern = re.compile(r"^[0-2]{0,1}[0-9]$")
lazyHourPattern = re.compile(r"^[0-9]:[0-5][0-9]$")
veryLazyHourPattern = re.compile(r"^[0-2]{0,1}[0-9][0-5][0-9]$")

#To improve, for the time being it redirects to the function and does nothing
def debug(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def error(error) -> bool:
    print(error or "Error")
    return error or "Error"

def splitTime(inputStr: str) -> str:
    integer = int(inputStr[:-3] + inputStr[-2:])
    string1 = f"{integer:03}"
    return f"{string1[:-2]}:{string1[-2:]}"

@debug
def backup(load: bool = False) -> bool:
    lista = [["database.db", "backups/temp.db"],
             ["backups/database-backup1.db", "database.db"],
             ["backups/database-backup2.db", "backups/database-backup1.db"],
             ["backups/temp.db", "backups/database-backup2.db"]] if load else [["backups/database-backup1.db", "backups/database-backup2.db"],
                                                                               ["database.db", "backups/database-backup1.db"]]
    for backup in lista:
        with sql.connect(cwd + backup[0]) as db0:
            with sql.connect(cwd + backup[1]) as db1:
                db0.backup(db1)
    if load: return True
    #debugger.debug("Backup was created")
    return True

def intToStrDate(integer: int) -> str:
    integer = str(integer)
    return f"{'0'*(max(2-len(integer[:-2]),0))}{integer[:-2]}:{integer[-2:]}" if len(integer) > 2 else f"00:{'0'*(2-len(integer))}{integer}"
def strDateToInt(strDate: str) -> int:
    return int(strDate[:-3] + strDate[-2:]) if strDate is not None else None

def parseToSQLParams(evento: dict, union: str = ", ") -> str:
    def helper(param):
        return f"'{param}'" if isinstance(param, str) else param
    return union.join(f"{element[0]} = {helper(element[1])}" for element in evento.items() if element[1] is not None)

def argumenterParserComander(names: tuple[str], values: tuple) -> str:
    a = " ".join(f"{name}:{value}" for name, value in zip(names, values) if value not in (None, ""))
    return a + " " if a != "" else ""

# Week calculator
def fecha(*args) -> int:
    if len(args) != 3:
        raise Exception(f"Expected 3 numbers for a date not {len(args)} ({args})")
    now = datetime.datetime.now()
    then = datetime.datetime(args[2],args[1],args[0],now.hour,now.minute)
    return (then - now).days // 7 + 1

def procesarFecha(input: str) -> list[int]:
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

def procesarHora(hora):
    if re.match(shortenedHourPattern, hora):
        return intToStrDate(int(hora)*100)
    if re.match(lazyHourPattern, hora):
        return "0" + hora
    if re.match(veryLazyHourPattern):
        return intToStrDate(int(hora))
    raise Exception('Hour format not contemplated')

def parseToDict(lista: list) -> dict:
    return {clave:valor for clave, valor in zip(header, lista)}

font = ImageFont.truetype('DiscordFonts/gg sans Regular.ttf', 14)
def titleFrontEndBullshit(index, month, day, txt, count):
    (width, _), _ = font.font.getsize(f"{index}. {month} {day}  —  **{txt}**")
    return width // 440
    pass

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

class EmailVerificationModal(nextcord.ui.Modal):
    def __init__(self, token) -> None:
        super().__init__('Email Verification', timeout=90)
        self.token = token

        self.verificationField = nextcord.ui.TextInput('Código de Verificación', max_length=30, required=True, placeholder="Introduce el código de verficación enviado a tu correo.")
        self.add_item(self.verificationField)

    async def callback(self, interaction: nextcord.Interaction):
        if not self.verificationField.value == self.token:
            return await interaction.followup.send("Intento de verificación fallido")
        #interaction.user
        return await interaction.followup.send("Verificación completada")