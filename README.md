# Printease

Minimal, dark-mode print-order web app with tracking and admin status updates.

## Live Demo
`https://printease-repo.vercel.app`

## Features
- Multi-file uploads with per-file copies and pages
- Instant price estimate
- Tracking code for orders
- Admin dashboard with status updates and CSV export
- Minimalist dark UI with zero rounded corners

## Local Run
```powershell
cd C:\Users\butem\Desktop\CODES\printease-repo\PRINT.apk
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python backendlogic.py
```
Open `http://127.0.0.1:5000`.

## Deploy (Vercel)
```powershell
cd C:\Users\butem\Desktop\CODES\printease-repo
vercel --prod --yes
```

## Notes
- Vercel serverless filesystem is ephemeral. SQLite data resets on cold starts.
- For production persistence, use a managed database (PostgreSQL/SQLite hosted) and update `DB_NAME` accordingly.
