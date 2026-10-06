# Browser verification

A report with one JavaScript error renders as a blank page, and a 700 KB file
looks perfectly healthy from the shell. Always drive a real browser before
delivering.

## Serve it

Most browsers refuse `file://` navigation from automation
(`Navigating to local URL is not allowed`), so serve over HTTP:

```bash
python3 -m http.server 8791 --bind 0.0.0.0 &
```

Bind `0.0.0.0` and navigate to the machine's LAN IP if `127.0.0.1` refuses to
connect from the browser — loopback ports are sometimes blocked even when the
browser and the shell share a network namespace. Kill the server afterwards, and
never leave it running as a background job you forget about.

## The checklist

Run these after every render. Each is a one-liner you can paste into an
`evaluate`-style command against the page.

**1. Every section the renderer promised actually mounted.**

```js
JSON.stringify({
  pages: document.querySelectorAll('.page').length,
  nav: document.querySelectorAll('#sidebar a').length,
  sections: [...document.querySelectorAll('#sidebar a')].map(a => a.dataset.page)
})
```

Compare against the renderer's `sections present:` line. A mismatch means a
renderer threw — check the console next.

**2. No JavaScript exceptions.** Look for `error exception` entries in the console.
`favicon.ico` 404s and `chrome-extension://invalid` resource errors are noise, not
your bug. Extension noise accumulates across reloads in the same tab, so index
numbers from earlier loads will still be listed — only entries from the current
load matter.

**3. No duplicate element ids.** Critical: the API page mounts either the prefix
tree or the flat list, never both, because both use the same endpoint ids. If both
exist, `getElementById` returns the wrong node and deep links break silently.

```js
(() => { const seen = new Set(), dup = [];
  document.querySelectorAll('[id]').forEach(e => { if (seen.has(e.id)) dup.push(e.id); seen.add(e.id); });
  return JSON.stringify([...new Set(dup)]); })()
```

**4. Navigation, search, Escape.**

```js
(async () => {
  const o = {};
  document.querySelector('#sidebar a[data-page="api"]').click();
  await new Promise(r => setTimeout(r, 300));           // hashchange is async
  o.activePage = document.querySelector('.page.active').id;
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true }));
  o.searchFocused = document.activeElement.id;          // expect "gsearch"
  const g = document.getElementById('gsearch');
  g.value = 'auth'; g.dispatchEvent(new Event('input'));
  o.searchResults = document.querySelectorAll('#results .res').length;
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
  o.closedOnEsc = !document.getElementById('results').classList.contains('open');
  return JSON.stringify(o);
})()
```

**5. API filters and the tree↔list toggle.** Each filter must change the visible
leaf count, and a filter must auto-expand so matches are actually on screen.

```js
(async () => {
  const visible = () => [...document.querySelectorAll('#eptree .ep')].filter(e => e.offsetParent !== null).length;
  const o = { total: document.querySelectorAll('#eptree .ep').length };
  const mod = document.getElementById('epmod');
  mod.value = mod.options[1].value; mod.dispatchEvent(new Event('input'));
  o.afterModuleFilter = visible();
  o.counter = document.getElementById('apicount').textContent;   // visible must be > 0
  mod.value = ''; mod.dispatchEvent(new Event('input'));
  [...document.querySelectorAll('.vtabs button')].find(b => b.dataset.view === 'list').click();
  o.listRows = document.querySelectorAll('#eplist .ep').length;
  o.treeGone = document.querySelectorAll('#eptree').length === 0;
  return JSON.stringify(o);
})()
```

**6. File tree and the detail panel.** A deep link must reveal ancestors, not just
scroll:

```js
(async () => {
  location.hash = '#files';
  await new Promise(r => setTimeout(r, 200));
  const f = document.querySelector('.ftn.fname');       // pick an annotated path in practice
  f.click();
  return JSON.stringify({ detailRendered: document.querySelector('#filedetail').textContent.length > 40 });
})()
```

**7. Deep links across every id scheme.** Pick one of each:

```js
location.hash = '#api::<endpoint-id>';       // must expand ancestor prefix nodes
location.hash = '#model-<table>';            // must switch page and open the <details>
location.hash = '#files::file-<slug>';       // must expand the tree to that file
```

Verify after each: `document.querySelector('.page.active').id` is the expected
page, the element exists, and `element.offsetParent !== null` (i.e. visible, not
inside a collapsed container).

**8. Theme.** Toggle must set `data-theme` on `<html>` and persist:

```js
(() => { const before = document.documentElement.dataset.theme;
  document.getElementById('themebtn').click();
  return JSON.stringify({ before, after: document.documentElement.dataset.theme,
    stored: localStorage.getItem('fctf-theme'),
    bg: getComputedStyle(document.body).backgroundColor }); })()
```

**9. Content is not full of placeholders.** Guards against template bugs that
render `undefined`:

```js
['undefined', 'NaN', '[object Object]'].filter(t => document.body.innerText.includes(t))
```

## If screenshots hang

CDP screenshot capture can time out on some host/connection setups. Do not block
on it — DOM assertions above prove the page works. If you do want a visual, try
again after collapsing large sections (the file tree and API tree are the heaviest
DOM) or reducing the viewport, and give up quickly if it stays unresponsive.

## When something fails

Fix the template, re-render, reload with a cache-busting query
(`?v=2`), and re-run the checklist. Do not declare success on a partially
rendering page: the reader's first impression *is* the report.
