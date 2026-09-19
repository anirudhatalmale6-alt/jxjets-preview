# -*- coding: utf-8 -*-
"""Attach real, reusable photographs to some of the demo listings.

The client asked for images. The photographs in his source spreadsheet are not
usable — they are Sandhills' and the sellers' — so these come from Wikimedia
Commons instead, and only where the licence genuinely permits reuse.

Rules this script enforces, rather than assumes:

  * only PUBLIC DOMAIN / CC0 / CC BY / CC BY-SA are accepted; anything else is
    skipped outright;
  * the author, the licence and the file page are recorded for every single
    photo and printed on the page — a CC BY photo without its credit is a
    licence breach, not a small omission;
  * the aircraft in the photo must match the listing's manufacturer AND model,
    otherwise it is skipped. A Learjet photo on a Cessna card is a lie that
    happens to be legal.

    python3 fetch_photos.py   ->  assets/photos/*.jpg + assets/photos.js
"""

import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
PHOTOS = os.path.join(ICI, 'assets', 'photos')
UA = {'User-Agent': 'jxjets-preview/1.0 (freelance web build; contact via Freelancer.com)'}

OK_LICENCES = ('public domain', 'cc0', 'cc by', 'cc-by')
BAD = ('non-commercial', 'noncommercial', 'nd', 'fair use', 'gfdl only')

# Commons is full of logos, badges and three-view drawings whose titles carry
# the aircraft type. A logo on a listing card looks like a broken photo, so
# these are rejected on the title before anything is downloaded.
PAS_UNE_PHOTO = ('logo', 'emblem', 'insignia', 'badge', 'patch', 'roundel',
                 'diagram', 'drawing', 'silhouette', 'schematic', 'blueprint',
                 'chart', 'map', 'seal', 'icon', 'wordmark', 'livery sticker',
                 'instrument panel', 'poster', 'stamp', 'graph')

COMBIEN = 16          # how many listings get a photograph
LARGEUR = 1000


def api(params, essais=4):
    """Commons rate-limits hard. Back off and retry rather than silently
    recording 'no photo exists' for an aircraft that has plenty."""
    u = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
    for n in range(essais):
        try:
            req = urllib.request.Request(u, headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=40))
        except urllib.error.HTTPError as e:
            if e.code != 429 or n == essais - 1:
                raise
            time.sleep(4 * (n + 1))
    return {}


def ressemble_a_une_photo(octets):
    """Cheap sanity test on the pixels themselves.

    A title filter catches most logos; this catches the rest. A photograph of
    an aircraft has a wide spread of colours and is not mostly white. A logo
    is a handful of flat colours on a white field.
    """
    try:
        from PIL import Image
    except ImportError:
        return True          # no Pillow here: fall back to the title filter
    try:
        im = Image.open(io.BytesIO(octets)).convert('RGB')
    except Exception:
        return False
    im.thumbnail((160, 160))
    px = list(im.getdata())
    if not px:
        return False
    blancs = sum(1 for r, g, b in px if r > 238 and g > 238 and b > 238)
    if blancs > len(px) * 0.55:
        return False
    # distinct colours, quantised — a flat graphic has very few
    teintes = {(r >> 4, g >> 4, b >> 4) for r, g, b in px}
    return len(teintes) >= 60


def nettoie(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html or '')).strip()


def licence_ok(nom):
    n = (nom or '').lower()
    if any(b in n for b in BAD):
        return False
    return any(g in n for g in OK_LICENCES)


