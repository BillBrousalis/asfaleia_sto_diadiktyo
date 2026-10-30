/* Cadmus Lab B — the simulated services (email, shop, social network, bank), the vault and the breach check. */
const $app = document.getElementById('app');
const mk = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
const post = (url, body) => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) }).then(r => r.status === 204 ? {} : r.json());
const get = url => fetch(url).then(r => r.json());
const BRAND = { email: 'Aigaio Mail', shop: 'Κυκλαδικό Κατάστημα', social: 'Συνομιλία', bank: 'Elara Bank', vault: 'Passkeeper · Διαχειριστής κωδικών', breach: 'Breach Check' };

document.title = BRAND[SVC];

// ---- top bar (way back to the start screen / completion) and the "phone"
const bar = document.getElementById('bar'), sms = document.getElementById('sms');
async function refreshBar() {
  const b = await get('/api/bar');
  bar.hidden = false; bar.className = 'bar'; bar.innerHTML = '';
  if (b.done) { bar.classList.add('done'); bar.appendChild(mk('span', '', 'Συγχαρητήρια! Ολοκλήρωσες με επιτυχία το lab. Κωδικός επιβεβαίωσης: ' + b.flag + ' ')); bar.appendChild(copyButton(() => b.flag, 'Αντιγραφή κωδικού')); bar.append(' · '); }
  const home = mk('a', '', 'Αρχική οθόνη και βήματα'); home.href = '/home'; home.target = '_blank';
  const prog = mk('a', '', 'Πρόοδος'); prog.href = '/progress'; prog.target = '_blank';
  bar.appendChild(home); bar.append(' · '); bar.appendChild(prog);
}
refreshBar(); setInterval(refreshBar, 4000);
function phone(code) {
  sms.hidden = false; sms.innerHTML = '';
  sms.appendChild(mk('small', '', 'Το κινητό σου · SMS'));
  sms.appendChild(mk('div', '', 'Ο κωδικός επιβεβαίωσης είναι ' + code + '. Μην τον δώσεις σε κανέναν.'));
  sms.appendChild(copyButton(() => code, 'Αντιγραφή κωδικού'));
  const x = mk('button', 'x', '✕'); x.title = 'Κλείσιμο'; x.onclick = () => { sms.hidden = true; }; sms.appendChild(x);
}

// ---- generic widgets
function field(label, type, name, value) {
  const l = mk('label', '', label); const i = mk('input'); i.type = type || 'text'; i.name = name; i.autocomplete = 'off';
  if (value) i.value = value; l.appendChild(i); return l;
}

// ---- login
async function showLogin(me) {
  $app.innerHTML = '';
  $app.appendChild(mk('div', 'brand', BRAND[SVC]));
  const box = mk('div', 'panel'); $app.appendChild(box);
  box.appendChild(mk('h2', '', 'Σύνδεση'));
  const f = mk('form'); const u = field('Όνομα χρήστη', 'text', 'user', me.user); const p = field('Κωδικός', 'password', 'pw');
  const code = field('Κωδικός SMS από το κινητό σου', 'text', 'code'); code.hidden = true;
  const msg = mk('p', 'small'); const btn = mk('button', 'big', 'Σύνδεση'); btn.type = 'submit';
  f.append(u, p, code, btn, msg); box.appendChild(f);
  if (SVC === 'bank') {
    const forgot = mk('button', 'link', 'Ξέχασες τον κωδικό; Επαναφορά με SMS'); forgot.type = 'button'; box.appendChild(forgot);
    forgot.addEventListener('click', () => showRecover(me));
  }
  f.addEventListener('submit', async ev => {
    ev.preventDefault();
    const r = await post('/api/login', { user: f.user.value, pw: f.pw.value, code: f.code.value });
    if (r.ok) return load();
    if (r.need_code) { code.hidden = false; if (r.sms) phone(r.sms); msg.textContent = r.error || 'Έγραψε τον κωδικό που έφτασε στο κινητό σου.'; msg.className = 'small' + (r.error ? ' err' : ''); return; }
    msg.textContent = r.error || 'Η σύνδεση απέτυχε.'; msg.className = 'small err';
  });
}

