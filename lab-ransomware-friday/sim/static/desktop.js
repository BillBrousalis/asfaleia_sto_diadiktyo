/* Cadmus Lab C — the player's simulated computer. */
const $app = document.getElementById('app');
const mk = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
const post = (url, body) => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) }).then(r => r.json());
const get = url => fetch(url).then(r => r.json());
document.title = 'Ο υπολογιστής του Θοδωρή';

let WIN_CLOSED = false, ST = null, TAB = 'Αρχεία', LOC = 'pc', PREVIEW = null, MSG = null, NOTE_CLOSED = false, TOAST_N = 0;
const APPS = ['Αρχεία', 'Αντίγραφα ασφαλείας', 'Ενημερώσεις', 'Δίκτυο', 'Antivirus', 'Ταχυδρομείο'];

// ---- top bar
const bar = document.getElementById('bar');
async function refreshBar() {
  const b = await get('/api/bar');
  bar.hidden = false; bar.className = 'bar'; bar.innerHTML = '';
  if (b.done) { bar.classList.add('done'); bar.appendChild(mk('span', '', 'Συγχαρητήρια! Ολοκλήρωσες με επιτυχία το lab. Κωδικός επιβεβαίωσης: ' + b.flag + ' · ')); }
  const home = mk('a', '', 'Αρχική οθόνη και βήματα'); home.href = '/home'; home.target = '_blank';
  const prog = mk('a', '', 'Πρόοδος'); prog.href = '/progress'; prog.target = '_blank';
  bar.appendChild(home); bar.append(' · '); bar.appendChild(prog);
}
refreshBar(); setInterval(refreshBar, 4000);

// ---- toast and ransom note
function showToast(t) {
  const el = document.getElementById('toast'); if (!t || t.n === TOAST_N) return; TOAST_N = t.n;
  el.hidden = false; el.className = 'toast ' + t.kind; el.innerHTML = ''; el.appendChild(mk('div', '', t.title));
  const x = mk('button', 'x', '✕'); x.onclick = () => { el.hidden = true; }; el.appendChild(x);
}
function showNote() {
  const n = document.getElementById('note');
  if (!ST.ransom || NOTE_CLOSED) { n.hidden = true; return; }
  n.hidden = false; n.innerHTML = '';
  const i = mk('div', 'in'); n.appendChild(i);
  i.appendChild(mk('h2', '', 'Τα αρχεία σου κρυπτογραφήθηκαν'));
  i.appendChild(mk('p', '', 'Όλα τα έγγραφα και οι φωτογραφίες σου είναι κλειδωμένα. Μόνο εμείς έχουμε το κλειδί για να τα ανοίξεις.'));
  i.appendChild(mk('p', '', 'Αν θέλεις να τα πάρεις πίσω, πλήρωσε και στείλε μας μήνυμα στη διεύθυνση:'));
  i.appendChild(mk('code', '', ST.contact));
  i.appendChild(mk('p', '', 'Μην ειδοποιήσεις κανέναν και μην προσπαθήσεις να τα ανοίξεις μόνος σου, γιατί θα χαθούν για πάντα.'));
  const pay = mk('button', 'dng', 'Πληρωμή'); pay.onclick = async () => { await post('/api/pay'); NOTE_CLOSED = true; load(); };
  const close = mk('button', 'small-btn', 'Κλείσιμο'); close.onclick = () => { NOTE_CLOSED = true; showNote(); };
  i.append(pay, close);
}

