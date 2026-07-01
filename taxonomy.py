"""
Vaste taxonomie voor de inhoudelijke analyse.

C2/C5: de onderwerpen zijn VOORAF vastgelegd (geen vrije labels per gesprek),
zodat de percentages in het rapport optelbaar en vergelijkbaar zijn.

Deze lijst is een startpunt op basis van het Voltafy-voorbeeld en Toteco's
domein (zonnepanelen, warmtepompen, thuisbatterijen). Bijstellen kan, maar
DOE DAT HIER op één plek — niet in de prompt of in de UI.
"""

ONDERWERPEN = [
    "Levering & installatie",
    "Storing / technisch",
    "Afspraak plannen/verzetten",
    "Warmtefonds / subsidie",
    "BTW / facturen / terugbetalingen",
    "Energiecontract / tarief / app",
    "Annuleren / herroepen",
    "Klacht bereikbaarheid/communicatie",
    "Intern (doorschakel/planning)",
    "Overig / administratief",
]

SENTIMENTEN = ["positief", "neutraal", "negatief"]
