# Deploying contact-service

The static site is on GitHub Pages; the contact form POSTs to this service at
`https://spacelift-demo-contact.kontango.net/contact`. Until the service is
running behind that name, the form validates client-side but submissions fail
with a "couldn't reach the contact service" message. This is the runbook to make
it live.

> **Current state (2026-07-20):** the public name resolves to the OPNsense Caddy
> ingress, which is answering with a **placeholder vhost** (any `GET` → 200,
> `POST`/`OPTIONS` → 405, no CORS headers). That 405-with-no-CORS is exactly what
> shows up in the browser as a network/CORS error. The fix below replaces that
> placeholder with a route to this service.

## 1. Run the service on an LXC

Pick an LXC that runs the schmutz agent (so `/run/bao-token` exists). Build a
static binary and install it with the systemd unit.

```bash
# on a build box with Go 1.25:
cd contact-service
CGO_ENABLED=0 go build -ldflags="-s -w" -o contact-service .

# copy to the LXC (scp to /tmp then install — never scp onto the final path):
scp contact-service root@<lxc>:/tmp/
ssh root@<lxc> 'install -m0755 /tmp/contact-service /usr/local/bin/contact-service'

# config: non-secret env + the unit (secrets come from Bao at runtime)
scp contact-service.env.example root@<lxc>:/tmp/
scp contact-service.service     root@<lxc>:/tmp/
ssh root@<lxc> '
  install -m0644 /tmp/contact-service.env.example /etc/contact-service.env
  install -m0644 /tmp/contact-service.service /etc/systemd/system/contact-service.service
  systemctl daemon-reload
  systemctl enable --now contact-service
  systemctl --no-pager status contact-service | head -5
'
```

`/etc/contact-service.env` must set the CORS origin to **only** the Pages site,
so no other origin can drive the form:

```ini
LISTEN_ADDR=:8080
ALLOWED_ORIGIN=https://dkontango.github.io
FROM_ADDR=no-reply@kontango.io
FROM_NAME=Kontango — Spacelift GitOps Demo
ADMIN_ADDR=admin@kontango.us
BAO_ADDR=https://secrets.kontango.net
BAO_NAMESPACE=kontango
SMTP_SECRET_PATH=secret/data/shared/purelymail
```

The unit sets `BAO_TOKEN_FILE=/run/bao-token` (the agent-maintained token) — no
secret is written to disk or into the unit.

Verify locally on the LXC:

```bash
curl -s localhost:8080/healthz         # -> ok
curl -s -X POST localhost:8080/contact -H 'Content-Type: application/json' -d '{"email":"bad"}'
# -> {"error":"that doesn't look like a valid email address"}
```

## 2. Route the public name through the OPNsense Caddy ingress

Replace the placeholder vhost for `spacelift-demo-contact.kontango.net` with a
reverse-proxy to the LXC. In the OPNsense Caddy config (or a site snippet):

```caddyfile
spacelift-demo-contact.kontango.net {
    encode zstd gzip
    reverse_proxy <lxc-overlay-name>.tango:8080
    # The service sets its own tight CORS (ALLOWED_ORIGIN); Caddy just proxies.
}
```

Use the LXC's **overlay name** (`<node>.tango`), not a raw LAN IP, per the
org's DNS/endpoint conventions. Reload Caddy, then verify from outside:

```bash
# CORS preflight should now succeed with the Pages origin, not 405:
curl -s -i -X OPTIONS https://spacelift-demo-contact.kontango.net/contact \
  -H 'Origin: https://dkontango.github.io' \
  -H 'Access-Control-Request-Method: POST' | head -5
# -> HTTP/2 204, access-control-allow-origin: https://dkontango.github.io

curl -s https://spacelift-demo-contact.kontango.net/healthz    # -> ok
```

## 3. Confirm end to end

Open the live site, submit the contact form with a real address, and confirm:
- the form shows the green "a confirmation email is on its way" status,
- the submitter receives the thank-you email,
- `admin@kontango.us` receives the "New contact submission" copy.

## Changing the endpoint host

If the service lives at a different name, rebuild the site with it baked in:

```bash
CONTACT_ENDPOINT=https://<host>/contact python3 site/build.py
```
and set `ALLOWED_ORIGIN` on the service to the exact published site origin.

## Security notes

- **CORS is the gate:** `ALLOWED_ORIGIN=https://dkontango.github.io` means only
  the Pages site's JS can drive the form from a browser. (CORS is not a hard
  server-side auth boundary — a non-browser client can still POST — which is why
  the service also rate-limits per IP, caps the body, runs a honeypot, and
  validates + MX-checks the address before sending.)
- **No secrets on the host:** SMTP credentials are read from Bao at startup via
  the agent token; nothing sensitive is in the env file, the unit, or the image.
- **Never expose the raw `:8080` publicly** — only via the Caddy ingress.
