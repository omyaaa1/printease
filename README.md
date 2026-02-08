# Printease

A minimalist, dark-mode print-order web app with tracking and admin status updates. Built to keep the flow fast for students and print shops: upload, estimate, submit, track.

## Live Demo
`https://printease-repo.vercel.app`

## Why This Exists
Print ordering is usually slow and messy: uploads are scattered, totals are unclear, and customers can’t track progress. Printease was created to fix that with a single clean flow and a lightweight backend that can run anywhere.

## How It Works
- The user fills details, selects print options, uploads files, and sets copies/pages per file.
- The backend calculates totals and generates a tracking code.
- The order is saved in SQLite with status set to `Pending`.
- Admins update status in the dashboard; users track by code or phone/email.

## Key Features
- Multi-file uploads with per-file copies/pages
- Instant price estimate
- Tracking codes and order status
- Admin dashboard with search, CSV export, and status updates
- Minimalist dark UI with zero rounded corners

## Challenges Solved
- Reliable file handling with safe filenames and clean downloads
- Consistent pricing across frontend and backend
- Status + tracking added without breaking existing data via a migration step
- Vercel serverless support (ephemeral storage handled with temp paths)

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
- Vercel’s filesystem is ephemeral. SQLite data resets on cold starts.
- For production persistence, use a managed database and update `DB_NAME` in `PRINT.apk/backendlogic.py`.
