#!/bin/bash
# Starts the three labs locally (Docker): one lab server (VM2) + one Firefox (VM1). Stop with ./stop.sh
set -e
cd "$(dirname "$0")/docker"

if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] Docker is not running or not installed. Start Docker Desktop and try again."
    exit 1
fi

docker compose up -d --build

cat <<'EOT'

================================================
  The labs are ready (give it ~30 seconds on first start).

  Open in your browser:   http://localhost:3030
  (Firefox inside the browser; it opens the page
   where you pick the lab)

  The three labs:
    http://phishing.cadmus-labs.example     (inside that Firefox)
    http://accounts.cadmus-labs.example
    http://ransomware.cadmus-labs.example

  Direct access to the server (no simulated names): http://localhost:8110
================================================
EOT