function showWin() {
  const w = document.getElementById('win');
  if (!ST.done || WIN_CLOSED) { w.hidden = true; return; }
  w.hidden = false; w.innerHTML = '';
  const i = mk('div', 'in'); w.appendChild(i);
  i.appendChild(mk('h2', '', 'Συγχαρητήρια! Ολοκλήρωσες με επιτυχία το lab'));
  i.appendChild(mk('p', '', 'Ανέκτησες τα αρχεία σου χωρίς να πληρώσεις, ο υπολογιστής είναι καθαρός και ενημερωμένος, και ενημέρωσες όσους έπρεπε.'));
  i.appendChild(mk('p', '', 'Κωδικός επιβεβαίωσης για την πλατφόρμα:'));
  i.appendChild(mk('code', '', ST.flag));
  const c = mk('button', 'small-btn', 'Κλείσιμο'); c.onclick = () => { WIN_CLOSED = true; showWin(); }; i.appendChild(c);
}

// ---- layout
async function load() {
  ST = await get('/api/state');
  if (ST.mistake) { location.href = '/progress'; return; }   // a mistake with consequences: explain it on the progress page; the exercise has to be restarted
  if (!ST.locations.find(l => l.id === LOC)) LOC = 'pc';
  render(); showToast(ST.toast); showNote(); showWin();
}
function render() {
  $app.innerHTML = '';
  const head = mk('div', 'desk-head');
  const t = mk('div'); t.appendChild(mk('b', '', 'Ο υπολογιστής του Θοδωρή')); t.appendChild(mk('div', 'when', ST.phase === 'prep' ? 'Παρασκευή 17:30' : 'Δευτέρα 08:30')); head.appendChild(t);
  if (ST.phase === 'prep') { const end = mk('button', 'big', 'Τέλος εργασίας'); end.onclick = async () => { if (confirm('Να κλείσεις τον υπολογιστή και να φύγεις για το Σαββατοκύριακο;')) { NOTE_CLOSED = false; PREVIEW = null; MSG = null; await post('/api/gohome'); load(); } }; head.appendChild(end); }
  $app.appendChild(head);
  const dock = mk('div', 'dock');
  APPS.forEach(a => { const b = mk('button', a === TAB ? 'on' : '', a); b.onclick = () => { TAB = a; MSG = null; PREVIEW = null; render(); }; dock.appendChild(b); });
  $app.appendChild(dock);
  const win = mk('div', 'win'); $app.appendChild(win); win.appendChild(mk('h2', '', TAB));
  ({ 'Αρχεία': files, 'Αντίγραφα ασφαλείας': backups, 'Ενημερώσεις': updates, 'Δίκτυο': network, 'Antivirus': antivirus, 'Ταχυδρομείο': mail })[TAB](win);
}
const msgbox = win => { if (MSG) win.appendChild(mk('p', MSG.ok ? 'okm' : 'err', MSG.text)); };
async function act(url, body) { const r = await post(url, body); MSG = { ok: r.ok !== false && !r.warn, text: r.error || r.warn || r.msg || '' }; if (!MSG.text) MSG = null; PREVIEW = null; await load(); }

// ---- files
function files(win) {
  const g = mk('div', 'files'); win.appendChild(g);
  const side = mk('div'); g.appendChild(side);
  ST.locations.forEach(l => { const b = mk('button', 'loc' + (l.id === LOC ? ' on' : ''), l.name); b.onclick = () => { LOC = l.id; PREVIEW = null; render(); }; side.appendChild(b); });
  const main = mk('div'); g.appendChild(main);
  const loc = ST.locations.find(l => l.id === LOC);
  const chk = mk('button', 'small-btn', 'Έλεγχος αρχείων'); chk.style.marginBottom = '8px';
  chk.onclick = async () => { const r = await post('/api/check', { loc: LOC }); PREVIEW = { ok: r.good === r.total, name: 'Έλεγχος αρχείων · ' + loc.name, text: 'Ανοίγουν ' + r.good + ' από ' + r.total + ' αρχεία.' + (r.good < r.total ? ' Τα υπόλοιπα είναι κρυπτογραφημένα.' : '') }; render(); };
  main.appendChild(chk);
  if (!loc.files.length) main.appendChild(mk('p', 'small', 'Εδώ δεν υπάρχουν αρχεία.'));
  ST.folders.forEach(fo => {
    const fs = loc.files.filter(f => f.folder === fo); if (!fs.length) return;
    main.appendChild(mk('div', 'fold', fo));
    fs.forEach(f => { const b = mk('button', 'file' + (f.name.endsWith('.locked') ? ' locked' : ''), (f.name.endsWith('.locked') ? '🔒 ' : '📄 ') + f.name);
      b.onclick = async () => { PREVIEW = await post('/api/open', { loc: LOC, id: f.id }); render(); }; main.appendChild(b); });
  });
  if (PREVIEW) { const p = mk('div', 'preview' + (PREVIEW.ok ? '' : ' bad')); p.appendChild(mk('b', '', PREVIEW.name || '')); p.appendChild(mk('p', '', PREVIEW.text || PREVIEW.error)); main.appendChild(p); }
}

