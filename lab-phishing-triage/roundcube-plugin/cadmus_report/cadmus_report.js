/* Cadmus Lab A — toolbar button "Αναφορά απάτης" */
if (window.rcmail) {
  rcmail.addEventListener('init', function () {
    // a genuine mail was reported earlier: the exercise has to be restarted from the progress page
    if (rcmail.env.cadmus_redirect && rcmail.env.cadmus_progress) { location.href = rcmail.env.cadmus_progress; return; }
    // link back to the start screen (instructions), served by the lab server
    var help = document.createElement('a');
    help.className = 'cadmus-home';
    help.href = rcmail.env.cadmus_home || '#';
    help.target = '_blank';
    help.title = 'Αρχική οθόνη και βήματα';
    help.textContent = 'Οδηγίες';
    var menu = document.getElementById('taskmenu');
    if (menu) menu.insertBefore(help, menu.firstChild);

    function currentUid() {
      return rcmail.env.uid || (rcmail.message_list && rcmail.message_list.get_single_selection());
    }

    rcmail.register_command('plugin.cadmus_report', function () {
      var uid = currentUid();
      if (!uid) return;
      rcmail.http_post('plugin.cadmus_report', { _uid: uid, _mbox: rcmail.env.mailbox }, rcmail.set_busy(true, 'loading'));
    }, false);

    if (rcmail.message_list) {
      rcmail.message_list.addEventListener('select', function (list) {
        rcmail.enable_command('plugin.cadmus_report', list.get_selection().length === 1);
      });
    } else if (rcmail.env.uid) {
      rcmail.enable_command('plugin.cadmus_report', true);
    }

    rcmail.addEventListener('plugin.cadmus_report_result', function (d) {
      if (d.error) { rcmail.display_message('Η αναφορά δεν ήταν δυνατή.', 'error'); return; }
      // all 8 scams reported, or a genuine mail reported: the explanation is on the progress page
      if ((d.complete || d.restart) && rcmail.env.cadmus_progress) { location.href = rcmail.env.cadmus_progress; return; }
      var mk = function (tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
      var root = mk('div', 'cadmus');
      root.appendChild(mk('p', 'cadmus-verdict ' + (d.ok ? 'ok' : 'warn'),
        'Σωστά: αυτό το μήνυμα ήταν απάτη.'));
      var ul = mk('ul'); d.why.forEach(function (t) { ul.appendChild(mk('li', '', t)); }); root.appendChild(ul);
      if (d.ok && d.moved) root.appendChild(mk('p', 'cadmus-note', 'Το μήνυμα μεταφέρθηκε στον φάκελο «Αναφορές». Μην πατήσεις τους συνδέσμους του.'));
      var box = mk('div', 'cadmus-box'); root.appendChild(box);

      var buttons = [];
      buttons.push({
        text: 'Δες τι θα συνέβαινε αν το είχες ακολουθήσει',
        'class': 'mainaction',
        click: function (e, ui) { renderOutcome(box, d.outcome, { user: 'Ελένη' }); $(e.target).hide(); }
      });
      buttons.push({
        text: 'Κλείσιμο',
        click: function (e, ui) { $(this).dialog('close'); }
      });
      var dialog = rcmail.show_popup_dialog(root, 'Αναφορά απάτης', buttons, {
        width: 680,
        height: 520,
        close: function () {
          $(this).remove();
          if (d.moved) {
            if (rcmail.env.action === 'show') rcmail.location_href({ _task: 'mail', _mbox: rcmail.env.mailbox }, window);
            else if (rcmail.message_list) {
              // drop only the moved row instead of reloading the whole list
              rcmail.message_list.remove_row(String(d.uid), false);
              rcmail.message_list.clear_selection();
              rcmail.show_contentframe(false);
              rcmail.enable_command('plugin.cadmus_report', false);
            }
          }
        }
      });
    });
  });
}