def cherche(mfr, model):
    """Find one reusable photo that is really of this aircraft type."""
    requete = 'filetype:bitmap %s %s' % (mfr, model)
    try:
        d = api({'action': 'query', 'format': 'json', 'generator': 'search',
                 'gsrsearch': requete, 'gsrlimit': 10, 'gsrnamespace': 6,
                 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size',
                 'iiurlwidth': LARGEUR})
    except Exception as e:
        print('   search failed: %s' % e)
        return None
    pages = (d.get('query') or {}).get('pages') or {}
    mots = [w for w in re.split(r'[\s/-]+', model.lower()) if len(w) > 1]
    for p in pages.values():
        ii = (p.get('imageinfo') or [{}])[0]
        em = ii.get('extmetadata') or {}
        lic = nettoie(em.get('LicenseShortName', {}).get('value'))
        if not licence_ok(lic):
            continue
        titre = p.get('title', '')
        bas = titre.lower()
        if any(m in bas for m in PAS_UNE_PHOTO):
            continue
        # the type has to be named in the file title, manufacturer included
        if mfr.split()[0].lower() not in bas:
            continue
        if not any(m in bas for m in mots):
            continue
        url = ii.get('thumburl') or ii.get('url')
        if not url:
            continue
        return {
            'url': url,
            'titre': titre,
            'auteur': nettoie(em.get('Artist', {}).get('value')) or 'Unknown',
            'licence': lic,
            'source': ii.get('descriptionurl') or
                      ('https://commons.wikimedia.org/wiki/' + urllib.parse.quote(titre)),
        }
    return None


def main():
    if not os.path.isdir(PHOTOS):
        os.makedirs(PHOTOS)
    data = io.open(os.path.join(ICI, 'assets', 'data.js'), encoding='utf-8').read()
    listings = json.loads(data.split('window.JX = ', 1)[1].split(';\nwindow.JX_CATS', 1)[0])

    # Prefer the expensive, well photographed airframes — that is what a buyer
    # lands on first, and what is most likely to exist on Commons.
    ordre = sorted(listings, key=lambda l: -l['price'])

    deja = {}
    pj = os.path.join(ICI, 'assets', 'photos.js')
    if os.path.exists(pj):
        txt = io.open(pj, encoding='utf-8').read()
        if 'window.JX_PHOTOS = ' in txt:
            deja = json.loads(txt.split('window.JX_PHOTOS = ', 1)[1].rsplit(';', 1)[0])
        deja = {k: v for k, v in deja.items()
                if os.path.exists(os.path.join(ICI, v['img']))}
        print('resuming: %d photos already on disk\n' % len(deja))

    trouve = {}
    for l in ordre:
        if len(trouve) >= COMBIEN:
            break
        if l['ref'] in deja:
            trouve[l['ref']] = deja[l['ref']]
            continue
        time.sleep(1.4)   # be a good citizen of someone else's API
        print('%-34s %s' % (l['mfr'] + ' ' + l['model'], l['ref']))
        p = cherche(l['mfr'], l['model'])
        if not p:
            print('   no reusable photo of this exact type — keeping the drawing')
            continue
        ext = os.path.splitext(urllib.parse.urlparse(p['url']).path)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png'):
            ext = '.jpg'
        nom = l['ref'] + ext
        try:
            req = urllib.request.Request(p['url'], headers=UA)
            octets = urllib.request.urlopen(req, timeout=60).read()
        except Exception as e:
            print('   download failed: %s' % e)
            continue
        if not ressemble_a_une_photo(octets):
            print('   looks like a logo or a flat graphic, not a photograph — skipped')
            continue
        io.open(os.path.join(PHOTOS, nom), 'wb').write(octets)
        trouve[l['ref']] = {
            'img': 'assets/photos/' + nom,
            'auteur': p['auteur'][:120],
            'licence': p['licence'],
            'source': p['source'],
        }
        print('   %-18s %s  (%d KB)' % (p['licence'], p['auteur'][:38], len(octets) // 1024))

    out = ('/* GENERATED by fetch_photos.py — do not edit by hand.\n'
           '   Photographs from Wikimedia Commons, reusable licences only.\n'
           '   Author, licence and source page are printed on the page. */\n'
           'window.JX_PHOTOS = %s;\n' % json.dumps(trouve, indent=0, sort_keys=True))
    io.open(os.path.join(ICI, 'assets', 'photos.js'), 'w', encoding='utf-8').write(out)
    print('\n%d photographs attached' % len(trouve))


if __name__ == '__main__':
    main()
