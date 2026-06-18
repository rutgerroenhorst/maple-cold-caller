# Maple Cold Caller Match Engine

Python/Tornado app for recruiting cold callers. SQLite database, no build step required.

---

## Local Development

```bash
cd ~/Documents/maple-cold-caller
bash start.sh          # runs on http://localhost:8888
```

To use AI features, set your Anthropic API key first:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
bash start.sh
```

---

## Deploy to Render

### 1. Push to GitHub

```bash
cd ~/Documents/maple-cold-caller
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/maple-cold-caller.git
git push -u origin main
```

### 2. Create a new Web Service on Render

1. Go to [render.com](https://render.com) → **New → Web Service**
2. Connect your GitHub repo
3. Render will detect `render.yaml` automatically and pre-fill:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python3 app.py --port=$PORT`

### 3. Add environment variables

In the Render dashboard under **Environment**:

| Key | Value |
|-----|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (your key) |
| `DB_PATH` | `/data/maple_cold_caller.db` |

> `DB_PATH` is already set in `render.yaml`. Only `ANTHROPIC_API_KEY` needs to be added manually (it's secret).

### 4. Add a Persistent Disk

The SQLite database must survive deploys:

1. In your Render service → **Disks → Add Disk**
2. Set **Mount Path** to `/data`
3. Set **Size** to `1 GB` (free tier: 1 GB included)

> Without the disk, data resets on every deploy.

### 5. Deploy

Click **Deploy**. Render installs deps, starts the app, and gives you a public URL like `https://maple-cold-caller.onrender.com`.

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8888` | Set automatically by Render |
| `DB_PATH` | `./maple_cold_caller.db` | SQLite file path |
| `ANTHROPIC_API_KEY` | *(unset)* | Required for AI scoring/outreach features |

AI features degrade gracefully when the key is missing — the app still runs, AI buttons just return a clear error message.