function showRecover(me) {
  $app.innerHTML = ''; $app.appendChild(mk('div', 'brand', BRAND[SVC]));
  const box = mk('div', 'panel'); $app.appendChild(box); box.appendChild(mk('h2', '', 'Επαναφορά κωδικού'));
  box.appendChild(mk('p', 'small', 'Θα στείλουμε έναν κωδικό SMS στο κινητό που έχεις δηλώσει. Μετά την επαναφορά αποσυνδέονται οι άγνωστες συσκευές.'));
  const f = mk('form'); const code = field('Κωδικός SMS', 'text', 'code'); code.hidden = true; const np = field('Νέος κωδικός', 'password', 'new'); np.hidden = true;
  const msg = mk('p', 'small'); const btn = mk('button', 'big', 'Στείλε κωδικό SMS'); btn.type = 'submit'; f.append(code, np, btn, msg); box.appendChild(f);
  const back = mk('button', 'link', 'Πίσω στη σύνδεση'); back.type = 'button'; back.addEventListener('click', () => showLogin(me)); box.appendChild(back);
  f.addEventListener('submit', async ev => { ev.preventDefault();
    const r = await post('/api/recover', { code: f.code.value, new: f.new.value });
    if (r.ok) return showLogin(me);
    if (r.need_code) { phone(r.sms); code.hidden = false; np.hidden = false; btn.textContent = 'Επαναφορά κωδικού'; msg.textContent = 'Έγραψε τον κωδικό SMS και τον νέο σου κωδικό.'; msg.className = 'small'; return; }
    msg.textContent = r.error || 'Η επαναφορά απέτυχε.'; msg.className = 'small err'; });
}

// ---- dashboard shell
let TAB = null;
async function load() {
  const d = await fetch('/api/data');
  if (d.status === 401) return showLogin(await get('/api/me'));
  render(await d.json());
}
function shell(d, tabs) {
  $app.innerHTML = '';
  const head = mk('div', 'row'); head.appendChild(mk('div', 'brand', BRAND[SVC]));
  const out = mk('button', 'small-btn', 'Αποσύνδεση ' + d.user); out.addEventListener('click', async () => { await post('/api/logout'); load(); });
  head.appendChild(out); $app.appendChild(head);
  const t = mk('div', 'tabs'); const names = Object.keys(tabs); TAB = names.includes(TAB) ? TAB : names[0];
  names.forEach(n => { const b = mk('button', 'tab' + (n === TAB ? ' on' : ''), n); b.addEventListener('click', () => { TAB = n; load(); }); t.appendChild(b); });
  $app.appendChild(t);
  const body = mk('div'); $app.appendChild(body); tabs[TAB](body);
}
const panel = (parent, title) => { const p = mk('div', 'panel'); if (title) p.appendChild(mk('h2', '', title)); parent.appendChild(p); return p; };

// ---- security tab (shared)
function security(body, d, extra) {
  const pw = panel(body, 'Κωδικός');
  const f = mk('form'); f.append(field('Τρέχων κωδικός', 'password', 'old'), field('Νέος κωδικός', 'password', 'new'));
  const so = mk('label'); const cb = mk('input'); cb.type = 'checkbox'; cb.name = 'so'; cb.style.display = 'inline'; cb.style.width = 'auto'; so.append(cb, ' Αποσύνδεση από όλες τις άλλες συσκευές'); f.appendChild(so);
  const b = mk('button', 'big', 'Αλλαγή κωδικού'); b.type = 'submit'; f.appendChild(b); const say = mk('p', 'small'); f.appendChild(say); pw.appendChild(f);
  f.addEventListener('submit', async ev => { ev.preventDefault();
    const r = await post('/api/password', { old: f.old.value, new: f.new.value, signout_others: f.so.checked });
    if (r.ok) { say.textContent = 'Ο κωδικός άλλαξε.'; say.className = 'small okm'; setTimeout(load, 700); } else { say.textContent = r.error; say.className = 'small err'; } });

  if (d.mfa !== null && d.mfa !== undefined) {
    const m = panel(body, 'Διπλή επαλήθευση');
    if (d.mfa) m.appendChild(mk('p', 'okm', 'Ενεργή: κάθε σύνδεση ζητά και κωδικό SMS.'));
    else {
      m.appendChild(mk('p', '', 'Εκτός από τον κωδικό, θα ζητείται και ένας κωδικός μιας χρήσης που έρχεται στο κινητό σου.'));
      const f2 = mk('form'); const code = field('Κωδικός SMS', 'text', 'code'); code.hidden = true; const bb = mk('button', 'big', 'Ενεργοποίηση'); bb.type = 'submit'; const s2 = mk('p', 'small');
      f2.append(code, bb, s2); m.appendChild(f2);
      f2.addEventListener('submit', async ev => { ev.preventDefault(); const r = await post('/api/mfa', { code: f2.code.value });
        if (r.ok) return load(); if (r.sms) phone(r.sms); code.hidden = false; s2.textContent = r.error || 'Έγραψε τον κωδικό που έφτασε στο κινητό σου.'; s2.className = 'small' + (r.error ? ' err' : ''); });
    }
  }
  const s = panel(body, 'Συνδεδεμένες συσκευές');
  d.sessions.forEach(x => { const r = mk('div', 'row'); r.appendChild(mk('span', '', x.device));
    if (x.id === 'me') r.appendChild(mk('span', 'pill ok', 'Αυτή η συσκευή'));
    else { const rv = mk('button', 'small-btn danger', 'Αποσύνδεση'); rv.addEventListener('click', async () => { await post('/api/revoke', { id: x.id }); load(); }); r.appendChild(rv); }
    s.appendChild(r); });
  if (extra) extra(body, d);
}

