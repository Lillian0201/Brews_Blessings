# Brews & Blessings

## Run the local backend on Windows

The frontend calls the FastAPI backend at `http://127.0.0.1:5001/api`. Keep the
API terminal running while using the app.

1. Install Python 3.10+ and PostgreSQL.
2. Create `backend/.env` with the local database settings:

   ```dotenv
   DB_HOST=127.0.0.1
   DB_PORT=5432
   DB_NAME=brews_blessings
   DB_USER=postgres
   DB_PASSWORD=your_local_postgres_password
   DB_ADMIN_NAME=postgres

   # Optional local development settings.
   BB_OWNER_PASSWORD=owner123
   BB_BARISTA_PASSWORD=barista123
   BB_AUTO_BOOTSTRAP=true
   BB_SEED_SAMPLE_DATA=true
   ```

   `.env` is ignored by Git. Replace the example database password and set
   private account passwords on your device.

3. Create a virtual environment and install dependencies:

   ```powershell
   cd "<project folder>\backend"
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

4. Start the API:

   ```powershell
   python main.py
   ```

   Startup automatically creates the configured database when needed, applies
   SQL migrations once, and seeds products, owner/barista accounts, and optional
   sample transactions. Set `BB_AUTO_BOOTSTRAP=false` to disable startup setup.
   Set `BB_SEED_SAMPLE_DATA=false` to skip sample transactions.

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
