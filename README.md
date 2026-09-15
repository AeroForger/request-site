# AeroForger

A responsive, dark developer portfolio with a private project-request API. Plain HTML, CSS, and JavaScript; Python standard-library WSGI backend. No frontend framework, remote fonts, or runtime package dependencies for local development.

## Run locally

Requires Python 3.10+.

```sh
cp .env.example .env
python -m server.app
```

Open http://localhost:3000. The portfolio works immediately. Email submissions return a useful 503 error until email credentials are configured; they never report fake success.

Optional development and production tooling:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

## Email configuration

1. Create a Resend API key with sending permission and verify your sender domain.
2. Set `RESEND_API_KEY` in `.env` or your host's secret environment settings.
3. Set `MAIL_FROM` to an address on that verified domain, e.g. `AeroForger <requests@your-domain.com>`.
4. Set `REQUEST_TO=AeroForgery@proton.me` server-side.
5. Set `SITE_ORIGIN` to the exact public origin, e.g. `https://your-domain.com` (no trailing slash).

The mail adapter is `server/mail.py`, using the [Resend send-email API](https://resend.com/docs/api-reference/emails/send-email). Only the configured sender and recipient are used. The visitor email becomes Reply-To. Message bodies are plain text. Credentials and destination addresses are never included in public assets. Never commit `.env`.

## Content

Edit all project descriptions, technology lists, status, and repository URLs in `public/projects.js`. Unknown fields are `null` or empty arrays and are omitted from the page. The project illustrations are abstract artwork, not claims about features. Edit identity and skills in `public/index.html`, shared typography, spacing, and icon tokens in `public/styles.css`, and replace `public/favicon.svg` if desired.

### Fonts and visual scale

The site self-hosts Latin-subset WOFF2 versions of Adwaita Sans (variable weight) and Adwaita Mono (regular), with `font-display: swap`. Their SIL Open Font License is included in `public/fonts/LICENSE.txt`. No external font service is required. Primary headings use responsive `clamp()` sizes; content and controls share a readable type scale. UI icons use 16 px, note icons 20 px, skill icons 24 px, and the brand mark 32 px. Project artwork retains its shared 150 × 110 px canvas.

## Request API

`POST /api/requests` with `Content-Type: application/json`:

```json
{
  "type": "desktop",
  "name": "Example App",
  "description": "A desktop application to organize and search my local files.",
  "budget": "Optional",
  "email": "client@example.com"
}
```

Types: `cli`, `desktop`, `web`, `embedded`, `library`, `other`. Names must contain 2–100 characters; descriptions 30–5,000; budget up to 100; email up to 254 and valid format. Optional `website` is an empty honeypot field. Unknown keys, invalid types, header/control-character injection, and nonempty honeypots are rejected. The maximum JSON body is 24,000 bytes. Same-origin browser checks and a five-attempts-per-IP-per-15-minutes limiter add basic spam protection.

Responses are JSON: 201 provider accepted, 400 invalid body/fields, 403 wrong origin, 405 incorrect method, 413 oversized body, 415 incorrect content type, 429 rate limited (Retry-After included), 503 email unavailable. A 201 means the provider accepted the email, not guaranteed inbox delivery. Temporary errors preserve form contents; double clicks are disabled while sending. Requests are not stored in a database and request bodies are not logged.

## Checks and build

```sh
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
python scripts/format_frontend.py --check
python scripts/build.py
```

For formatting: `ruff format .` and `python scripts/format_frontend.py`. The build copies self-contained frontend assets into `dist/`. Once built, the server serves `dist/`; rebuild after frontend changes, or remove `dist/` to serve `public/` directly.

## Production deployment

Upload this project to a Python host, set the environment variables, install `requirements.txt`, run the build, and start:

```sh
gunicorn server.app:application --bind 127.0.0.1:3000 --workers 1 --threads 4 --timeout 30 --limit-request-line 4094
```

Put an HTTPS reverse proxy in front of Gunicorn. Set its request-body limit to 24 KB, request/read timeout to 20 seconds, and enable HSTS once HTTPS is working. Route both static pages and `/api/requests` to the application. The local development server is not intended for production.

The bounded, thread-safe rate limiter is in memory: use one worker as shown, and note that restarting clears it. Behind a reverse proxy, the app deliberately ignores untrusted forwarding headers, so the app limit may be shared by all visitors. Configure a trusted edge/proxy per-client rate limit and a trusted client-IP integration before public deployment; replace the in-memory limiter with a shared store before adding workers/replicas. Basic honeypot protection is not a CAPTCHA; add a server-verified challenge if traffic requires it.

No email credentials are bundled. Test delivery with your configured provider before publishing.