// ---- backups
function backups(win) {
  msgbox(win);
  const o1 = mk('div', 'opt'); o1.appendChild(mk('h3', '', 'Φάκελος «Αντίγραφα» στον υπολογιστή'));
  o1.appendChild(mk('p', 'small', 'Κρατά ένα αντίγραφο των αρχείων σε άλλον φάκελο του υπολογιστή.'));
  const b1 = mk('button', 'small-btn', ST.disk_backup ? 'Ανανέωση αντιγράφου' : 'Δημιουργία αντιγράφου'); b1.onclick = () => act('/api/backup', { target: 'disk' }); o1.appendChild(b1); win.appendChild(o1);

  const o2 = mk('div', 'opt'); o2.appendChild(mk('h3', '', 'CloudBox'));
  o2.appendChild(mk('p', 'small', 'Υπηρεσία αποθήκευσης στο διαδίκτυο. Συγχρονίζει τα αρχεία σου αυτόματα: ό,τι αλλάζει εδώ αλλάζει και στο cloud.'));
  const b2 = mk('button', 'small-btn', ST.cloud_on ? 'Απενεργοποίηση συγχρονισμού' : 'Ενεργοποίηση συγχρονισμού'); b2.onclick = () => act('/api/backup', { target: 'cloud', on: !ST.cloud_on }); o2.appendChild(b2); win.appendChild(o2);

  const o3 = mk('div', 'opt'); o3.appendChild(mk('h3', '', 'Εξωτερικός δίσκος'));
  o3.appendChild(mk('p', 'small', ST.ext.plugged ? 'Ο δίσκος είναι συνδεδεμένος στον υπολογιστή.' : 'Ο δίσκος δεν είναι συνδεδεμένος.'));
  const row = mk('div', 'tick');
  const pl = mk('button', 'small-btn', ST.ext.plugged ? 'Ασφαλής αφαίρεση δίσκου' : 'Σύνδεση δίσκου'); pl.onclick = () => act('/api/ext', { plugged: !ST.ext.plugged }); row.appendChild(pl);
  const bk = mk('button', 'small-btn', 'Δημιουργία αντιγράφου'); bk.onclick = () => act('/api/backup', { target: 'ext' }); row.appendChild(bk);
  o3.appendChild(row); win.appendChild(o3);

  win.appendChild(mk('h2', '', 'Επαναφορά αρχείων'));
  win.appendChild(mk('p', 'small', 'Αντιγράφει τα αρχεία από ένα αντίγραφο πίσω στον υπολογιστή.'));
  const r = mk('div', 'tick');
  [['disk', 'Από τον φάκελο «Αντίγραφα»'], ['cloud', 'Από το CloudBox'], ['ext', 'Από τον εξωτερικό δίσκο']].forEach(([k, t]) => {
    const b = mk('button', 'small-btn', t); b.onclick = () => { if (confirm('Τα αρχεία του υπολογιστή θα αντικατασταθούν με αυτά του αντιγράφου. Συνέχεια;')) act('/api/restore', { src: k }); }; r.appendChild(b); });
  win.appendChild(r);
}

