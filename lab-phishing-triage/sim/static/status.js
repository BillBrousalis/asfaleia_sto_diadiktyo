const rowsEl = document.getElementById('rows');
const modal = document.getElementById('modal');
const modalContent = document.getElementById('modal-content');
const mk = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };

async function refresh() {
  const d = await (await fetch('/api/status')).json();
  rowsEl.innerHTML = '';
  d.rows.forEach((r, i) => {
    const row = mk('div', 'row prog');
    const meta = mk('div', 'meta');
    meta.appendChild(mk('span', 'num', String(i + 1)));
    const t = mk('div'); t.appendChild(mk('strong', '', r.subject)); t.appendChild(mk('br'));
    t.appendChild(mk('span', 'small', 'Από: ' + r.from_name + ' · ' + r.date));
    meta.appendChild(t); row.appendChild(meta);
    const chips = mk('div', 'chips');
    if (r.reported) chips.appendChild(mk('span', 'chip rep', 'Το ανέφερες'));
    if (r.submitted) chips.appendChild(mk('span', 'chip bad', 'Έγραψες στοιχεία'));
    else if (r.opened) chips.appendChild(mk('span', 'chip warn', 'Άνοιξες τον σύνδεσμο'));
    if (!r.reported && !r.opened) chips.appendChild(mk('span', 'chip', 'Δεν έχεις κάνει κάτι'));
    row.appendChild(chips);
    rowsEl.appendChild(row);
  });
  const done = document.getElementById('done');
  done.hidden = !d.complete;
  if (d.complete) {
    done.innerHTML = '';
    done.appendChild(mk('h2', '', 'Συγχαρητήρια! Ολοκλήρωσες με επιτυχία το lab.'));
    done.appendChild(mk('p', '', 'Ανέφερες σωστά και τις 8 ύποπτες απάτες, χωρίς να αναφέρεις γνήσιο μήνυμα. Κωδικός επιβεβαίωσης για την πλατφόρμα:'));
    done.appendChild(mk('code', 'flag', d.flag));
  }
  const box = document.getElementById('restart');
  box.hidden = !d.restart;
  if (d.restart && !box.dataset.id) {
    const r = d.restart; box.dataset.id = r.id; box.innerHTML = '';
    box.appendChild(mk('h2', '', 'Ανέφερες ένα γνήσιο μήνυμα'));
    box.appendChild(mk('p', 'lead', '«' + r.subject + '» από ' + r.from_name + ' ήταν γνήσιο, όχι απάτη. Γιατί:'));
    const ul = mk('ul'); r.why.forEach(t => ul.appendChild(mk('li', '', t))); box.appendChild(ul);
    box.appendChild(mk('p', '', 'Αν το είχες αναφέρει στην πραγματικότητα, θα είχες χάσει χρόνο ή κάτι σημαντικό. Δες τι θα συνέβαινε:'));
    box.appendChild(outcomeButton('Δες τι θα κόστιζε η υπερβολική καχυποψία', r.outcome, 'btn2'));
    box.appendChild(mk('p', '', 'Η άσκηση ξεκινά από την αρχή, ώστε να εξασκηθείς να ελέγχεις με στοιχεία πριν αναφέρεις.'));
    const go = mk('button', 'big', 'Ξεκίνα από την αρχή'); go.type = 'button';
    go.addEventListener('click', async () => { await fetch('/api/reset', { method: 'POST' }); box.dataset.id = ''; location.reload(); });
    box.appendChild(go);
  }
  if (!d.restart) box.dataset.id = '';
  document.getElementById('count').textContent = d.reported + ' αναφορές μέχρι τώρα';
}
refresh(); setInterval(refresh, 3000);

function outcomeButton(label, o, cls) {
  const b = mk('button', cls || 'link', label); b.type = 'button';
  b.addEventListener('click', () => { modal.hidden = false; renderOutcome(modalContent, o, { user: 'Ελένη' }); });
  return b;
}

document.getElementById('close').addEventListener('click', () => { modal.hidden = true; });
modal.addEventListener('click', e => { if (e.target === modal) modal.hidden = true; });
