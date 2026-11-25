# Brews & Blessings

Brews & Blessings uses a static HTML/CSS/JavaScript frontend and a modular
FastAPI backend backed by PostgreSQL. The frontend calls `/api` on the deployed
site; local browser development calls the API on `127.0.0.1:5001`.

## Local development

1. Install Python 3.10+ and PostgreSQL. Create `backend/.env` with local
   database settings:

   ```dotenv
   DB_HOST=127.0.0.1
   DB_PORT=5432
   DB_NAME=brews_blessings
   DB_USER=postgres
   DB_PASSWORD=your_local_postgres_password
   DB_ADMIN_NAME=postgres
   BB_OWNER_PASSWORD=owner123
   BB_BARISTA_PASSWORD=barista123
   BB_COOKIE_SECURE=false
   BB_AUTO_BOOTSTRAP=true
   BB_SEED_SAMPLE_DATA=true
   ```

   `.env` is ignored by Git. Use private passwords on any non-local system.

2. In a terminal, install dependencies and start the API:

   ```powershell
   cd "<project folder>\backend"
   uv sync
   uv run python main.py
   ```

   The local API applies schema migrations and seeds products, users, and
   optional sample transactions at startup.

3. In a second terminal, serve the frontend instead of opening the HTML files
   directly. This lets the browser use the session cookie correctly:

   ```powershell
   cd "<project folder>"
   py -m http.server 5500 --bind 127.0.0.1
   ```

   Open `http://127.0.0.1:5500/`. The root page redirects to the login page.
   The API health check is `http://127.0.0.1:5001/api/health`.

## Docker

The backend image uses the pinned `uv.lock` dependencies and listens on the
port supplied through `PORT` (80 by default, matching Vercel's container
runtime). From `backend/`:

```powershell
docker build -t brews-blessings-api .
docker run --rm -p 5001:80 --env-file .env -e BB_COOKIE_SECURE=false brews-blessings-api
```

For a local PostgreSQL database outside Docker, use `host.docker.internal` for
`DB_HOST`. A Supabase `DATABASE_URL` can also be supplied to the container.

## Vercel + Supabase deployment

`vercel.json` defines two Vercel Services: a static frontend build and a
containerized FastAPI backend. Vercel routes `/api/*` to the backend and all
other paths to the frontend. Vercel Services are currently a Beta feature; the
container runs as a stateless, autoscaling web service, not a persistent Docker
host.

1. Import this repository into Vercel and enable Vercel Services for the
   project. Keep the project root at this repository's root.
2. In Vercel's production environment variables, set:

   - `DATABASE_URL`: the Supabase **transaction-pooler** PostgreSQL URL. Do not
     commit it or use a direct database URL for the serverless app.
   - `BB_AUTO_BOOTSTRAP=false`: schema changes must be applied separately;
     startup bootstrap uses session-level advisory locks.
   - `BB_COOKIE_SECURE=true`: require HTTPS for the authentication cookie.
   - Optionally set `BB_SESSION_TTL_HOURS` (defaults to `8`).

   Same-origin frontend/API requests do not need a production CORS allowlist.
   If you later host the frontend on a different origin, set
   `BB_CORS_ORIGINS` to the exact comma-separated frontend origins.

3. Apply the schema and existing migrations to a new Supabase database in this
   order: `backend/schema.sql`, then
   `backend/migrations/001_transactions.sql`,
   `backend/migrations/002_inventory_pos.sql`,
   `backend/migrations/003_auth_sessions.sql`,
   `backend/migrations/003_pos_catalog_prices.sql`, and
   `backend/migrations/004_default_grandeur_price.sql`. For an existing
   database, apply whichever of these migrations are not already recorded as
   applied: auth sessions are required for login, and the POS catalog
   migrations are required by the current product/POS API.
4. For a new database, run `backend/seed_products.sql` in Supabase's SQL
   Editor. Create initial accounts from a trusted machine: set `DATABASE_URL`,
   `BB_OWNER_PASSWORD`, and `BB_BARISTA_PASSWORD` as environment variables,
   then run `uv run python seed_users.py` from `backend/`. Use strong, unique
   passwords; never use the local example passwords in a public deployment.
5. Deploy the repository from Vercel. Verify `/api/health`, then sign in at the
   deployment's root URL. The login API creates a revocable PostgreSQL session
   and returns it in an HttpOnly, Secure, SameSite=Strict cookie. The browser
   never sends a user identity header; each protected API request validates the
   session and current account status in PostgreSQL.

## API tests

With the backend running and seeded accounts available, run:

```powershell
cd "<project folder>\backend"
$env:BB_OWNER_PASSWORD = "your-owner-password"
$env:BB_BARISTA_PASSWORD = "your-barista-password"
uv run python api_tests.py
```

The test runner logs in with these accounts and reuses their session cookies.
