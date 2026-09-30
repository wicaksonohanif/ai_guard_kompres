AI Guard dashboard patch

Copy these files over the matching files in your existing C:\laragon\www\ai guard project.
Do NOT replace your .env or data/ai_guard.db.

Changes:
- Dashboard separates authentication result from security detection.
- Shows Detection, Attack Type, Severity, and Explanation.
- Login attempts are linked to the AI Guard traffic log, so an invalid_username can still show XSS/SQL Injection/etc. when the request itself was detected as an attack.
- Adds attack count KPI.
- Telegram single-alert message includes severity.
- Adds python-dotenv to website requirements.
- .env.example is only a template; do not put real tokens in it.

After copying:
1. venv\\Scripts\\activate
2. pip install -r requirements-website.txt
3. Restart inference API and Flask website.
4. Log in to admin and test an XSS/SQLi request.