// ---- services
const RENDER = {
  email(d) {
    shell(d, {
      'Εισερχόμενα': body => { const p = panel(body); d.mails.forEach(m => {
        const row = mk('div', 'msg'); row.appendChild(mk('div', 's', m.subj)); row.appendChild(mk('div', 'm', m.from + ' · ' + m.date));
        const open = mk('div'); open.hidden = true; open.appendChild(mk('p', '', m.body));
        m.links.forEach(l => { const a = mk('a', '', l[0]); a.href = l[1]; a.target = '_blank'; open.appendChild(a); });
        row.appendChild(open); row.addEventListener('click', () => { open.hidden = !open.hidden; }); p.appendChild(row); }); },
      'Ασφάλεια': body => security(body, d, (b, dd) => {
        const r = panel(b, 'Κανόνες προώθησης');
        if (!dd.rules.length) r.appendChild(mk('p', 'small', 'Κανένας κανόνας προώθησης.'));
        dd.rules.forEach(x => { const row = mk('div', 'row'); row.appendChild(mk('span', '', x.text)); const rm = mk('button', 'small-btn danger', 'Διαγραφή');
          rm.addEventListener('click', async () => { await post('/api/rule/delete', { id: x.id }); load(); }); row.appendChild(rm); r.appendChild(row); }); })
    });
  },
  shop(d) {
    shell(d, {
      'Ο λογαριασμός μου': body => { const p = panel(body, 'Παραγγελίες'); d.orders.forEach(o => p.appendChild(mk('div', 'row', o)));
        const q = panel(body, 'Στοιχεία'); q.appendChild(mk('div', 'row', 'Διεύθυνση παράδοσης: ' + d.address)); q.appendChild(mk('div', 'row', 'Αποθηκευμένη κάρτα: ' + d.card)); },
      'Ασφάλεια': body => security(body, d)
    });
  },
  social(d) {
    shell(d, {
      'Το προφίλ μου': body => { const p = panel(body, 'Αναρτήσεις'); d.posts.forEach(x => { const row = mk('div', 'row'); row.appendChild(mk('span', '', x.text));
        const sel = mk('select'); [['public', 'Δημόσια'], ['friends', 'Φίλοι'], ['me', 'Μόνο εγώ']].forEach(([v, t]) => { const o = mk('option', '', t); o.value = v; if (x.vis === v) o.selected = true; sel.appendChild(o); });
        sel.style.width = 'auto'; sel.addEventListener('change', async () => { await post('/api/post', { id: x.id, action: sel.value }); load(); });
        const del = mk('button', 'small-btn danger', 'Διαγραφή'); del.addEventListener('click', async () => { await post('/api/post', { id: x.id, action: 'delete' }); load(); });
        const c = mk('span'); c.append(sel, ' ', del); row.appendChild(c); p.appendChild(row); }); },
      'Ασφάλεια': body => security(body, d)
    });
  },
  bank(d) {
    shell(d, {
      'Λογαριασμός': body => { const p = panel(body, 'Ο λογαριασμός μου'); p.appendChild(mk('div', 'row', d.account)); },
      'Δικαιούχοι': body => { const p = panel(body, 'Αποθηκευμένοι δικαιούχοι'); d.payees.forEach(x => { const row = mk('div', 'row'); row.appendChild(mk('span', '', x.name));
        const rm = mk('button', 'small-btn danger', 'Διαγραφή'); rm.addEventListener('click', async () => { await post('/api/payee/delete', { id: x.id }); load(); }); row.appendChild(rm); p.appendChild(row); }); },
      'Ασφάλεια': body => security(body, d, (b, dd) => { const a = panel(b, 'Ειδοποιήσεις συναλλαγών'); const on = dd.alerts;
        a.appendChild(mk('p', on ? 'okm' : '', on ? 'Ενεργές: λαμβάνεις SMS για κάθε συναλλαγή.' : 'Ανενεργές.'));
        const t = mk('button', 'big', on ? 'Απενεργοποίηση' : 'Ενεργοποίηση'); t.addEventListener('click', async () => { await post('/api/alerts', { on: !on }); load(); }); a.appendChild(t); })
    });
  }
};
function render(d) { RENDER[SVC](d); }

