/* jxjets preview — filtering, masonry rendering, detail dialog, feedback form.
   Vanilla. No library, no build step, nothing fetched from a third party. */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var all = window.JX || [];

  var f = {
    q: '', cat: '', mfr: '', sort: 'price-desc',
    maxPrice: Infinity, minYear: 0
  };

  var nf = new Intl.NumberFormat('en-US');
  function usd(n) { return '$' + nf.format(n); }

  /* Three silhouette families. A Robinson R44 drawn as an airliner is the
     sort of detail an aircraft buyer spots in half a second, so helicopters
     and drones get their own outline rather than a shared one. */
  function silhouette(kind) {
    if (kind === 'heli') {
      return '' +
        /* cabin */
        '<path d="M108 120 q-14 -10 -6 -24 q10 -18 34 -20 l30 -2 q22 0 34 16 l14 20 q4 10 -8 10 Z"/>' +
        /* tail boom + fin */
        '<path d="M206 108 L268 102 M262 102 l8 -18 M262 102 l10 10"/>' +
        /* main rotor */
        '<path d="M150 74 l0 -12 M70 60 L244 60"/>' +
        /* skids */
        '<path d="M104 140 L214 140 M122 122 l-6 18 M196 122 l6 18"/>';
    }
    if (kind === 'drone') {
      return '' +
        '<path d="M140 100 h40 v20 h-40 Z"/>' +
        '<path d="M140 100 L104 68 M180 100 L216 68 M140 120 L104 152 M180 120 L216 152"/>' +
        '<circle cx="104" cy="68" r="16"/><circle cx="216" cy="68" r="16"/>' +
        '<circle cx="104" cy="152" r="16"/><circle cx="216" cy="152" r="16"/>';
    }
    return '' +
      /* fuselage */
      '<path d="M66 112 L214 112 q26 0 34 -9 q-8 -9 -34 -9 L66 94 q-12 9 0 18 Z"/>' +
      /* wing */
      '<path d="M132 103 L104 64 L124 64 L162 100"/>' +
      '<path d="M132 109 L104 150 L124 150 L162 112"/>' +
      /* tail */
      '<path d="M206 96 L196 70 L206 70 L222 94"/>' +
      '<path d="M78 103 l14 0"/>';
  }

  /* The card image is drawn, not downloaded. Each aircraft gets a stable hue
     from its data, so the grid is varied without a single external file —
     and without borrowing anybody's photographs. */
  /* A real photograph wins whenever there is one. The drawn plate is the
     fallback, not the goal — the day the inventory carries images it needs no
     code change, only an `img` on the record. */
  function plate(l, big) {
    if (l.img) {
      return '<img src="' + esc(l.img) + '" alt="' +
        esc(l.year + ' ' + l.mfr + ' ' + l.model) + '" loading="lazy" ' +
        'style="width:100%;height:100%;object-fit:cover">';
    }
    var h = l.hue, h2 = (h + 26) % 360;
    var id = 'g' + l.ref.replace(/\W/g, '') + (big ? 'b' : '');
    return '' +
      '<svg viewBox="0 0 320 200" role="img" aria-label="' +
        esc(l.year + ' ' + l.mfr + ' ' + l.model) + ', illustration">' +
      '<defs>' +
        '<linearGradient id="' + id + '" x1="0" y1="0" x2="0.4" y2="1">' +
          '<stop offset="0" stop-color="hsl(' + h + ',46%,30%)"/>' +
          '<stop offset=".55" stop-color="hsl(' + h + ',42%,18%)"/>' +
          '<stop offset="1" stop-color="hsl(' + h2 + ',34%,10%)"/>' +
        '</linearGradient>' +
        '<linearGradient id="' + id + 'h" x1="0" y1="0" x2="0" y2="1">' +
          '<stop offset="0" stop-color="hsl(' + h + ',60%,60%)" stop-opacity=".22"/>' +
          '<stop offset="1" stop-color="hsl(' + h + ',60%,60%)" stop-opacity="0"/>' +
        '</linearGradient>' +
      '</defs>' +
      '<rect width="320" height="200" fill="url(#' + id + ')"/>' +
      /* low sun */
      '<circle cx="256" cy="52" r="30" fill="hsl(' + h + ',72%,64%)" opacity=".16"/>' +
      '<circle cx="256" cy="52" r="13" fill="hsl(' + h + ',80%,72%)" opacity=".22"/>' +
      /* horizon glow + ground line */
      '<rect x="0" y="120" width="320" height="80" fill="url(#' + id + 'h)"/>' +
      '<path d="M0 152 L320 152" stroke="hsl(' + h + ',40%,88%)" stroke-opacity=".16" stroke-width="1.1"/>' +
      '<path d="M0 168 L320 168" stroke="hsl(' + h + ',40%,88%)" stroke-opacity=".08" stroke-width="1"/>' +
      /* cloud bands, thin enough not to fight the silhouette */
      '<g stroke="hsl(' + h + ',30%,92%)" stroke-opacity=".10" stroke-width="2" stroke-linecap="round">' +
        '<path d="M28 44 h44"/><path d="M40 58 h26"/><path d="M232 96 h38"/>' +
      '</g>' +
      '<g transform="translate(160,108) rotate(' + l.tilt + ') translate(-160,-108)" ' +
      'fill="none" stroke="hsl(' + h + ',52%,88%)" stroke-opacity=".70" stroke-width="2.4" ' +
      'stroke-linecap="round" stroke-linejoin="round">' +
      silhouette(l.shape) +
      '</g>' +
      '</svg>';
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function etatClass(s) {
    if (s === 'Just listed') return 'etat neuf';
    if (s === 'Under offer') return 'etat offre';
    return 'etat';
  }

  function filtre() {
    var q = f.q.trim().toLowerCase();
    return all.filter(function (l) {
      if (f.cat && l.cat !== f.cat) return false;
      if (f.mfr && l.mfr !== f.mfr) return false;
      if (l.price > f.maxPrice) return false;
      if (l.year < f.minYear) return false;
      if (q) {
        var hay = (l.mfr + ' ' + l.model + ' ' + l.cat + ' ' + l.city + ' ' +
                   l.country + ' ' + l.ref + ' ' + l.year).toLowerCase();
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    }).sort(function (a, b) {
      switch (f.sort) {
        case 'price-asc': return a.price - b.price;
        case 'year-desc': return b.year - a.year || a.price - b.price;
        case 'hours-asc': return a.hours - b.hours;
        default: return b.price - a.price;
      }
    });
  }

  function rendu() {
    var res = filtre();
    var g = $('#grille');
    $('#compte').innerHTML = '<b>' + res.length + '</b> aircraft' +
      (res.length === all.length ? '' : ' of ' + all.length);

    if (!res.length) {
      g.innerHTML = '';
      $('#vide').hidden = false;
      return;
    }
    $('#vide').hidden = true;

    g.innerHTML = res.map(function (l) {
      return '<button class="card" type="button" data-ref="' + esc(l.ref) + '">' +
        '<span class="plate" style="aspect-ratio:' + (l.ar || '16/10') + '">' + plate(l) +
          '<span class="' + etatClass(l.status) + '">' + esc(l.status) + '</span>' +
        '</span>' +
        '<span class="cbody">' +
          '<span class="ctype">' + esc(l.cat) + '</span>' +
          '<h3>' + esc(l.year + ' ' + l.mfr + ' ' + l.model) + '</h3>' +
          '<span class="prix">' + usd(l.price) + '</span>' +
          '<span class="meta">' +
            '<span>' + nf.format(l.hours) + ' h</span>' +
            '<span class="dot"></span>' +
            '<span>' + esc(l.city) + ', ' + esc(l.country) + '</span>' +
            '<span class="dot"></span>' +
            '<span>' + esc(l.ref) + '</span>' +
          '</span>' +
        '</span>' +
      '</button>';
    }).join('');
  }

  function ouvrir(ref) {
    var l = all.filter(function (x) { return x.ref === ref; })[0];
    if (!l) return;
    $('#dplate').innerHTML = plate(l, true);
    $('#dtitre').textContent = l.year + ' ' + l.mfr + ' ' + l.model;
    $('#dsous').textContent = l.cat + ' · ' + l.city + ', ' + l.country;
    $('#dprix').textContent = usd(l.price);
    $('#dheures').textContent = nf.format(l.hours) + ' h';
    $('#dannee').textContent = l.year;
    $('#dref').textContent = l.ref;
    $('#detat').textContent = l.status;
    var d = $('#detail');
    if (d.showModal) { d.showModal(); } else { d.setAttribute('open', ''); }
  }

  document.addEventListener('click', function (e) {
    var c = e.target.closest ? e.target.closest('.card') : null;
    if (c) { ouvrir(c.getAttribute('data-ref')); }
  });

  /* ---- controls ---- */
  function bind() {
    var cats = window.JX_CATS || [], mfrs = window.JX_MFRS || [];
    $('#fcat').innerHTML = '<option value="">All categories</option>' +
      cats.map(function (c) { return '<option>' + esc(c) + '</option>'; }).join('');
    $('#fmfr').innerHTML = '<option value="">All manufacturers</option>' +
      mfrs.map(function (m) { return '<option>' + esc(m) + '</option>'; }).join('');

    var max = Math.max.apply(null, all.map(function (l) { return l.price; }));
    var pr = $('#fprix');
    pr.max = max; pr.value = max; f.maxPrice = max;
    $('#oprix').textContent = usd(max);

    $('#fq').addEventListener('input', function () { f.q = this.value; rendu(); });
    $('#fcat').addEventListener('change', function () { f.cat = this.value; rendu(); });
    $('#fmfr').addEventListener('change', function () { f.mfr = this.value; rendu(); });
    $('#ftri').addEventListener('change', function () { f.sort = this.value; rendu(); });
    pr.addEventListener('input', function () {
      f.maxPrice = +this.value;
      $('#oprix').textContent = usd(+this.value);
      rendu();
    });
    $('#fannee').addEventListener('input', function () {
      f.minYear = +this.value;
      $('#oannee').textContent = this.value === '0' ? 'any' : this.value + '+';
      rendu();
    });

    Array.prototype.forEach.call(document.querySelectorAll('.puce'), function (b) {
      b.addEventListener('click', function () {
        var on = b.getAttribute('aria-pressed') === 'true';
        Array.prototype.forEach.call(document.querySelectorAll('.puce'), function (o) {
          o.setAttribute('aria-pressed', 'false');
        });
        b.setAttribute('aria-pressed', on ? 'false' : 'true');
        f.cat = on ? '' : (b.getAttribute('data-cat') || '');
        $('#fcat').value = f.cat;
        rendu();
      });
    });

    $('#dfermer').addEventListener('click', function () {
      var d = $('#detail');
      if (d.close) { d.close(); } else { d.removeAttribute('open'); }
    });

    /* feedback form — local only, nothing is sent anywhere */
    var note = 0;
    Array.prototype.forEach.call(document.querySelectorAll('.stars button'), function (b, i) {
      b.addEventListener('click', function () {
        note = i + 1;
        Array.prototype.forEach.call(document.querySelectorAll('.stars button'), function (o, j) {
          o.setAttribute('aria-pressed', j < note ? 'true' : 'false');
        });
      });
    });
    $('#fbform').addEventListener('submit', function (e) {
      e.preventDefault();
      $('#fbok').textContent =
        'Thank you. In the live site this would be queued for moderation' +
        (note ? ' (' + note + '/5)' : '') + '. Nothing was sent from this preview.';
    });
  }

  bind();
  rendu();
})();
