# OpsSecure Suite

A production-ready internal security toolkit for SSL certificate monitoring, certificate management, crypto utilities, network analysis, and data conversion.

---

## Features

| Module             | Description                                                                |
|--------------------|----------------------------------------------------------------------------|
| **SSL Monitoring** | Track cert expiry, scheduled scans, email alerts at milestones             |
| **Cert Reader**    | Parse and inspect uploaded PEM / DER / CRT / CER certificates              |
| **Cert Matcher**   | Verify a certificate matches its private key                               |
| **Cert Generator** | Generate self-signed certificates with custom CN, SAN, validity & key size |
| **Crypto Tools**   | AES (Fernet) encrypt/decrypt, Base64 encode/decode, password generator     |
| **Secret Vault**   | Store AES-encrypted secrets in the database                                |
| **Converters**     | JSON ↔ YAML ↔ Excel bidirectional conversion                               |
| **Network Tools**  | TCP Ping, Port Scanner                                                     |

---

## Project Structure

```
ssl_monitor_prod/
├── app.py                  # Application factory
├── run.py                  # Entry point
├── config.py               # Config classes (dev / prod)
├── gunicorn.conf.py        # Production WSGI config
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example            # Copy → .env and fill in values
│
├── blueprints/
│   ├── auth.py             # Login / logout
│   ├── main.py             # Dashboard
│   ├── sites.py            # Site management + SSL API
│   ├── certs.py            # Cert reader, matcher & generator
│   ├── crypto.py           # Crypto tools + vault
│   ├── network.py          # Network tools (ping, port scan)
│   └── tools.py            # JSON/YAML/Excel converter
│
├── modules/
│   ├── db.py               # DB init + connection
│   ├── cert_checker.py     # Live SSL inspection
│   ├── cert_reader.py      # Parse uploaded certs
│   ├── cert_matcher.py     # Cert/key match check
│   ├── cert_generator.py   # Self-signed certificate generation
│   ├── network_utils.py    # Ping, port scanner logic
│   ├── converter.py        # Format conversions
│   ├── crypto_utils.py     # Fernet + Base64 helpers
│   ├── email_utils.py      # SMTP alert sender
│   ├── malware_checker.py  # Basic page scan
│   ├── scanner.py          # Background scheduler
│   └── utils.py            # Shared decorators (role_required)
│
├── templates/
│   ├── base.html           # Shared layout & sidebar
│   ├── login.html
│   ├── index.html          # Dashboard
│   ├── sites.html          # SSL site monitoring table
│   ├── add_site.html
│   ├── certs.html          # Cert Reader + Matcher + Generator (tabbed)
│   ├── crypto.html         # AES + Base64 + Password Gen (tabbed)
│   ├── network.html        # Ping + Port Scanner (tabbed)
│   ├── vault.html
│   ├── json_converter.html
│   └── errors/             # 400, 403, 404, 429, 500
│
└── logs/                   # Rotating log files (auto-created)
```

---

## Quick Start (Development)

```bash
# 1. Clone and enter the directory
cd OpsSecure-Suite

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY at minimum

# 5. Run
python app_run.py
```

Visit http://localhost:5000

**Default credentials** (change immediately):

| Username | Password   | Role   |
|----------|------------|--------|
| admin    | admin@123  | admin  |
| viewer   | viewer@123 | viewer |

---

## Production — Docker

```bash
cp .env.example .env
# Edit .env with real values

mkdir -p data logs
docker-compose up -d
```

## Production — Bare server (gunicorn)

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in values

