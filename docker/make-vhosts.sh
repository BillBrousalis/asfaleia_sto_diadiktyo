#!/bin/bash
# Writes the Apache virtual hosts of the shared lab server (the same layout the Ansible playbook creates).
#   000-hub          default vhost (the IP address): the page that lists the three labs
#   001-mail         Roundcube, lab A (config/apache-roundcube.conf)
#   002-phishing     lab A: simulated websites + start screen / progress page   -> Flask :8080
#   003-accounts     lab B: simulated services + start screen / progress page   -> Flask :8091
#   004-ransomware   lab C: the simulated computer + start screen / progress    -> Flask :8092
set -e
SITES=/etc/apache2/sites-available

cat > $SITES/000-hub.conf <<CONF
<VirtualHost *:80>
    DocumentRoot /var/www/hub
    <Directory /var/www/hub>
        Options -Indexes
        Require all granted
    </Directory>
</VirtualHost>
CONF

proxy_vhost() {   # file, port, start host, hosts file
    local file=$1 port=$2 start=$3 hosts=$4
    {
        echo "<VirtualHost *:80>"
        echo "    ServerName $start"
        for h in $(cat "$hosts"); do echo "    ServerAlias $h"; done
        echo "    ProxyPreserveHost On"
        echo "    ProxyPass / http://127.0.0.1:$port/"
        echo "    ProxyPassReverse / http://127.0.0.1:$port/"
        echo "</VirtualHost>"
    } > "$SITES/$file"
}

proxy_vhost 002-phishing.conf   8080 phishing.cadmus-labs.example   /opt/lab-phishing/hosts.txt
proxy_vhost 003-accounts.conf   8091 accounts.cadmus-labs.example   /opt/lab-leaked-account/hosts.txt
proxy_vhost 004-ransomware.conf 8092 ransomware.cadmus-labs.example /opt/lab-ransomware-friday/hosts.txt

a2ensite 000-hub 001-mail 002-phishing 003-accounts 004-ransomware
