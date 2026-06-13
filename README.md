# 🌍 Geo-Presenze

**Location + face recognition attendance system built with Streamlit.**

Students mark attendance by taking a selfie and allowing GPS access.
The system verifies their face against a registered photo and checks
that they are physically within the campus geo-fence.

---

## Project structure

```
geo-presenze/
├── Home.py                 ← Streamlit entry point
├── pages/
│   ├── 1_Scan.py           ← Student attendance scan page
│   ├── 2_Dashboard.py      ← Admin records & charts
│   └── 3_Admin.py          ← Register students, sessions, geo-fence test
├── db/
│   ├── database.py         ← SQLAlchemy engine + session factory
│   └── models.py           ← Student, SessionModel, Attendance tables
├── services/
│   ├── geo.py              ← Haversine geo-fence check (geopy)
│   └── face.py             ← Face verification (DeepFace, lazy-loaded)
├── static/faces/           ← Stored student face photos (gitignored)
├── .streamlit/
│   ├── config.toml         ← Theme + server settings
│   └── secrets.toml.example ← Template for your secrets
├── requirements.txt
└── .gitignore
```

---

## Quick start (local)

```bash
# 1. Clone / unzip the project
cd geo-presenze

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies  (first run takes 5–10 min — DeepFace is large)
pip install -r requirements.txt

# 4. Set up secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml and set a real SECRET_KEY

# 5. Run
streamlit run Home.py
# Opens at http://localhost:8501
```

> **Camera and GPS require HTTPS.**
> For local HTTPS testing, use ngrok:
> ```bash
> ngrok http 8501
> ```
> Then open the `https://` ngrok URL on your phone.

---

## Deployment — Streamlit Community Cloud (free, forever)

1. Push this project to a GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select your repo, branch `main`, and main file `Home.py`.
4. Under **Advanced settings → Secrets**, paste the contents of `secrets.toml`.
5. Click **Deploy** — your app will be live at `your-app.streamlit.app`.

---

## First-time setup after deploy

1. Open `<your-url>/Admin` (or use the Admin page in the sidebar).
2. **Register student tab**: enter a student ID, name, and upload a face photo.
3. **Create session tab**: enter your course code, start/end times, and your
   campus GPS coordinates (right-click on Google Maps → "What's here?").
4. Note the **Session ID** shown after creation — students need this.
5. Open `<your-url>/Scan` on your phone and test a check-in.

---

## Important notes

### SQLite vs PostgreSQL
The default database is SQLite (`presenze.db`).
**SQLite is wiped on every Streamlit Cloud redeploy.**
For persistent data, use a free PostgreSQL database:

- [Supabase](https://supabase.com) — free 500 MB PostgreSQL
- [Neon](https://neon.tech) — free 512 MB serverless PostgreSQL

Update `DATABASE_URL` in your secrets to the PostgreSQL connection string.
No code changes needed — SQLAlchemy handles both databases identically.

### Face photos
`static/faces/` is listed in `.gitignore` — student photos are never
pushed to GitHub. On Streamlit Cloud, re-upload photos via the Admin
page after each deploy (or use a persistent volume / object storage).

### DeepFace model weights
DeepFace downloads ~500 MB of model weights on first use.
On Streamlit Cloud this happens automatically during the first
face verification request — expect a 30–60 second delay the first time.

### GPS in browsers
Camera and GPS only work on HTTPS. Streamlit Cloud provides HTTPS
automatically. For local testing, use ngrok (see above).

---

## Tech stack

| Component | Library |
|---|---|
| Web framework | Streamlit |
| Face recognition | DeepFace (Facenet512 model) |
| Face detection | RetinaFace |
| Geolocation | geopy (Haversine formula) |
| Database ORM | SQLAlchemy |
| Database | SQLite (dev) / PostgreSQL (prod) |
| GPS capture | Browser `navigator.geolocation` via HTML component |
| Camera capture | `st.camera_input()` |