// ---- updates
function updates(win) {
  msgbox(win);
  ST.updates.forEach(u => { const r = mk('div', 'row'); r.appendChild(mk('span', '', u.name)); r.appendChild(mk('span', 'pill ' + (u.done ? 'ok' : 'warn'), u.done ? 'Εγκαταστάθηκε' : 'Σε αναμονή')); win.appendChild(r); });
  const pending = ST.updates.some(u => !u.done);
  const b = mk('button', 'big', 'Εγκατάσταση όλων'); b.disabled = !pending; b.onclick = () => act('/api/update', { id: 'all' }); win.appendChild(b);
  const a = mk('label'); const cb = mk('input'); cb.type = 'checkbox'; cb.checked = ST.auto; cb.style.display = 'inline'; cb.style.width = 'auto';
  cb.onchange = () => act('/api/update', { auto: cb.checked }); a.append(cb, ' Αυτόματες ενημερώσεις'); win.appendChild(a);
}

// ---- network
function network(win) {
  win.appendChild(mk('p', ST.net ? 'okm' : 'err', ST.net ? 'Ο υπολογιστής είναι συνδεδεμένος στο δίκτυο του γραφείου και στο διαδίκτυο.' : 'Ο υπολογιστής δεν είναι συνδεδεμένος σε κανένα δίκτυο.'));
  const b = mk('button', 'big', ST.net ? 'Αποσύνδεση από το δίκτυο' : 'Σύνδεση στο δίκτυο'); b.onclick = () => act('/api/net', { on: !ST.net }); win.appendChild(b);
}

// ---- antivirus
function antivirus(win) {
  msgbox(win);
  win.appendChild(mk('p', '', 'Σαρώνει τον υπολογιστή για κακόβουλα προγράμματα και τα αφαιρεί.'));
  const b = mk('button', 'big', 'Σάρωση υπολογιστή'); b.onclick = () => act('/api/scan'); win.appendChild(b);
}

