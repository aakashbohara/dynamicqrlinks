# ⚡ Dynamic QR Links

Create short links with **dynamic QR codes** — update the destination URL anytime without changing the QR code or short link.

Perfect for printed materials, marketing campaigns, and menus where you need to change the link target after printing.

## Features

- 🔗 **Short Links** — clean `yourdomain.com/code` URLs
- 📱 **QR Code Generation** — auto-generated for every link, downloadable as PNG
- ✏️ **Dynamic Destinations** — update where a link points without changing the QR
- 📊 **Click Tracking** — see how many times each link has been visited
- 🔍 **Search & Filter** — find links quickly in the dashboard
- 🗑️ **Delete Links** — remove links you no longer need
- 📄 **Pagination** — handles large numbers of links efficiently
- 🌙 **Dark Mode** — automatic based on system preference
- 📱 **Mobile Responsive** — works great on all devices
- 🔒 **Auth** — JWT-based admin authentication

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn |
| Database | PostgreSQL + SQLAlchemy |
| Auth | JWT (python-jose) |
| QR Codes | qrcode + Pillow |
| Frontend | Vanilla HTML/CSS/JS |

## Quick Start (Development)

```bash
# 1. Clone
git clone https://github.com/aakashbohara/dynamicqrlinks.git
cd dynamicqrlinks

# 2. Virtual environment
python -m venv env
env\Scripts\Activate   # Windows
# source env/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
copy .env.example .env
# Edit .env with your database URL and credentials

# 5. Run
cd app
uvicorn main:app --reload
```

Open http://127.0.0.1:8000 and sign in with your admin credentials.

## Production Deployment (GCE Free Tier)

Deploy on a Google Compute Engine **e2-micro** instance (Always Free = $0/month):

```bash
# On the GCE instance:
git clone https://github.com/aakashbohara/dynamicqrlinks.git
cd dynamicqrlinks
chmod +x deploy.sh
sudo ./deploy.sh
```

The script will:
1. Install PostgreSQL, Python, Nginx
2. Create the database and user
3. Set up a Python venv with all dependencies
4. Generate `.env` with secure random secrets
5. Create a systemd service for auto-start
6. Configure Nginx as a reverse proxy

After deployment, get HTTPS:
```bash
sudo certbot --nginx -d yourdomain.com
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/login` | No | Get JWT token |
| POST | `/create` | Yes | Create a short link |
| GET | `/links?skip=0&limit=50` | Yes | List links (paginated) |
| PATCH | `/update/{code}` | Yes | Update target URL |
| DELETE | `/delete/{code}` | Yes | Delete a link |
| GET | `/qr/{code}` | No | Get QR code (base64) |
| GET | `/{code}` | No | Redirect to target |
| GET | `/health` | No | Health check |

## Environment Variables

See [`.env.example`](.env.example) for all available options.

## License

MIT
