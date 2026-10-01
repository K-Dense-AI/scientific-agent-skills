// Fictiv quote-page state extractor.
//
// Paste the body of this file into the browser's javascript tool while on
//   https://app.fictiv.com/pages/quotes/<quoteId>            (quote page)
//   https://app.fictiv.com/pages/orders/quote/<quoteId>      (checkout page)
// It returns a terse line-per-item digest of what the page shows (QUOTE, STAGE,
// TIERS, one P<n> line per part, SUMMARY, BUTTONS, CHECKOUT, DIALOG) so you can
// reason about the quote without screenshots. The full structured object
// (incl. partIds) is left on window.__fictivState. Read-only: never clicks.
//
// The app is built on Ant Design, so selectors lean on stable `ant-*` classes and
// visible text rather than hashed CSS-module names (e.g. `tableColumns--sfkbO`),
// which change between Fictiv releases.

(() => {
  const txt = (el) => (el ? el.innerText.replace(/\u00a0/g, ' ').trim() : '');
  const lines = (el) => txt(el).split('\n').map((s) => s.trim()).filter(Boolean);
  const body = document.body.innerText;
  const path = location.pathname;

  const out = {
    url: location.origin + path,
    page: /\/pages\/orders\/quote\//.test(path)
      ? 'checkout'
      : /\/part\/[^/]+\/(configuration|threads|feedback)/.test(path)
        ? 'part-modal'
        : /\/pages\/quotes\/[0-9a-f-]{36}/.test(path)
          ? 'quote'
          : 'other',
    quoteId: (path.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/) || [null])[0],
    quoteName: null,
    banner: null,
    useClassification: null,
    leadTimeTiers: [],
    usaOnly: null,
    parts: [],
    summary: {},
    buttons: {},
    openDialogs: [],
    analyzing: /Analyzing (parts|geometry)|Configuring part|Determining available lead times/.test(body),
  };

  // Quote title sits right after "Save and back".
  const m = body.match(/Save and back\n(.+)\nLast modified/);
  if (m) out.quoteName = m[1].trim();

  // Banner above the parts table tells you which stage the quote is in.
  for (const b of [
    'Required: Are these parts for prototype or commercial use?',
    'Configure parts to receive lead times',
    'Determining available lead times',
    'Select regional preference',
  ]) if (body.includes(b)) { out.banner = b; break; }

  // Prototype / Commercial: shown as two cards before selection, as a small
  // dropdown (a bare "Prototype"/"Commercial" line) in the banner afterwards.
  if (out.banner && out.banner.startsWith('Required')) out.useClassification = 'NOT SET';
  else {
    const top = body.slice(0, body.indexOf('Select files or drag') > 0 ? body.indexOf('Select files or drag') : 3000);
    const cm = top.match(/\n(Prototype|Commercial)\n/);
    out.useClassification = cm ? cm[1] : null;
  }

  // Lead-time tiers are radio inputs whose value names the tier.
  document.querySelectorAll('input[type=radio]').forEach((r) => {
    if (!/^(domestic|overseas)/.test(r.value)) return;
    const l = lines(r.closest('label') || r.parentElement);
    out.leadTimeTiers.push({
      key: r.value,
      region: r.value.startsWith('domestic') ? 'North America' : 'Overseas',
      label: l.find((s) => /production days/.test(s)) || null,
      price: l.find((s) => /^\$/.test(s)) || null,
      tag: l.find((s) => /^(Fastest|Standard|Cost-effective)$/.test(s)) || null,
      selected: r.checked,
    });
  });
  const usa = [...document.querySelectorAll('label')].find((l) => txt(l) === 'USA only');
  if (usa) { const cb = usa.querySelector('input[type=checkbox]'); out.usaOnly = cb ? cb.checked : null; }

  // Parts table rows.
  document.querySelectorAll('tr.ant-table-row').forEach((tr) => {
    const c = [...tr.children];
    if (c.length < 6) return;
    const name = lines(c[1]);
    const cfg = lines(c[2]).filter((s) => s !== 'Edit configuration' && s !== 'Configure');
    const link = c[1].querySelector('a[href*="/part/"]');
    const partId = link ? (link.getAttribute('href').match(/part\/([0-9a-f-]{36})/) || [])[1] : null;
    out.parts.push({
      file: name.find((s) => /\.[a-z0-9_]+$/i.test(s)) || name.join(' '),
      revision: name.find((s) => /^Rev /.test(s)) || null,
      dfmIssueCount: Number(name.find((s) => /^\d+$/.test(s))) || 0,
      hasFeedbackLink: name.includes('View feedback'),
      partId,
      configured: !lines(c[2]).includes('Configure'),
      process: cfg[0] || null,
      material: cfg[1] || null,
      finishAndOptions: cfg.slice(2),
      productionDetails: lines(c[3]).join(' ') || null,
      quantity: (c[4].querySelector('input') || {}).value || null,
      quantityNote: lines(c[4]).join(' ') || null,
      price: lines(c[5]),
      needsManualQuote: /Please request a quote/.test(txt(c[5])),
      selected: !!(c[0].querySelector('input[type=checkbox]') || {}).checked,
    });
  });

  // Summary card (right column). Grab label/value pairs between "Summary" and the buttons.
  const sIdx = body.indexOf('\nSummary\n');
  if (sIdx >= 0) {
    const seg = body.slice(sIdx + 9, sIdx + 1500).split('\n').map((s) => s.trim()).filter(Boolean);
    const keys = ['Part production', 'Shipping', 'Tax', 'Order total', 'Ship by', 'Est. Delivery', 'Shipping address'];
    for (let i = 0; i < seg.length; i++) {
      const k = keys.find((kk) => seg[i].startsWith(kk));
      if (k && out.summary[seg[i]] === undefined) out.summary[seg[i]] = seg[i + 1] || null;
      if (/Your dedicated account manager/.test(seg[i])) break;
    }
    const note = seg.find((s) => /Please configure|require a human to quote|Some of your parts/.test(s));
    if (note) out.summary.note = note;
  }

  // Key buttons and whether they're usable.
  for (const label of ['Request quote', 'Begin checkout', 'Place order', 'Download quote', 'Forward to purchaser',
                       'Bulk configure parts', 'Configure via drawing']) {
    const b = [...document.querySelectorAll('button')].find((x) => txt(x) === label);
    if (b) out.buttons[label] = b.disabled || b.getAttribute('aria-disabled') === 'true' ? 'disabled' : 'enabled';
  }

  // Checkout-page specifics.
  if (out.page === 'checkout') {
    const cut = body.match(/Checkout within .+? cutoff on .+?\./);
    out.checkout = {
      cutoffNotice: cut ? cut[0] : null,
      shippingOptions: /No shipping options available/.test(body) ? 'none (add an address first)' : 'available',
      payTab: (() => {
        const t = [...document.querySelectorAll('[role=tab], button, div')].find((x) =>
          /^(Pay with credit card|Pay with PO)$/.test(txt(x)) && /active|selected|checked/i.test(x.className));
        return t ? txt(t) : null;
      })(),
      savedCards: /Your saved cards\nNo Data/.test(body) ? 0 : 'see page',
      savedAddresses: /Ship to\nAdd new address\nNo Data/.test(body) ? 0 : 'see page',
    };
  }

  // Any open modal/dialog (e.g. confirmation prompts) — first 400 chars of each.
  const seen = new Set();
  document.querySelectorAll('.ant-modal-content, .ant-popover-inner, .ant-drawer-content').forEach((d) => {
    const t = txt(d);
    if (t && !seen.has(t) && d.offsetParent !== null) { seen.add(t); out.openDialogs.push(t.slice(0, 400)); }
  });

  // Browser JS tools truncate results at roughly 1 KB, so return a terse
  // line-per-item digest and stash the full object on window for slicing:
  //   window.__fictivState            -> full object (JSON.stringify it in pieces)
  //   window.__fictivStateText.slice(1000, 2000)  -> next chunk of the digest
  window.__fictivState = out;
  const L = [];
  L.push(`QUOTE ${out.quoteName || '?'} id=${out.quoteId || '?'} page=${out.page} analyzing=${out.analyzing}`);
  L.push(`STAGE ${out.banner || '-'} | use=${out.useClassification || '-'}${out.usaOnly ? ' | USA-only' : ''}`);
  if (out.leadTimeTiers.length) {
    L.push('TIERS ' + out.leadTimeTiers.map((t) =>
      `${t.selected ? '*' : ''}${t.key}:${(t.label || '').replace(/ production days?/, 'd')}:${t.price}`).join(' | '));
  }
  out.parts.forEach((p, i) => {
    L.push(`P${i + 1} ${p.file} ${p.revision || ''} | ${p.configured ? [p.process, p.material, ...p.finishAndOptions].join(' / ') : 'NOT CONFIGURED'}`
      + ` | qty ${p.quantity || '-'} | ${p.needsManualQuote ? 'MANUAL QUOTE' : p.price.join(' ')}`
      + `${p.dfmIssueCount ? ` | DFM ${p.dfmIssueCount}` : ''}${p.productionDetails ? ` | ${p.productionDetails}` : ''}`);
  });
  const s = Object.entries(out.summary).map(([k, v]) => (k === 'note' ? `NOTE: ${v.slice(0, 90)}` : `${k}=${v}`));
  if (s.length) L.push('SUMMARY ' + s.join(' | '));
  L.push('BUTTONS ' + Object.entries(out.buttons).map(([k, v]) => `${k}:${v}`).join(' | '));
  if (out.checkout) L.push('CHECKOUT ' + Object.entries(out.checkout).map(([k, v]) => `${k}=${v}`).join(' | '));
  out.openDialogs.forEach((d) => L.push('DIALOG ' + d.replace(/\n/g, ' / ').slice(0, 200)));
  window.__fictivStateText = L.join('\n');
  return window.__fictivStateText;
})();
