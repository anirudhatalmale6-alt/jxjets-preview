# -*- coding: utf-8 -*-
"""jxjets preview — automatic checks.

Run against the PUBLISHED page, not a local copy:

    python3 src/checks.py
    python3 src/checks.py http://127.0.0.1:8000/     # or any other base

Exit code is non-zero if anything fails, so it drops straight into CI.
The suite prints its own total; that total is the figure quoted for this
project, and anyone can recount it by running this file.

One thing this suite deliberately does NOT assert: "no third-party requests".
The Motion section embeds four animations from hakimadjaoudi.com on purpose,
so that claim would be false here. It checks those frames are present and
framable instead.
"""

import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1
        else 'https://anirudhatalmale6-alt.github.io/jxjets-preview/')
if not BASE.endswith('/'):
    BASE += '/'

ok = [0]
ko = [0]


def t(nom, cond, detail=''):
    if cond:
        ok[0] += 1
        print('  ok    %s' % nom)
    else:
        ko[0] += 1
        print('  ECHEC %s   %s' % (nom, detail))


def head(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as r:
            return r.status
    except Exception as e:
        return getattr(e, 'code', 0)


def main():
    print('jxjets preview')
    print('  %s' % BASE)
    errs = []
    failed = []

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1280, 'height': 900})
        def console(m):
            # The Motion section embeds hakimadjaoudi.com on purpose. Errors
            # raised inside those frames are their pages' business, not this
            # page's — record only what our own origin logs.
            src = (m.location or {}).get('url', '') or ''
            if m.type == 'error' and (src.startswith(BASE) or src == ''):
                errs.append('%s  <- %s' % (m.text, src or 'no source'))
        pg.on('console', console)
        pg.on('response', lambda r: failed.append('%s %s' % (r.status, r.url))
              if r.status >= 400 and 'hakimadjaoudi' not in r.url else None)

        resp = pg.goto(BASE, wait_until='domcontentloaded')
        pg.wait_for_timeout(1500)

        # ---- the page itself ----
        t('the page answers 200', resp is not None and resp.status == 200)
        t('the title names the project', 'jxjets' in pg.title().lower(), pg.title())
        t('the html declares a language',
          bool(pg.evaluate("document.documentElement.getAttribute('lang')")))
        t('there is a viewport meta', pg.evaluate("!!document.querySelector('meta[name=viewport]')"))
        desc = pg.evaluate("(document.querySelector('meta[name=description]')||{}).content||''")
        t('the description meta is filled in', len(desc.strip()) > 30)
        t('exactly one h1', pg.evaluate("document.querySelectorAll('h1').length") == 1)
        t('there is a main landmark', pg.evaluate("!!document.querySelector('main')"))
        t('the stylesheet is published', head(BASE + 'assets/style.css') == 200)
        t('the script is published', head(BASE + 'assets/app.js') == 200)
        t('the inventory data is published', head(BASE + 'assets/data.js') == 200)

        # ---- the honesty banner: this page must never look like real stock ----
        avis = pg.evaluate("(document.querySelector('.avis')||{}).textContent||''")
        t('the demonstration banner is present', 'Demonstration' in avis)
        t('the banner says no real listing is reproduced',
          'No real listing' in avis or 'no real listing' in avis.lower())
        t('the footer repeats that it is not a commercial offer',
          'not a commercial offer' in (pg.evaluate("document.querySelector('footer').textContent") or '').lower())
        t('the counter of copied listings reads zero', pg.evaluate(
            "Array.from(document.querySelectorAll('.ch')).some(c=>"
            "/Real listings copied/i.test(c.textContent) && /(^|\\D)0(\\D|$)/.test(c.textContent))"))

        # ---- inventory renders ----
        n = pg.evaluate("document.querySelectorAll('.card').length")
        t('the grid renders every aircraft', n >= 60, 'count=%s' % n)
        t('the data and the grid agree', n == pg.evaluate("window.JX.length"))
        t('no listing carries a seller name or phone field', pg.evaluate(
            "window.JX.every(l=>!('company' in l) && !('phone' in l) && !('description' in l))"))
        t('no image is loaded from outside this site', pg.evaluate(
            "Array.from(document.images).every(i=>i.src.startsWith(location.origin))"))
        t('the plates are drawn in the page as SVG',
          pg.evaluate("document.querySelectorAll('.plate svg').length") >= 60)

        # ---- red house colour, and the image slot ----
        # The client asked for red. Assert it, so a future edit cannot quietly
        # drift the palette back without a failing check.
        t('the house colour is red, not gold', pg.evaluate(
            "(()=>{const c=getComputedStyle(document.querySelector('.prix')).color;"
            "const m=c.match(/\\d+/g).map(Number);"
            "return m[0]>150 && m[0] > m[1]+60 && m[0] > m[2]+60;})()"),)
        t('the demonstration banner follows the red palette', pg.evaluate(
            "(()=>{const c=getComputedStyle(document.querySelector('.avis b')).color;"
            "const m=c.match(/\\d+/g).map(Number); return m[0]>m[1]+50;})()"))
        t('every record carries an image slot, so real photos need no code change',
          pg.evaluate("window.JX.every(l=>'img' in l)"))
        t('no aircraft photograph is reproduced in this preview',
          pg.evaluate("window.JX.every(l=>!l.img)"))
        t('no broken image is left on the page', pg.evaluate(
            "Array.from(document.images).every(i=>i.complete && i.naturalWidth>0)"))
        t('every card is a real button, not a clickable div', pg.evaluate(
            "Array.from(document.querySelectorAll('.card')).every(c=>c.tagName==='BUTTON')"))

        # ---- masonry ----
        t('the grid is laid out in columns',
          int(pg.evaluate("getComputedStyle(document.querySelector('.mason')).columnCount") or 0) >= 2)
        t('cards are not allowed to split across a column', pg.evaluate(
            "getComputedStyle(document.querySelector('.card')).breakInside==='avoid'"))
        hs = pg.evaluate("Array.from(document.querySelectorAll('.card')).slice(0,24)"
                         ".map(c=>Math.round(c.getBoundingClientRect().height))")
        t('cards have varied heights, so the masonry actually staggers',
          len(set(hs)) >= 3, 'distinct heights=%s' % len(set(hs)))

        # ---- silhouettes match the aircraft family ----
        t('helicopters are drawn as helicopters, not aeroplanes', pg.evaluate(
            "(()=>{const h=window.JX.filter(l=>l.shape==='heli');"
            "return h.length>0 && h.every(l=>/Helicopter/.test(l.cat));})()"))
        t('every listing has a silhouette family',
          pg.evaluate("window.JX.every(l=>['plane','heli','drone'].includes(l.shape))"))

        # ---- filters really filter ----
        total = pg.evaluate("document.querySelectorAll('.card').length")
        pg.select_option('#fcat', 'Jet Aircraft')
        pg.wait_for_timeout(400)
        jets = pg.evaluate("document.querySelectorAll('.card').length")
        t('the category filter reduces the grid', 0 < jets < total, '%s of %s' % (jets, total))
        t('every card left is in that category', pg.evaluate(
            "Array.from(document.querySelectorAll('.mason .ctype')).every(e=>e.textContent==='Jet Aircraft')"))
        t('the counter follows the filter',
          str(jets) in pg.evaluate("document.querySelector('#compte').textContent"))
        pg.select_option('#fcat', '')
        pg.wait_for_timeout(350)
        t('clearing the filter restores every card',
          pg.evaluate("document.querySelectorAll('.card').length") == total)

        pg.fill('#fq', 'zzzznotanaircraft')
        pg.wait_for_timeout(400)
        t('a search with no match empties the grid',
          pg.evaluate("document.querySelectorAll('.card').length") == 0)
        t('and says so instead of showing nothing at all',
          pg.evaluate("!document.querySelector('#vide').hidden"))
        pg.fill('#fq', '')
        pg.wait_for_timeout(350)

        pg.evaluate("(()=>{const r=document.querySelector('#fprix');"
                    "r.value=r.min;r.dispatchEvent(new Event('input'));})()")
        pg.wait_for_timeout(400)
        cheap = pg.evaluate("document.querySelectorAll('.card').length")
        t('the price ceiling removes the expensive aircraft', cheap < total, '%s' % cheap)
        pg.evaluate("(()=>{const r=document.querySelector('#fprix');"
                    "r.value=r.max;r.dispatchEvent(new Event('input'));})()")
        pg.wait_for_timeout(400)
        t('raising the ceiling brings them back',
          pg.evaluate("document.querySelectorAll('.card').length") == total)

        pg.select_option('#ftri', 'price-asc')
        pg.wait_for_timeout(400)
        prix = pg.evaluate("Array.from(document.querySelectorAll('.mason .prix'))"
                           ".map(e=>Number(e.textContent.replace(/[^0-9]/g,'')))")
        t('sorting by price ascending really sorts', prix == sorted(prix))
        pg.select_option('#ftri', 'price-desc')
        pg.wait_for_timeout(350)

        # ---- detail sheet ----
        pg.click('.card')
        pg.wait_for_timeout(600)
        t('clicking a card opens the detail sheet', pg.evaluate("document.querySelector('#detail').open"))
        t('the sheet is filled in, not blank',
          len((pg.evaluate("document.querySelector('#dtitre').textContent") or '').strip()) > 6)
        t('the sheet shows a price',
          '$' in (pg.evaluate("document.querySelector('#dprix').textContent") or ''))
        pg.click('#dfermer')
        pg.wait_for_timeout(400)
        t('the sheet closes again', not pg.evaluate("document.querySelector('#detail').open"))

        # ---- motion section ----
        frames = pg.evaluate("Array.from(document.querySelectorAll('.anim iframe')).map(f=>f.src)")
        t('the four animations are embedded', len(frames) == 4, str(len(frames)))
        t('they point at the live originals',
          all('hakimadjaoudi.com/project/' in f for f in frames))
        for f in frames:
            t('animation still answers: %s' % f.rstrip('/').rsplit('/', 1)[-1], head(f) == 200)

        # ---- feedback section ----
        t('the review cards are marked as templates',
          pg.evaluate("document.querySelectorAll('.gabtag').length") >= 3)
        t('no review is presented as a real person', pg.evaluate(
            "Array.from(document.querySelectorAll('.fb')).every(c=>c.classList.contains('gab'))"))
        t('the feedback form is present', pg.evaluate("!!document.querySelector('#fbform')"))
        t('the rating control has five stars',
          pg.evaluate("document.querySelectorAll('.stars button').length") == 5)
        pg.evaluate("document.querySelectorAll('.stars button')[3].click()")
        pg.wait_for_timeout(250)
        t('choosing a rating lights the stars up to it',
          pg.evaluate("document.querySelectorAll('.stars button[aria-pressed=true]').length") == 4)
        pg.fill('#fbnom', 'Check Suite')
        pg.evaluate("document.querySelector('#fbform').requestSubmit()")
        pg.wait_for_timeout(450)
        t('submitting gives the visitor an answer',
          len((pg.evaluate("document.querySelector('#fbok').textContent") or '').strip()) > 10)
        t('and says nothing left the browser',
          'nothing was sent' in (pg.evaluate("document.querySelector('#fbok').textContent") or '').lower())

        # ---- accessibility and layout ----
        t('every button has an accessible name', pg.evaluate(
            "Array.from(document.querySelectorAll('button')).every(b=>"
            "((b.textContent||'').trim()||b.getAttribute('aria-label')||'').length>0)"))
        t('every form field has a label', pg.evaluate(
            "Array.from(document.querySelectorAll('input,select,textarea'))"
            ".filter(e=>e.type!=='range'&&e.type!=='submit')"
            ".every(e=>!!document.querySelector('label[for=\"'+e.id+'\"]'))"))
        t('no positive tabindex anywhere', pg.evaluate(
            "!document.querySelector('[tabindex]:not([tabindex=\"0\"]):not([tabindex=\"-1\"])')"))
        t('every iframe carries a title',
          pg.evaluate("Array.from(document.querySelectorAll('iframe')).every(f=>!!f.title)"))

        for w in (390, 768, 1280):
            pg.set_viewport_size({'width': w, 'height': 900})
            pg.wait_for_timeout(350)
            sw = pg.evaluate('document.documentElement.scrollWidth')
            t('no horizontal overflow at %spx' % w, sw <= w + 1, 'scrollWidth=%s' % sw)

        pg.set_viewport_size({'width': 390, 'height': 780})
        pg.wait_for_timeout(400)
        t('the grid collapses to one column on a phone',
          pg.evaluate("getComputedStyle(document.querySelector('.mason')).columnCount") in ('1', 'auto'))

        t('the console reported no error', not errs, '; '.join(errs[:3]))
        t('no request from this site failed', not failed, '; '.join(failed[:3]))

        pg.close()
        b.close()

    total_checks = ok[0] + ko[0]
    print('')
    print('  %s checks, %s passed, %s failed' % (total_checks, ok[0], ko[0]))
    sys.exit(1 if ko[0] else 0)


if __name__ == '__main__':
    main()