// ---- mail
const WHO = { it: 'Μαρία Κ. · υπεύθυνη του γραφείου', police: 'Δίωξη Ηλεκτρονικού Εγκλήματος', attacker: null };
function done(ST) {   // what the player has really done so far, as sentences
  const l = [];
  l.push(ST.net ? 'Ο υπολογιστής είναι ακόμα συνδεδεμένος στο δίκτυο του γραφείου.' : 'Αποσυνδέσαμε τον υπολογιστή από το δίκτυο.');
  l.push(ST.paid ? 'Έγινε πληρωμή στους εκβιαστές και δεν λάβαμε κλειδί αποκρυπτογράφησης.' : 'Δεν έχει γίνει καμία πληρωμή.');
  l.push(ST.replied ? 'Έχουμε απαντήσει στους εκβιαστές.' : 'Δεν έχουμε επικοινωνήσει με τους εκβιαστές.');
  if (ST.rep_it) l.push('Ενημερώσαμε την υπεύθυνη του γραφείου.');
  if (!ST.infected) l.push('Σαρώσαμε τον υπολογιστή και αφαιρέθηκε το κακόβουλο πρόγραμμα.');
  if (ST.ok_files > 0) l.push('Έχουμε επαναφέρει αρχεία από αντίγραφο ασφαλείας: ' + ST.ok_files + ' από τα ' + ST.total + ' ανοίγουν πλέον κανονικά.');
  l.push('Διατηρούμε το μήνυμα των εκβιαστών και τα ονόματα των αρχείων ως στοιχεία.');
  return l;
}
function template(to) {
  if (to === 'police') return ['Αναφορά περιστατικού ransomware · Λογιστικό Γραφείο Πρωτεύς',
`Αξιότιμοι κύριοι/κυρίες,

Αναφέρω περιστατικό ransomware στον υπολογιστή του λογιστικού μας γραφείου.

Τι συνέβη
Τη Δευτέρα το πρωί, στις 08:30, διαπιστώσαμε ότι τα αρχεία του υπολογιστή μου δεν ανοίγουν. Όλα έχουν πάρει την κατάληξη «.locked» και εμφανίστηκε μήνυμα εκβιασμού που ζητά πληρωμή και ζητά να γράψουμε στη διεύθυνση ${ST.contact}.

Τι επηρεάστηκε
Εννέα αρχεία σε τρεις φακέλους: λογιστικά, πελάτες και προσωπικά. Στα αρχεία των πελατών υπάρχουν προσωπικά δεδομένα.

Τι έχουμε κάνει μέχρι τώρα
${done(ST).map(x => '- ' + x).join('\n')}

Παρακαλώ για τις οδηγίες σας.

Με εκτίμηση,
Θοδωρής Λιάκος
Λογιστικό Γραφείο Πρωτεύς
Τηλέφωνο επικοινωνίας: 210 000 0000`];
  if (to === 'it') return ['Επείγον: ransomware στον υπολογιστή μου',
`Μαρία, καλημέρα,

Σήμερα το πρωί τα αρχεία του υπολογιστή μου κρυπτογραφήθηκαν και εμφανίστηκε μήνυμα εκβιασμού. ${ST.net ? 'Ο υπολογιστής μου είναι ακόμα στο δίκτυο.' : 'Τον έχω αποσυνδέσει από το δίκτυο.'}

Παρακαλώ μην ανοίξεις αρχεία από κοινόχρηστους φακέλους και μην συνδέσεις δίσκους ή USB στον δικό σου υπολογιστή μέχρι να σου πω. Ενημέρωσε και τους υπόλοιπους να μην ανοίγουν ύποπτα μηνύματα.

${ST.rep_auth ? 'Έχω κάνει αναφορά στην αρμόδια αρχή.' : 'Θα κάνω αναφορά στην αρμόδια αρχή.'} Θα σε ενημερώσω για τα επόμενα βήματα.

Θοδωρής`];
  return ['Re: Τα αρχεία σου κρυπτογραφήθηκαν',
`Γεια σας,

Δώστε μου το κλειδί να ανοίξω τα αρχεία μου. Τι πρέπει να κάνω;`];
}
function mail(win) {
  msgbox(win);
  if (ST.phase === 'prep') { win.appendChild(mk('p', 'small', 'Δεν έχεις νέα μηνύματα.')); return; }
  win.appendChild(mk('p', 'small', 'Νέο μήνυμα'));
  const f = mk('form');
  const lt = mk('label', '', 'Προς'); const sel = mk('select');
  [['', 'Διάλεξε παραλήπτη'], ['it', WHO.it], ['police', WHO.police], ['attacker', ST.contact]].forEach(([v, t]) => { const o = mk('option', '', t); o.value = v; sel.appendChild(o); });
  lt.appendChild(sel); f.appendChild(lt);
  const prev = mk('div', 'mailprev'); prev.hidden = true; const subj = mk('div', 'mailsub'); const body = mk('div', 'mailbody'); prev.append(subj, body); f.appendChild(prev);
  let cur = null;
  sel.onchange = () => { if (!sel.value) { prev.hidden = true; cur = null; return; } cur = template(sel.value); subj.textContent = cur[0]; body.textContent = cur[1]; prev.hidden = false; };
  const btn = mk('button', 'big', 'Αποστολή'); btn.type = 'submit'; f.appendChild(btn); win.appendChild(f);
  f.addEventListener('submit', ev => { ev.preventDefault(); act('/api/mail', { to: sel.value ? [sel.value] : [], subject: cur ? cur[0] : '', body: cur ? cur[1] : '' }); });
  if (ST.sent.length) {
    win.appendChild(mk('h2', '', 'Απεσταλμένα'));
    ST.sent.forEach(m => { const r = mk('div', 'row'); r.appendChild(mk('span', '', (m.to[0] === 'attacker' ? ST.contact : WHO[m.to[0]]) + ' · ' + m.subject)); win.appendChild(r); });
  }
}
load();
