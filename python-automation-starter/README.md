# Python Automation Starter — NASA APOD Fetcher

This starter project shows how to build and ship a simple **automation script**.  
It uses the public NASA APOD API to download today's Astronomy Picture of the Day (image + metadata)
into the `output/` folder. You can run it manually or schedule it to run every day.

> Why this? It's a safe, legal demo that proves the full workflow you'll reuse for client work:
> config ➜ fetch data ➜ save files ➜ logs ➜ (optional) schedule.

---

## 🚀 What you get
- `main.py` — the script you run
- `config.example.json` — copy this to `config.json` and edit your settings
- `requirements.txt` — libraries to install
- `utils/logger.py` — tiny logging helper
- `output/` — where files are saved

---

## 🧰 Setup (once)
1. **Install Python** (3.9+ recommended): https://www.python.org/downloads/
2. **Open a terminal** in this folder (the project folder).
3. Install libraries:
   ```bash
   pip install -r requirements.txt
   ```
4. Make your config:
   ```bash
   copy config.example.json config.json   # Windows (PowerShell: cp config.example.json config.json)
   cp config.example.json config.json     # macOS / Linux
   ```
5. (Optional) Get a free NASA API key: https://api.nasa.gov/  
   You can use `"DEMO_KEY"` to start (limited rate).

Edit `config.json` as needed.

---

## ▶️ Run it
```bash
python main.py
```
It will fetch today's APOD, save the image (if available) and metadata JSON into `output/`.

---

## ⏰ Schedule it (run daily automatically)
**Windows (Task Scheduler):**
1. Open *Task Scheduler* → *Create Basic Task…*
2. Trigger: *Daily* (choose time)
3. Action: *Start a Program*
4. Program/script: `python`
5. Add arguments: `main.py`
6. Start in: the **full path** to this folder

**macOS / Linux (cron):**
1. Find your Python path: `which python` (or `which python3`)
2. Edit cron: `crontab -e`
3. Add a daily entry at 8:00 AM:
   ```
   0 8 * * * /usr/bin/python3 /full/path/to/main.py >> /full/path/to/output/cron.log 2>&1
   ```

---

## 🧪 Customize for clients
Replace the NASA fetch step with:
- Calling a public API your client uses
- Reading a CSV/Excel, cleaning data, exporting a report
- Hitting a SaaS API and generating a PDF summary

Keep the **structure**, swap the **task**. That's it.

---

## 📦 Hand-off to a client
- Zip this folder or push it to a private GitHub repo
- Include your `README.md` and (optionally) a short Loom video showing how to run it
- Never include secrets in your repo; keep them only in `config.json` (gitignored by default in real projects)

---

## ❓ FAQ
- **Do I need a NASA key?** You can start with `DEMO_KEY`, but it's rate-limited. Get your own free key for reliability.
- **Where are files saved?** In `output/` (create this folder if it doesn't exist).
- **Can I change the time it runs?** Yes—adjust Task Scheduler or cron.
