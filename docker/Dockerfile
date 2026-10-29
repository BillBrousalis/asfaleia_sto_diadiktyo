# The shared lab server (VM2) as one image: Apache in front on :80 (name-based vhosts), Roundcube + Dovecot + Postfix
# for lab A, and three Flask apps on local ports (A 8080, B 8091, C 8092). Build context: the repository root.
FROM debian:12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    postfix dovecot-core dovecot-imapd apache2 libapache2-mod-php php php-sqlite3 \
    php-mbstring php-xml php-intl php-zip php-curl php-cli roundcube roundcube-sqlite3 \
    supervisor curl python3-flask \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 5000 vmail && useradd -u 5000 -g vmail -s /sbin/nologin vmail

# --- lab A: mail server and webmail
COPY lab-phishing-triage/config/dovecot.conf /etc/dovecot/dovecot.conf
COPY lab-phishing-triage/config/postfix-main.cf /etc/postfix/main.cf
COPY lab-phishing-triage/config/roundcube.config.php /etc/roundcube/config.inc.php
RUN mkdir -p /var/roundcube/db && chown www-data:www-data /var/roundcube/db
COPY lab-phishing-triage/config/apache-roundcube.conf /etc/apache2/sites-available/001-mail.conf
COPY lab-phishing-triage/roundcube-plugin/cadmus_report /var/lib/roundcube/plugins/cadmus_report
COPY lab-phishing-triage/sim/static/outcome.js /var/lib/roundcube/plugins/cadmus_report/outcome.js
COPY lab-phishing-triage/mail/ /etc/mail/lab/
COPY lab-phishing-triage/init/mail-manifest.json /etc/mail/lab/mail-manifest.json

# --- the three simulations
COPY lab-phishing-triage/sim/ /opt/lab-phishing/
COPY lab-leaked-account/sim/ /opt/lab-leaked-account/
COPY lab-ransomware-friday/sim/ /opt/lab-ransomware-friday/

# --- hub page and the name-based virtual hosts
COPY hub/ /var/www/hub/
COPY docker/make-vhosts.sh /usr/local/bin/make-vhosts.sh
RUN a2dissite 000-default && a2enmod rewrite php8.2 proxy proxy_http && bash /usr/local/bin/make-vhosts.sh

COPY docker/supervisord.conf /etc/supervisord.conf
COPY lab-phishing-triage/init/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
