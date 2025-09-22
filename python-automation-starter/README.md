# Python Automation Starter — Etsy Lister

This starter project now automates **draft listing creation on Etsy**. Provide your
product catalog in a CSV file and the script will call Etsy's v3 API to create
listings (optionally uploading product photos) for the items you flag. Start in
`dry_run` mode to validate everything locally, then switch to live mode once
you're satisfied with the payloads.

---

## 🚀 What it does
- Loads Etsy API credentials and run settings from `config.json`
- Reads products from a CSV inventory file
- Creates draft listings through the Etsy Open API v3
- Uploads one or more product photos per listing (optional)
- Logs every step and saves a run summary into `output/`

---

## 🧰 Setup (once)
1. **Install Python** (3.9+ recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the example config and update it with your Etsy credentials:
   ```bash
   cp config.example.json config.json
   ```
4. Generate an inventory file. Start from `inventory.example.csv`, replace the
   sample row with your products, and save it as `inventory.csv` (the default
   file name referenced in the config).
5. Place product photos in the folder referenced by `images_dir` (defaults to
   `images/` relative to this project). Use the `image_filename` column in the
   CSV to point to each photo.

> ℹ️ When you're ready to push listings live, set `"dry_run": false` inside
> `config.json`. Leave it as `true` while testing to avoid API calls.

---

## ⚙️ Config options (`config.json`)
| Key | Description |
| --- | --- |
| `etsy_api_key` | Your Etsy app's API key. |
| `etsy_access_token` | OAuth access token for the shop you want to manage. |
| `shop_id` | Numeric Etsy shop ID. |
| `inventory_file` | Path to the CSV that defines listings to create. |
| `images_dir` | Directory where product images live. |
| `save_dir` | Where logs and run summaries are written (defaults to `output/`). |
| `default_currency` | ISO currency code for prices (e.g. `USD`). |
| `default_who_made` | Default maker info (e.g. `i_did`). |
| `default_when_made` | Production timeframe (e.g. `made_to_order`). |
| `default_is_supply` | Whether items are supplies by default. |
| `default_taxonomy_id` | Etsy taxonomy ID applied when a row omits one. |
| `default_type` | Listing type (`physical` or `download`). |
| `shipping_profile_id` | Shipping profile to attach (required for physical goods). |
| `return_policy_id` | Optional return policy ID. |
| `production_partner_ids` | List of production partner IDs to link. |
| `should_auto_renew` | Whether Etsy should auto-renew the listing. |
| `dry_run` | If `true`, skip Etsy API calls and only log what would happen. |

---

## 📄 Inventory CSV format
The script expects a header row with the following columns (all lowercase):

| Column | Required | Notes |
| --- | --- | --- |
| `title` | ✅ | Listing title. |
| `description` | ✅ | Full listing description. |
| `price` | ✅ | Decimal amount (uses `default_currency`). |
| `quantity` | ✅ | Stock level to publish. |
| `tags` | ⛔️ | Optional comma/semicolon separated tags. |
| `materials` | ⛔️ | Optional list of materials. |
| `image_filename` | ⛔️ | Comma/semicolon separated image file names. |
| `sku` | ⛔️ | Optional SKU. |
| `taxonomy_id` | ⛔️ | Overrides `default_taxonomy_id` for the row. |
| `who_made` | ⛔️ | Overrides `default_who_made`. |
| `when_made` | ⛔️ | Overrides `default_when_made`. |
| `is_supply` | ⛔️ | Overrides `default_is_supply` (`true`/`false`). |
| `shipping_profile_id` | ⛔️ | Overrides config value. |
| `return_policy_id` | ⛔️ | Overrides config value. |
| `shop_section_id` | ⛔️ | Optional section to assign. |
| `production_partner_ids` | ⛔️ | Comma/semicolon separated IDs for the row. |
| `type` | ⛔️ | Overrides `default_type`. |

Additional columns are ignored. Remove rows you do not wish to list yet.

`inventory.example.csv` includes a sample row you can reference.

---

## ▶️ Run it
```bash
python main.py
```

- **Dry run (`dry_run = true`)** — Validates the CSV, builds the payloads, and
  logs what would be sent to Etsy. No network calls are made.
- **Live mode (`dry_run = false`)** — Creates draft listings on Etsy and uploads
  any referenced images.

Each execution writes a JSON summary like `output/etsy_run_YYYYMMDD-HHMMSS.json`
containing the status of every attempted listing. Review this file (and
`output/run.log`) after every run.

---

## ⏰ Schedule it (optional)
Reuse your OS scheduler to run the script automatically—just like the original
starter project.

**Windows (Task Scheduler)**
1. *Create Basic Task…*
2. Trigger: choose when it should run (daily, weekly, etc.)
3. Action: *Start a Program* → `python`
4. Add arguments: `main.py`
5. Start in: the **full path** to this folder

**macOS / Linux (cron)**
```cron
0 8 * * * /usr/bin/python3 /full/path/to/main.py >> /full/path/to/output/cron.log 2>&1
```
Adjust the schedule and Python path as needed.

---

## ❓ FAQ
- **Can I test without real API credentials?** Yes—leave `dry_run` enabled. The
  script will parse the CSV, build payloads, and log them locally.
- **How do I get required IDs?** Use Etsy's admin or API to look up taxonomy,
  shipping profile, section, and production partner IDs. Fill them in either in
  `config.json` or directly in the CSV.
- **Where are files saved?** Logs and run summaries live in the directory
  defined by `save_dir` (defaults to `output/`).
- **Can I reuse this for other marketplaces?** Absolutely. Swap out the Etsy
  API calls with the marketplace you need, but keep the overall structure: load
  config → read inventory → perform API actions → log results.
