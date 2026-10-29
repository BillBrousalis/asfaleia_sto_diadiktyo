const mk = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
const NAMES = { email: 'Email', shop: 'Κατάστημα', social: 'Κοινωνικό δίκτυο', bank: 'Τράπεζα' };
const TXT = { pending: 'Δεν έχει δοκιμάσει ακόμα', blocked: 'Ο απατεώνας μπλοκαρίστηκε', partial: 'Μπλοκαρίστηκε, αλλά η ασφάλιση δεν έχει ολοκληρωθεί', compromised: 'Ο απατεώνας έχει πρόσβαση' };

async function refresh() {
  const d = await (await fetch('/api/progress')).json();
  const clock = document.getElementById('clock');
  clock.textContent = d.round ? 'Γύροι δοκιμής του απατεώνα μέχρι τώρα: ' + d.round : 'Ο απατεώνας δεν έχει δοκιμάσει ακόμα. Όταν θες να δεις πώς αντέχει η άμυνά σου, πάτα «Δοκίμασε την άμυνά μου».';
  const done = document.getElementById('done');
  done.hidden = !d.done;
  if (d.done) { done.innerHTML = ''; done.appendChild(mk('h2', '', 'Συγχαρητήρια! Ολοκλήρωσες με επιτυχία το lab.'));
    done.appendChild(mk('p', '', 'Δεν έμεινε πρόσβαση για τον απατεώνα σε κανέναν λογαριασμό. Κωδικός επιβεβαίωσης για την πλατφόρμα:')); done.appendChild(mk('code', 'flag', d.flag)); }
  const ban = document.getElementById('banner'); ban.hidden = true;
  const unfinished = d.open && Object.keys(NAMES).some(k => d.open[k].length) && !d.done;
  if (unfinished && Object.values(d.tiles).every(t => t !== 'compromised')) {
    ban.hidden = false; ban.textContent = 'Ο απατεώνας δεν κατάφερε να μπει, αλλά δεν έχεις τελειώσει ακόμα: λείπουν ακόμα μέτρα ασφαλείας (δες παρακάτω). Το lab ολοκληρώνεται όταν γίνουν όλα.';
  }
  const tiles = document.getElementById('tiles'); tiles.innerHTML = '';
  Object.keys(NAMES).forEach(k => { const t = mk('div', 'tile ' + d.tiles[k]); t.appendChild(mk('b', '', NAMES[k])); t.appendChild(mk('span', '', TXT[d.tiles[k]])); tiles.appendChild(t); });
  const box = document.getElementById('reportbox'); box.innerHTML = '';
  const left = d.open ? Object.keys(NAMES).filter(k => d.open[k].length) : [];
  box.hidden = !left.length || d.done;
  if (!box.hidden) {
    box.appendChild(mk('h2', '', 'Τι χρειάζεται ακόμα, μετά την τελευταία δοκιμή'));
    left.forEach(k => { box.appendChild(mk('h3', '', NAMES[k])); const ul = mk('ul'); d.open[k].forEach(x => ul.appendChild(mk('li', '', x + ': ' + (d.hints[x] || 'χρειάζεται ακόμα προσοχή')))); box.appendChild(ul); });
    box.appendChild(mk('p', 'small', 'Διόρθωσέ τα και πάτα ξανά «Δοκίμασε την άμυνά μου».'));
  }
  const ev = document.getElementById('events'); ev.innerHTML = '';
  if (!d.events.length) ev.appendChild(mk('p', 'small', 'Ακόμα τίποτα.'));
  d.events.forEach(e => { const b = mk('div', 'ev' + (e.ok ? ' bad' : '')); const h = mk('h3'); h.appendChild(mk('span', 't', 'Γύρος ' + e.round)); h.append(e.title); b.appendChild(h);
    if (e.ok) { const ol = mk('ol'); e.steps.forEach(s => ol.appendChild(mk('li', '', s))); b.appendChild(ol); }
    else b.appendChild(mk('p', 'small', e.reason));
    if (e.cause && e.cause.length) { const c = mk('div', 'cause'); c.appendChild(mk('b', '', 'Τι το επέτρεψε')); const cl = mk('ul'); e.cause.forEach(x => cl.appendChild(mk('li', '', x))); c.appendChild(cl); b.appendChild(c); }
    ev.appendChild(b); });
}
refresh(); setInterval(refresh, 2000);

document.getElementById('reset').addEventListener('click', async () => { if (confirm('Να ξεκινήσει η άσκηση από την αρχή;')) { await fetch('/api/reset', { method: 'POST' }); location.reload(); } });
document.getElementById('attack').addEventListener('click', async () => { await fetch('/api/attack', { method: 'POST' }); refresh(); });