// ---- breach check
function showBreach() {
  $app.innerHTML = ''; $app.appendChild(mk('div', 'brand', BRAND.breach));
  const p = panel($app, 'Αποτέλεσμα για eleni.markou@aigaio-mail.example');
  p.appendChild(mk('p', 'err', 'Η διεύθυνση βρέθηκε σε 1 διαρροή δεδομένων.'));
  const row = mk('div', 'row'); row.appendChild(mk('b', '', 'ShopStar · 2019')); p.appendChild(row);
  p.appendChild(mk('p', '', 'Τι εκτέθηκε: διεύθυνση email και κωδικός πρόσβασης.'));
  const pw = mk('p'); pw.append('Κωδικός που εκτέθηκε: ', mk('span', 'pw', 'Ele••••85')); p.appendChild(pw);
  p.appendChild(mk('p', 'small', 'Αν έχεις χρησιμοποιήσει τον ίδιο κωδικό και σε άλλους λογαριασμούς, ο απατεώνας θα τον δοκιμάσει εκεί.'));
}

// ---- vault
async function showVault() {
  const d = await get('/api/vault');
  $app.innerHTML = ''; $app.appendChild(mk('div', 'brand', BRAND.vault));
  const p = panel($app, 'Οι κωδικοί σου');
  d.rows.forEach(r => { const row = mk('div', 'row'); const left = mk('div'); left.appendChild(mk('b', '', r.name)); left.appendChild(mk('div', 'small', r.user));
    const a = mk('a', 'small', r.url); a.href = r.url; a.target = '_blank'; left.appendChild(a); row.appendChild(left);
    const mid = mk('div'); const code = mk('span', 'pw', '••••••••••'); const show = mk('button', 'small-btn', 'Εμφάνιση'); let v = false;
    show.addEventListener('click', () => { v = !v; code.textContent = v ? r.pw : '••••••••••'; show.textContent = v ? 'Απόκρυψη' : 'Εμφάνιση'; });
    mid.append(code, ' ', show, copyButton(() => r.pw)); row.appendChild(mid);
    const tags = mk('div');
    if (r.reused) tags.appendChild(mk('span', 'pill bad', 'Ίδιος κωδικός σε άλλον λογαριασμό'));
    if (r.leaked) tags.appendChild(mk('span', 'pill bad', 'Διέρρευσε'));
    if (r.weak) tags.appendChild(mk('span', 'pill warn', 'Αδύναμος'));
    if (!r.reused && !r.leaked && !r.weak) tags.appendChild(mk('span', 'pill ok', 'Εντάξει'));
    row.appendChild(tags); p.appendChild(row); });
  const g = panel($app, 'Δημιουργία νέου κωδικού');
  g.appendChild(mk('p', 'small', 'Δημιούργησε έναν τυχαίο, μακρύ κωδικό και αντίγραψέ τον στη φόρμα αλλαγής κωδικού του λογαριασμού.'));
  const out = mk('input'); out.type = 'text'; out.readOnly = true; out.placeholder = 'Πάτα «Δημιουργία»';
  const b = mk('button', 'big', 'Δημιουργία'); b.addEventListener('click', async () => { out.value = (await post('/api/generate')).pw; out.select(); });
  const c = copyButton(() => out.value);
  g.append(out, document.createElement('br'), b, ' ', c);
  const r = mk('button', 'link', 'Ανανέωση λίστας'); r.addEventListener('click', showVault); $app.appendChild(r);
}

(async () => {
  if (SVC === 'breach') return showBreach();
  if (SVC === 'vault') return showVault();
  load();
})();
