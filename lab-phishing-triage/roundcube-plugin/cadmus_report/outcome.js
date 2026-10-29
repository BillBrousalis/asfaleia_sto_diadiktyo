// Step-by-step consequence timeline. Everything is rendered in the browser.
function renderOutcome(container, o, typed) {
  typed = typed || {};
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const fill = s => s.replace('{user}', typed.user || '…');
  container.innerHTML = '';
  const wrap = el('div', 'result ' + (o.truth === 'scam' ? 'bad' : 'warn'));
  wrap.appendChild(el('h2', '', o.title));
  const list = el('ol', 'timeline');
  wrap.appendChild(list);
  const next = el('button', 'big', 'Τι έγινε μετά ▶');
  wrap.appendChild(next);
  const summary = el('div', 'summary'); summary.hidden = true; wrap.appendChild(summary);
  container.appendChild(wrap);
  let i = 0;
  function reveal() {
    const s = o.steps[i++];
    const li = el('li', 'step ' + s.kind);
    li.appendChild(el('span', 'time', s.t));
    li.appendChild(el('span', 'who', s.kind === 'you' ? 'Εσύ' : s.kind === 'atk' ? 'Ο απατεώνας' : 'Συνέπεια'));
    li.appendChild(el('p', '', fill(s.text)));
    list.appendChild(li);
    li.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    if (i >= o.steps.length) { next.hidden = true; showSummary(); }
  }
  function showSummary() {
    summary.hidden = false;
    summary.appendChild(el('p', 'loss-label', o.truth === 'scam' ? 'Τι χάνεις' : 'Τι κόστισε'));
    summary.appendChild(el('p', 'loss-amount', o.loss));
    summary.appendChild(el('h3', '', o.truth === 'scam' ? 'Τι έδειχνε ότι ήταν παγίδα' : 'Σημείωση'));
    const m = el('ul'); o.missed.forEach(t => m.appendChild(el('li', '', t))); summary.appendChild(m);
    summary.appendChild(el('h3', '', o.truth === 'scam' ? 'Αν συνέβαινε στ’ αλήθεια, κάνε αμέσως αυτά' : 'Πώς θα το έλεγχες'));
    const d = el('ul'); o.do_now.forEach(t => d.appendChild(el('li', '', t))); summary.appendChild(d);
  }
  next.addEventListener('click', reveal);
  reveal();
}
