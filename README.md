# Brews & Blessings

## Run the local backend on Windows

The frontend calls the Flask API at `http://127.0.0.1:5001/api`. Keep the API
terminal running while using the app.

1. Install Python 3.10+ and PostgreSQL. Create a PostgreSQL database for the
   project (for example, `brews_blessings`).
2. In pgAdmin's Query Tool, connected to that database, run these files in
   order:
   - `backend/schema.sql`
   - `backend/migrations/001_transactions.sql`
   - `backend/migrations/002_inventory_pos.sql`
3. In PowerShell, create the local Python environment and install dependencies:

   ```powershell
   cd "<project folder>\backend"
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

4. Create `backend/.env` with the credentials for your local PostgreSQL database:

   ```dotenv
   DB_HOST=127.0.0.1
   DB_PORT=5432
   DB_NAME=brews_blessings
   DB_USER=postgres
   DB_PASSWORD=your_local_postgres_password
   # Optional; change these before using outside local development.
   BB_OWNER_PASSWORD=owner123
   BB_BARISTA_PASSWORD=barista123
   ```

   `.env` is ignored by Git. Replace the example database password and set
   private account passwords on your device.
5. From the `backend` folder, seed the sample products and local accounts:

   ```powershell
   psql -U postgres -d brews_blessings -f seed_products.sql
   python seed_users.py
   ```

   To load sample sales as well, run `psql -U postgres -d brews_blessings -f
   seed_transactions.sql` before `python seed_users.py`. That sample script
   inserts placeholder passwords; `seed_users.py` replaces them with hashes.
   Running `seed_users.py` resets the local `owner` and `barista` passwords to
   the values in `.env` (or the development defaults shown above).
6. Start the API:

   ```powershell
   python app.py
   ```

   Open `http://127.0.0.1:5001/api/health`; it should return `{"status":"ok"}`.
   Open the frontend by launching `Login Page/Login.html` in a browser and sign
   in with the local account you seeded.

## Current API coverage

Login, Settings, Expense, and Transactions pages call the Flask API. POS,
Inventory, and Dashboard currently keep their data in browser storage, even
though backend endpoints for those modules are present. Those screens need
frontend integration before their data is shared with PostgreSQL.

The API currently identifies requests with an `X-Username` header. This is
adequate only for local development; it is not secure authentication for a
public deployment.
