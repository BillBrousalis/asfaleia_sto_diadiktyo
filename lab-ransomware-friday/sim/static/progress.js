const mk = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
const post = url => fetch(url, { method: 'POST' });

async function refresh() {
  const d = await (await fetch('/api/progress')).json();
  document.getElementById('status').textContent = d.phase === 'prep'
    ? 'Είναι Παρασκευή απόγευμα. Δεν έχει συμβεί ακόμα τίποτα.'
    : 'Αρχεία που ανοίγουν στον υπολογιστή: ' + d.readable + ' από ' + d.total;
  const mb = document.getElementById('mistake'); mb.innerHTML = ''; mb.hidden = !d.mistake || d.done;
  if (!mb.hidden) {
    const m = d.mistake;
    mb.appendChild(mk('h2', '', 'Έγινε ένα λάθος'));
    mb.appendChild(mk('h3', '', 'Τι έγινε: ' + m.title));
    if (m.steps && m.steps.length) { const ul = mk('ul'); m.steps.forEach(x => ul.appendChild(mk('li', '', x))); mb.appendChild(ul); }
    if (m.cause && m.cause.length) { mb.appendChild(mk('p', '', 'Γιατί συνέβη: ' + m.cause.join(' '))); }
    if (m.fix) mb.appendChild(mk('p', 'fixline', 'Τι έπρεπε να κάνεις: ' + m.fix));
    mb.appendChild(mk('p', '', 'Η σειρά των ενεργειών έχει σημασία. Ξεκίνα την άσκηση από την αρχή και δοκίμασε να το αποφύγεις.'));
    const row = mk('div', 'actions');
    const r1 = mk('button', 'big', 'Ξεκίνα από την αρχή'); r1.onclick = async () => { await post('/api/reset'); location.href = 'http://pc.protefs-office.example/'; };
    row.appendChild(r1);
    mb.appendChild(row);
  }
  const done = document.getElementById('done');
  done.hidden = !d.done;
  if (d.done) { done.innerHTML = ''; done.appendChild(mk('h2', '', 'Συγχαρητήρια! Ολοκλήρωσες με επιτυχία το lab.'));
    done.appendChild(mk('p', '', 'Ανέκτησες τα αρχεία σου χωρίς να πληρώσεις. Κωδικός επιβεβαίωσης για την πλατφόρμα:')); done.appendChild(mk('code', 'flag', d.flag)); }
  const box = document.getElementById('reportbox'); box.innerHTML = '';
  box.hidden = !d.open || !d.open.length || d.done;
  if (!box.hidden) {
    box.appendChild(mk('h2', '', 'Τι χρειάζεται ακόμα, μετά την τελευταία φορά που πάτησες «Ολοκλήρωσα»'));
    const ul = mk('ul'); d.open.forEach(x => ul.appendChild(mk('li', '', x + ': ' + (d.hints[x] || 'χρειάζεται ακόμα προσοχή')))); box.appendChild(ul);
    box.appendChild(mk('p', 'small', 'Συνέχισε και πάτα ξανά «Ολοκλήρωσα» όταν είσαι έτοιμος.'));
  }
  const ev = document.getElementById('events'); ev.innerHTML = '';
  if (!d.events.length) ev.appendChild(mk('p', 'small', 'Ακόμα τίποτα.'));
  d.events.forEach(e => { const b = mk('div', 'ev' + (e.kind === 'bad' ? ' bad' : e.kind === 'info' ? ' info' : '')); b.appendChild(mk('h3', '', e.title));
    if (e.steps.length) { const ol = mk('ul'); e.steps.forEach(s => ol.appendChild(mk('li', '', s))); b.appendChild(ol); }
    if (e.cause && e.cause.length) { const c = mk('div', 'cause'); c.appendChild(mk('b', '', 'Τι το επέτρεψε')); const cl = mk('ul'); e.cause.forEach(x => cl.appendChild(mk('li', '', x))); c.appendChild(cl); b.appendChild(c); }
    ev.appendChild(b); });
}
refresh(); setInterval(refresh, 2000);
document.getElementById('finish').addEventListener('click', async () => { await post('/api/finish'); refresh(); });
document.getElementById('reset').addEventListener('click', async () => { if (confirm('Να ξεκινήσει η άσκηση από την αρχή;')) { await post('/api/reset'); location.reload(); } });
document.getElementById('help').addEventListener('click', async () => {
  const h = await (await fetch('/api/hint')).json(); const box = document.getElementById('helpbox');
  box.hidden = false; box.innerHTML = ''; box.appendChild(mk('h3', '', 'Επόμενο βήμα: ' + h.title)); box.appendChild(mk('p', '', 'Γιατί: ' + h.why));
});
