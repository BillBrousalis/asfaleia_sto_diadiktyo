/* Copy buttons.  window.copyText(text, button) copies (works on plain http, where navigator.clipboard is unavailable),
   window.copyButton(getText, label) builds a button, <button data-copy="..."> copies its attribute, and every
   code.flag (the completion code) automatically gets a "Αντιγραφή" button next to it. */
(function () {
  function fallback(text) {
    var t = document.createElement('textarea'); t.value = text;
    t.style.position = 'fixed'; t.style.opacity = '0'; document.body.appendChild(t); t.select();
    var ok = false; try { ok = document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(t); return ok;
  }
  window.copyText = function (text, btn) {
    var done = function (ok) {
      if (!btn) return;
      var old = btn.dataset.label || btn.textContent; btn.dataset.label = old;
      btn.textContent = ok ? 'Αντιγράφηκε ✓' : 'Δεν αντιγράφηκε';
      clearTimeout(btn._t); btn._t = setTimeout(function () { btn.textContent = old; }, 1600);
    };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(fallback(text)); });
    else done(fallback(text));
  };
  window.copyButton = function (getText, label) {
    var b = document.createElement('button'); b.type = 'button'; b.className = 'copybtn'; b.textContent = label || 'Αντιγραφή';
    b.addEventListener('click', function () { window.copyText(typeof getText === 'function' ? getText() : getText, b); });
    return b;
  };
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('button[data-copy]');
    if (b) window.copyText(b.getAttribute('data-copy'), b);
  });
  function decorate() {
    document.querySelectorAll('code.flag').forEach(function (c) {
      if (c.dataset.copyReady) return; c.dataset.copyReady = '1';
      c.insertAdjacentElement('afterend', window.copyButton(function () { return c.textContent; }));
    });
  }
  document.addEventListener('DOMContentLoaded', function () {
    decorate(); new MutationObserver(decorate).observe(document.body, { childList: true, subtree: true });
  });
})();
