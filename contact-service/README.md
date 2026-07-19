# contact-service

The backend behind the guide's **Contact us** form. A static site (GitHub Pages
/ S3) can't send email or hold SMTP credentials, so the form POSTs to this small
Go service, which validates the address and relays a real thank-you email
through our own SMTP.

```
browser form ──POST /contact──▶ contact-service ──SMTP──▶ Purelymail ──▶ submitter's inbox
                                    │
                                    └─ SMTP creds read from OpenBao at startup (never in the browser)
```

## What it does

- `POST /contact` `{ "email": "...", "name": "...", "message": "..." }`
  1. **Validates** the email — RFC-ish format **and** a DNS **MX** lookup on the
     domain (falls back to A/AAAA), so we only accept addresses at a domain that
     can actually receive mail. The browser does the same format check inline.
  2. **Sends** a plain-text thank-you confirmation to that address via
     `mailserver.purelymail.com:587` (STARTTLS + auth).
  3 Returns `{ "status": "sent", "message": "..." }`, or a `4xx/5xx` with an
    `error` the form displays.
- `GET /healthz` → `ok`.
- **Anti-abuse:** a hidden honeypot field, per-IP rate limiting (5/min), a 16 KB
  body cap, and header-injection sanitization on the name field.

## Config

Secrets are **read from Bao at startup** — never on disk, never in the browser.
Everything else is env (`contact-service.env.example`):

| Env | Purpose |
|-----|---------|
| `LISTEN_ADDR` | bind address (default `:8080`) |
| `ALLOWED_ORIGIN` | the one site origin allowed to POST (CORS) |
| `FROM_ADDR` / `FROM_NAME` | thank-you From identity (a Purelymail-domain address) |
| `BAO_ADDR` / `BAO_NAMESPACE` | OpenBao address + namespace |
| `BAO_TOKEN_FILE` | path to the agent-maintained token (`/run/bao-token`) — or `BAO_TOKEN` inline |
| `SMTP_SECRET_PATH` | KV v2 data path, default `secret/data/shared/purelymail` (keys: `smtp_host/port/user/password`) |

## Run

```bash
# local (token inline)
BAO_ADDR=https://secrets.kontango.net BAO_NAMESPACE=kontango \
BAO_TOKEN=$(bao print token) \
FROM_ADDR=no-reply@kontango.io ALLOWED_ORIGIN='*' LISTEN_ADDR=:8099 \
go run .

# container
docker build -t contact-service .
docker run -p 8080:8080 --env-file /etc/contact-service.env \
  -e BAO_TOKEN=$(bao print token) contact-service

# systemd on a schmutz-agent host (token via /run/bao-token)
install -m0755 contact-service /usr/local/bin/
install -m0644 contact-service.env.example /etc/contact-service.env   # then edit
install -m0644 contact-service.service /etc/systemd/system/
systemctl enable --now contact-service
```

## Publishing the endpoint

The form's endpoint is baked into `index.html` at build time from
`CONTACT_ENDPOINT` (default `https://spacelift-demo-contact.kontango.net/contact`).
Expose the service on that public HTTPS name via the OPNsense Caddy ingress (the
same `*.kontango.*` DNS-anchor path the rest of the stack uses) and set
`ALLOWED_ORIGIN` to the published site origin so CORS is tight. Rebuild the site
after changing the endpoint:

```bash
CONTACT_ENDPOINT=https://<host>/contact python3 site/build.py
```

> **Never expose an internal port publicly** without going through the ingress —
> route it through Caddy/Ziti, not a raw port.
