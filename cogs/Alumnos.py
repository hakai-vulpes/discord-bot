import sys, os
#Añado el directorio de main al path para acceder a mis librerías
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import nextcord
from nextcord import Interaction, SlashOption
from nextcord.ext import commands

from helpers.alumnos import alumno
from extras import *

class Alumnos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_any_role(staffRoles)
    @nextcord.slash_command(name = 'alumnos', description = 'Para buscar un alumno.', guild_ids = guildList)
    async def alumnos(self, interaction: Interaction, búsqueda: str):
        print("Comando alumnos")
        if búsqueda:
            if result := await alumno(búsqueda):
                await interaction.response.send_message(result)
            else:
                await interaction.response.send_message("No se han encontrado resultados.")
        else:
            await interaction.response.send_message("Inserta nombre, apellidos... Lo que te apetezca y en el orden que quieras.")

    #@commands.command(name = 'alumnos', brief = 'Para buscar un alumno.', help = 'Uso: !alumnos <nombre>.\nEjemplo: !alumnos Daniel Navarro')
    

def setup(bot):
    bot.add_cog(Alumnos(bot))