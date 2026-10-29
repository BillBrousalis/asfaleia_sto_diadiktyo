#!/bin/bash
set -e

USER_PART="eleni.markou"
DOMAIN="meltemi-logistics.example"
PASS="cadmus2026"
MAILDIR="/var/mail/vhosts/${DOMAIN}/${USER_PART}"

mkdir -p "${MAILDIR}"/{new,cur,tmp}

HASH=$(doveadm pw -s SHA512-CRYPT -p "${PASS}")
echo "${USER_PART}@${DOMAIN}:${HASH}:5000:5000::${MAILDIR}::" > /etc/dovecot/passwd
chown dovecot:dovecot /etc/dovecot/passwd
chmod 600 /etc/dovecot/passwd

# Deliver the emails oldest-first, with arrival time = Date header (UTC).
php -r '
foreach (json_decode(file_get_contents("/etc/mail/lab/mail-manifest.json"), true) as $m)
    echo $m["src"], " ", $m["name"], " ", $m["mtime"], "\n";
' | while read -r SRC NAME MTIME; do
    cp "/etc/mail/lab/${SRC}" "${MAILDIR}/new/${NAME}"
    TZ=UTC touch -t "${MTIME}" "${MAILDIR}/new/${NAME}"
done

chown -R vmail:vmail /var/mail/vhosts
chmod -R 700 /var/mail/vhosts

php /var/lib/roundcube/bin/initdb.sh --dir=/var/lib/roundcube/SQL 2>/dev/null || true

exec /usr/bin/supervisord -c /etc/supervisord.conf