mkdir -p logs
gunicorn -c gunicorn.conf.py "run:app"
```

---

## Module Details

### SSL Monitoring
- Tracks certificate expiry for all registered sites
- Background scans every 5 minutes via `scanner.py`
- Email alerts at configurable day milestones: 30, 20, 15, 10, 8, 6, 4, 3, 2, 1 days
- Supports internal/private domains via IP override
- Per-site malware / security header scan

### SSL Certificate Tools — `certs.html` *(3 tabs)*

**Cert Reader**
- Upload `.pem`, `.crt`, `.cer`, `.der` certificates
- Displays: Common Name, Issuer, Valid From, Expiry, Days Left, Serial Number, Version, Subject Alt Names (SAN)

**Cert Matcher**
- Upload a certificate and its private key
- Verifies they belong to the same key pair
- Accepts `.pem`, `.crt`, `.cer`, `.der` for cert and `.key`, `.pem` for key

**Generate Cert**
- Generate a self-signed RSA certificate entirely server-side
- Configurable fields: Common Name, Organization, Country, State, Locality
- Validity: 90 / 180 / 365 / 730 / 1825 days
- Key size: 2048-bit or 4096-bit
- Subject Alternative Names: DNS names and IP addresses (auto-detected)
- Download as `cert.pem`, `private.key`, or a ZIP bundle containing both
- Private keys are never stored — generated in memory and returned immediately

### Crypto Tools — `crypto.html` *(3 tabs)*

**AES Encrypt / Decrypt**
- Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256)
- Auto key generation or bring your own key
- Copy output or save as file

**Base64**
- Encode plain text to Base64
- Decode Base64 back to plain text

**Password Generator**
- Cryptographically random password generation (`crypto.getRandomValues`)
- Length slider: 8–64 characters
- Character set options: Uppercase, Lowercase, Numbers, Symbols
- Real-time strength meter (Very Weak → Very Strong)

### Network Tools — `network.html` *(2 tabs)*

**Ping**
- TCP connect-based ping (ports 80 → 443 → 22)
- Configurable packet count: 4, 8, or 16
- Per-packet latency display with color coding (green/yellow/red)
- Bar chart visualization + min/avg/max/loss summary


**Port Scanner**
- Concurrent TCP scan using Python `ThreadPoolExecutor` (50 workers)
- Built-in presets: Common ports, Web services, Databases, Mail services
- Custom port range (up to 200 ports)
- Service name detection for 25+ well-known ports
- Results show Open / Filtered status with animated progress bar

### Converters — `json_converter.html`
- JSON ↔ YAML bidirectional conversion
- Excel ↔ JSON bidirectional conversion
- Pretty-formatted output with copy and download

### Secret Vault — `vault.html`
- Store named secrets encrypted with AES (Fernet)
- Admin-controlled: add and delete secrets
- Secrets are encrypted at rest in the database

---


## Security Notes

- `SECRET_KEY` **must** be a long random value in production — never use the default.
- Default user passwords **must** be changed before going live.
- Rate limiting is applied to the login endpoint (10 req/min) and all API endpoints.
- CSRF tokens are present on all forms and injected automatically into all `fetch()` calls via the global override in `base.html`.
- Security headers (X-Frame-Options, CSP, etc.) are set on every response.
- File uploads are validated by extension before processing.
- `verify=True` is enforced on all outbound TLS connections; self-signed/internal CAs fall back to unverified with a warning banner.
- No credentials or internal addresses are hardcoded — everything is configured via `.env`.
- Self-signed certificate generation is entirely server-side and in-memory; private keys are never written to disk or stored in the database.

---

## Changing Default Passwords

Log in as admin, then run from a Python shell:

```python
from modules.db import get_connection
from werkzeug.security import generate_password_hash

conn = get_connection()
conn.execute("UPDATE users SET password=? WHERE username=?",
             (generate_password_hash("your-new-password"), "admin"))
conn.commit()
conn.close()
```

---

## Requirements

Key dependencies (see `requirements.txt` for full list):

```
flask
flask-login
flask-wtf
cryptography        # cert parsing, generation, AES encryption
schedule            # background SSL scanner
openpyxl            # Excel conversion
pyyaml              # YAML conversion
gunicorn            # production WSGI server
```