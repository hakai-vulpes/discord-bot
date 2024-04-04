from typing import Optional
import nextcord, datetime, asyncio, re

from nextcord.interactions import Interaction
from nextcord.ui.item import Item
from extras import *
from keys import *
from unidecode import unidecode
from nextcord.ext import commands


intents = nextcord.Intents.all()
intents.members = True

bot = commands.Bot(command_prefix = "!", intents =  intents)

guildList = [473511544454512642]

import smtplib, ssl, secrets
from email.message import EmailMessage

emailPattern = re.compile(r"^[a-zA-Z0-9_.+-]+@alumnos.upm.es$")
def validate_email_syntax(email):
    return re.match(emailPattern, email) is not None
    
async def sendConfirmationEmail(address, token):
    subject = "Email Confirmation"
    body = f"Este es tu código de confirmación: {token}"
    email = EmailMessage()
    email['From'], email['To'], email['Subject'] = EMAIL_ADDR, address, subject
    email.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(EMAIL_ADDR, EMAIL_PASS)
        smtp.sendmail(EMAIL_ADDR, address, email.as_string())

def isPrime(n: int) -> bool:
    for i in range(2,n):
        if n % i == 0: return False
    return True

@commands.has_permissions(manage_messages=True)
@bot.slash_command(name = "lol", description = 'Correo',  guild_ids=guildList)
async def lol(interaction: nextcord.Interaction, num: int = 0):
    await interaction.response.defer()
    if isPrime(num):
        await interaction.followup.send('It is prime')
        return True
    await interaction.followup.send("It isn't prime")
    return False

@commands.has_permissions(manage_messages=True)
@bot.slash_command(name = "correo", description = 'Correo',  guild_ids=guildList)
async def correo(interaction: nextcord.Interaction, email: str = ""):

    if not validate_email_syntax(email):
        return await interaction.response.send_message("Sintaxis de correo incorrecta.")
    token = secrets.token_urlsafe(6)
    await interaction.response.send_modal(EmailVerificationModal(token))
    await sendConfirmationEmail(email, token)
    print(interaction)

@bot.event
async def on_ready():
    print("The bot is running! :3\n")

bot.run(TOKEN)