# Cadmus — εργαστήρια κυβερνοασφάλειας (3 labs, ένα μηχάνημα)

Τρία εργαστήρια για αρχάριους και μη τεχνικούς, στα ελληνικά. Και τα τρία τρέχουν **στο ίδιο μηχάνημα (VM2)**. Ο παίκτης ανοίγει τον Firefox του VM1, πηγαίνει στη διεύθυνση του VM2 και διαλέγει την άσκηση.

| Lab | Άσκηση | Αρχική οθόνη |
|---|---|---|
| A | Αναγνώριση spam και phishing emails | `http://phishing.labs.example` |
| B | Ασφάλιση λογαριασμών μετά από διαρροή κωδικού | `http://accounts.labs.example` |
| C | Προστασία και ανάκτηση αρχείων από ransomware | `http://ransomware.labs.example` |

Η διεύθυνση IP του VM2 (`http://192.168.10.20`) δείχνει μια σελίδα με τα τρία labs και κουμπιά προς τις αρχικές οθόνες τους.

## Δομή

```
topology.yml                  # vm1 (xubuntu, c3_r3_d15) + vm2 (server, c2_r2_d12) + router (standard.small), δίκτυο 192.168.10.0/24
variables.yml                 # κενό ({}), όπως στο παράδειγμα btcmp-18
provisioning/
  playbook.yml                # ένα playbook για και τα τρία labs
  requirements.yml            # role user-access
hub/                          # η σελίδα επιλογής άσκησης (default vhost)
lab-phishing-triage/          # Lab A: theory.md · Questions_Answers.md · Solution.md · sim/ · roundcube-plugin/ · mail/ · tools/
lab-leaked-account/           # Lab B: theory.md · Questions_Answers.md · Solution.md · sim/ · tools/
lab-ransomware-friday/        # Lab C: theory.md · Questions_Answers.md · Solution.md · sim/ · tools/
docker/                       # τοπική εκδοχή (Dockerfile, docker-compose.yml) για δοκιμή χωρίς VM
tools/check_hosts.py          # έλεγχος ότι τα ονόματα είναι μοναδικά και ίδια σε όλα τα αρχεία
cadmus_training_definition.json  # training definition για την πλατφόρμα (παράγεται από tools/build_training_definition.py)
example_training_def.json     # το παράδειγμα της πλατφόρμας (μορφή αναφοράς)
run.sh  stop.sh               # τοπικό τρέξιμο με Docker
```

## Πώς δουλεύει το κοινό μηχάνημα
Ο Apache ακούει στη θύρα 80 και δρομολογεί **με βάση το όνομα** (name-based virtual hosts). Οι εφαρμογές τρέχουν σε τοπικές θύρες.

| Όνομα (Host) | Πηγαίνει σε |
|---|---|
| η διεύθυνση IP (και ό,τι άγνωστο) | σελίδα επιλογής (`hub/`) |
| `mail.meltemi-logistics.example` | Roundcube (Lab A) |
| `phishing.labs.example` + 11 ψεύτικα sites | Flask του A, θύρα 8080 |
| `accounts.labs.example` + 6 υπηρεσίες | Flask του B, θύρα 8091 |
| `ransomware.labs.example` + `pc.protefs-office.example` | Flask του C, θύρα 8092 |

Το VM1 λύνει και τα 22 ονόματα προς το VM2 μέσω `/etc/hosts` (το ορίζει το playbook). Κάθε lab κρατά τη δική του κατάσταση, οπότε οι παίκτες δεν επηρεάζουν τα άλλα labs.
Τα ονόματα πρέπει να είναι μοναδικά σε όλα τα labs: για αυτό το κατάστημα του Lab B είναι στο `shop.kyklades-store.example` (το `www.kykladiko-shop.example` ανήκει στο Lab A).

## Πρόσβαση
- **VM1 (μαθητής):** χρήστης `user` · `Password123` (ρόλος `user-access`).
- **Lab A webmail:** `eleni.markou@meltemi-logistics.example` · `cadmus2026`.

## Τοπικά (Docker)
```
./run.sh          # ανοίγει: http://localhost:3030  (Firefox μέσα στον browser, με τη σελίδα επιλογής)
./stop.sh
```
Το `docker/docker-compose.yml` στήνει `vm2` (192.168.13.20, θύρα `8110` προς τα έξω) και `vm1` (Firefox, θύρα `3030`). Αν αλλάξεις hostname σε κάποιο lab, τρέξε `python3 tools/check_hosts.py` και ενημέρωσε το `extra_hosts`.

## Για τον εκπαιδευτή
- Όλα τα ονόματα είναι πλασματικά (`.example`). Κανένα εξωτερικό αίτημα.
- Εργαλεία ελέγχου (δεν αναπτύσσονται στο VM): `lab-*/tools/`. Τα Lab B και C τρέχουν με `START_HOST=<αρχική οθόνη> python3 tools/play.py http://127.0.0.1:8110 <σενάριο>`, το Lab A με `python3 tools/verify_key.py`.
- Κάθε lab έχει flag ολοκλήρωσης (`FLAG{…}`) στο `Questions_Answers.md` και στο `Solution.md` του.
