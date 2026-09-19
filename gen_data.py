# -*- coding: utf-8 -*-
"""Generate the DEMONSTRATION inventory for the jxjets preview.

Why this file exists at all, and what it deliberately does NOT do:

The client's spreadsheet holds 5 415 real listings scraped from Sandhills
(Controller.com / Trade-A-Plane). The listing text, the photographs and the
sellers' phone numbers belong to those sellers. None of it is published here.

What IS reused is the *vocabulary*: the set of (category, manufacturer, model)
triples — aircraft type names are public product names, not listing content.
Everything else below — years, hours, prices, references, locations — is
generated, and the page says so in the banner.

Deterministic: a fixed seed, so a rebuild does not reshuffle the grid and two
screenshots taken a day apart still match.

    python3 gen_data.py   ->  assets/data.js
"""

import io
import json
import os
import random

ICI = os.path.dirname(os.path.abspath(__file__))
RND = random.Random(20260919)

# Price bands per category, in USD. Invented, but in the right order of
# magnitude so the price filter has something honest to bite on.
BANDES = {
    'Jet Aircraft':             (1_200_000, 38_000_000),
    'Turboprop Aircraft':       (450_000, 6_500_000),
    'Turbine Helicopters':      (390_000, 4_800_000),
    'Piston Twin Aircraft':     (85_000, 950_000),
    'Piston Single Aircraft':   (38_000, 780_000),
    'Piston Helicopters':       (95_000, 520_000),
    'Light Sport Aircraft':     (42_000, 210_000),
    'Experimental/Homebuilt Aircraft': (28_000, 260_000),
    'Piston Military Aircraft': (120_000, 1_900_000),
    'Turbine Military Aircraft': (600_000, 7_500_000),
    'Turbine Agricultural Aircraft': (250_000, 1_400_000),
    'Piston Agricultural Aircraft': (60_000, 320_000),
    'Piston Amphibious/Floatplanes': (95_000, 690_000),
    'Turbine Amphibious/Floatplanes': (700_000, 3_900_000),
    'Drones':                   (2_500, 68_000),
    'Flight Simulators':        (35_000, 480_000),
    'Other':                    (15_000, 240_000),
}
DEFAUT = (12_000, 180_000)

# Deliberately generic. No company from the client's file appears here.
BASES = [
    ('Geneva', 'Switzerland'), ('Farnborough', 'United Kingdom'),
    ('Le Bourget', 'France'), ('Montreal', 'Canada'),
    ('Teterboro', 'United States'), ('Dubai', 'United Arab Emirates'),
    ('Vienna', 'Austria'), ('Lisbon', 'Portugal'),
    ('Casablanca', 'Morocco'), ('Singapore', 'Singapore'),
    ('Dublin', 'Ireland'), ('Oslo', 'Norway'),
]

ETATS = ['Available', 'Available', 'Available', 'Under offer', 'Just listed']

# How many demo aircraft per category. Mirrors the shape of the real file
# (piston singles dominate, then jets) without carrying any of its content.
QUOTA = {
    'Piston Single Aircraft': 16, 'Jet Aircraft': 14, 'Turboprop Aircraft': 9,
    'Turbine Helicopters': 7, 'Piston Twin Aircraft': 6,
    'Piston Helicopters': 4, 'Light Sport Aircraft': 3,
    'Experimental/Homebuilt Aircraft': 3, 'Piston Military Aircraft': 2,
    'Drones': 2, 'Turbine Military Aircraft': 2,
    'Turbine Agricultural Aircraft': 2, 'Flight Simulators': 1,
    'Piston Amphibious/Floatplanes': 2, 'Turbine Amphibious/Floatplanes': 1,
}


def arrondi(n):
    """Prices in a shop window are never 1 234 567."""
    if n >= 5_000_000:
        return int(round(n / 250_000.0) * 250_000)
    if n >= 1_000_000:
        return int(round(n / 50_000.0) * 50_000)
    if n >= 100_000:
        return int(round(n / 5_000.0) * 5_000)
    return int(round(n / 1_000.0) * 1_000)


def main():
    types = json.load(io.open(os.path.join(ICI, '_types.json'), encoding='utf-8'))
    par_cat = {}
    for cat, mfr, mod, _n in types:
        par_cat.setdefault(cat, []).append((mfr, mod))

    listings = []
    ref = 4100
    for cat, combien in QUOTA.items():
        dispo = par_cat.get(cat) or []
        if not dispo:
            continue
        # sample without repeating a type inside a category
        choix = RND.sample(dispo, min(combien, len(dispo)))
        lo, hi = BANDES.get(cat, DEFAUT)
        for mfr, mod in choix:
            ref += 7
            an = RND.randint(1998, 2024)
            # older airframes sit lower in the band
            age = (2025 - an) / 27.0
            prix = arrondi(hi - (hi - lo) * (age ** 0.85) * RND.uniform(.72, 1.0))
            heures = int(RND.uniform(180, 9800))
            ville, pays = RND.choice(BASES)
            listings.append({
                'ref': 'JX-%d' % ref,
                'cat': cat,
                'mfr': mfr,
                'model': mod,
                'year': an,
                'price': max(prix, lo),
                'hours': heures,
                'city': ville,
                'country': pays,
                'status': RND.choice(ETATS),
                # a stable hue per aircraft, used to draw the SVG plate.
                # Kept inside the red family: a red site with rainbow cards
                # reads as an accident rather than a palette.
                'hue': RND.choice([348, 352, 356, 0, 4, 8, 12, 16, 20, 24,
                                   358, 6, 14, 344]),
                'tilt': round(RND.uniform(-7, 7), 1),
                # silhouette family — a helicopter drawn as an airliner is the
                # kind of detail a buyer notices immediately
                'shape': ('heli' if 'Helicopter' in cat else
                          'drone' if cat == 'Drones' else
                          'plane'),
                # varied plate heights are what makes the masonry visible;
                # taken from the data so a rebuild does not reshuffle the grid
                'ar': RND.choice(['16/10', '16/10', '4/3', '16/9', '5/4']),
                # A photograph goes here when there is one to show. Empty in
                # the preview on purpose: the source file's photos belong to
                # Sandhills and to the sellers, so none is reproduced.
                'img': '',
            })

    RND.shuffle(listings)
    cats = sorted({l['cat'] for l in listings})
    mfrs = sorted({l['mfr'] for l in listings})
    out = ('/* GENERATED by gen_data.py — do not edit by hand.\n'
           '   Demonstration inventory. Aircraft types are real product names;\n'
           '   years, hours, prices, references and locations are generated. */\n'
           'window.JX = %s;\nwindow.JX_CATS = %s;\nwindow.JX_MFRS = %s;\n' % (
               json.dumps(listings, indent=0, sort_keys=True),
               json.dumps(cats), json.dumps(mfrs)))
    io.open(os.path.join(ICI, 'assets', 'data.js'), 'w', encoding='utf-8').write(out)
    print('%d demo listings, %d categories, %d manufacturers' % (
        len(listings), len(cats), len(mfrs)))
    print('price range %s - %s' % (
        min(l['price'] for l in listings), max(l['price'] for l in listings)))


if __name__ == '__main__':
    main()
