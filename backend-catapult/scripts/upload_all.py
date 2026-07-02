#!/usr/bin/env python3
import os, requests, csv, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Config from environment with sensible defaults
URL = os.getenv("BULK_UPLOAD_URL", "http://localhost:8000/catapult/upload")
TOKEN = os.getenv("TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
CSV_DIR = Path(os.getenv("CSV_DIR", "/mnt/c/Users/loicl/Desktop/PSGAcadémie/CSV"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))
RETRIES = int(os.getenv("RETRIES", "3"))
SLEEP_ON_FAIL = int(os.getenv("SLEEP_ON_FAIL", "2"))
RESULTS_CSV = Path(os.getenv("RESULTS_CSV", "upload_results.csv"))


def upload(path):
    for attempt in range(1, RETRIES+1):
        try:
            with open(path, "rb") as fh:
                files = {"file": (path.name, fh, "text/csv")}
                r = requests.post(URL, headers=HEADERS, files=files, timeout=120)
            return path.name, r.status_code, r.text
        except Exception as e:
            if attempt < RETRIES:
                time.sleep(SLEEP_ON_FAIL * attempt)
            else:
                return path.name, "ERROR", str(e)


def main():
    if not CSV_DIR.exists():
        print(f"Aucun CSV trouvé: dossier {CSV_DIR} introuvable")
        return

    paths = sorted([p for p in CSV_DIR.iterdir() if p.is_file()])
    if not paths:
        print("Aucun CSV trouvé dans", CSV_DIR); return

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex, open(RESULTS_CSV, "w", newline='', encoding='utf-8') as out:
        writer = csv.writer(out)
        writer.writerow(["filename","status","response"])
        futures = {ex.submit(upload, p): p for p in paths}
        for fut in as_completed(futures):
            name, code, body = fut.result()
            print(f"{name}: {code}")
            writer.writerow([name, code, body.replace('\n',' ')[:4000]])
    print("Résultats écrits dans", RESULTS_CSV)

if __name__ == "__main__":
    main()
