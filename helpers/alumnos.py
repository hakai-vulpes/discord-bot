import re
from unidecode import unidecode
from keys import *

async def alumno(stringInput: str) -> str:
    raw = htmlExtract

    students = re.findall(r"Seleccionar '[^']*'", raw)
    for index, name in enumerate(students):
        students[index] = unidecode(name[13:len(name)-1].lower())

    alumnoString = unidecode(stringInput.lower())
    alumno = alumnoString.split()

    samples = []
    for part in alumno:
        sample = set()
        for index, name in enumerate(students):
            query = re.findall(part, name)
            if query != []:
                sample.add(name)
        samples.append(sample)

    intersection = samples[0]
    for sample in samples[1:]:
        intersection.intersection_update(sample)

    collisions = list(intersection)
    response = ""
    for collision in collisions:
        response = response + f"{alumnoString.title()} encontrado como {collision.title()}\n"
    response = response.rstrip("\n")
    return response