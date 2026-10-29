<?php
$config = [];
$config['default_host'] = '127.0.0.1';
$config['default_port'] = 143;
$config['imap_conn_options'] = ['ssl' => ['verify_peer' => false, 'verify_peer_name' => false]];
$config['smtp_server'] = '127.0.0.1';
$config['smtp_port'] = 25;
$config['smtp_user'] = '';
$config['smtp_pass'] = '';
$config['product_name'] = 'Webmail';
$config['support_url'] = '';
$config['skin'] = 'elastic';
$config['enable_installer'] = false;
$config['des_key'] = 'cadmus_lab_secret_key_24';
$config['db_dsnw'] = 'sqlite:////var/roundcube/db/roundcube.db';

// ── Lab settings ──────────────────────────────────────────────────────────────
$config['language'] = 'el_GR';
$config['message_show_email'] = true;   // show the full sender address next to the name
$config['plugins'] = ['cadmus_report'];
$config['dont_override'] = ['message_show_email', 'language'];
