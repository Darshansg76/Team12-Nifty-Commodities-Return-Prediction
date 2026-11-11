"""Retrieve official Nifty Commodities PRICE index daily OHLC and provenance.

No proxy series, simulated observations or forward filling. Public requests
obey the historical-data website's maximum 365-day interval.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ENDPOINT = "https://www.niftyindices.com/BackPage/getHistoricaldatatabletoString"
SOURCE_PAGE = "https://www.niftyindices.com/reports/historical-data"
INDEX_PAGE = "https://www.niftyindices.com/indices/equity/thematic-indices/nifty-commodities"
ROOT = Path(__file__).resolve().parents[1]

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def request_year(start: date, end: date, output_dir: Path) -> tuple[list[dict], dict]:
    assert 0 <= (end - start).days <= 365
    params = {"name": "NIFTY COMMODITIES", "startDate": start.strftime("%d-%b-%Y"),
              "endDate": end.strftime("%d-%b-%Y"), "indexName": "NIFTY COMMODITIES"}
    # Mirror the official JavaScript's outer JSON and single-quoted cinfo string.
    # Do not use eval to parse any server response.
    payload = {"cinfo": str(params)}
    request = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(),
        headers={"User-Agent": "Mozilla/5.0 (academic reproducible research)",
                 "Referer": SOURCE_PAGE, "Content-Type": "application/json; charset=utf-8",
                 "Accept": "application/json"}, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw, status = response.read(), response.status
            break
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    output_file = output_dir / f"nifty_commodities_{start}_{end}.json"
    output_file.write_bytes(raw)
    data = json.loads(raw)
    if isinstance(data, dict) and "d" in data:
        data = data["d"]
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, list):
        raise ValueError(f"Unexpected response for {start}: {type(data)}")
    return data, {"url": ENDPOINT, "method": "POST", "payload": payload,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "http_status": status,
        "response_file": output_file.name, "response_sha256": sha256(raw),
        "response_bytes": len(raw), "observations": len(data)}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2010-01-01")
    parser.add_argument("--end", default="2026-11-10")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if start > end:
        parser.error("--start must be on or before --end")
    if end >= date.today():
        parser.error("--end must precede the current date to exclude an incomplete session")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records, requests = [], []
    for year in range(start.year, end.year + 1):
        chunk_start, chunk_end = max(start, date(year, 1, 1)), min(end, date(year, 12, 31))
        data, meta = request_year(chunk_start, chunk_end, args.output_dir)
        records.extend(data)
        requests.append(meta)
        print(f"{year}: {len(data)} observations", flush=True)
        time.sleep(0.4)
    rows, duplicates = {}, 0
    for r in records:
        if r.get("INDEX_NAME", "").strip().lower() != "nifty commodities":
            raise ValueError(f"Unexpected index identity: {r.get('INDEX_NAME')}")
        dt = datetime.strptime(r["HistoricalDate"], "%d %b %Y").date()
        if not start <= dt <= end:
            raise ValueError(f"Out-of-range observation: {dt}")
        row = {"date": dt.isoformat(), **{c.lower(): (None if r[c] in ("-", "", None) else float(r[c])) for c in ("OPEN", "HIGH", "LOW", "CLOSE")}}
        if row["close"] is None:
            raise ValueError(f"Missing close at {dt}")
        if min(row[c] for c in ("open", "high", "low", "close") if row[c] is not None) <= 0:
            raise ValueError(f"Non-positive price at {dt}")
        if all(row[c] is not None for c in ("open", "high", "low", "close")) and not (row["low"] <= min(row["open"], row["close"]) <= max(row["open"], row["close"]) <= row["high"]):
            raise ValueError(f"Inconsistent OHLC bounds at {dt}")
        if dt in rows:
            duplicates += 1
            if rows[dt] != row:
                raise ValueError(f"Conflicting duplicate at {dt}")
        rows[dt] = row
    ordered = [rows[k] for k in sorted(rows)]
    if not ordered:
        raise ValueError("No observations returned")
    csv_path = args.output_dir / "nifty_commodities_daily.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close"])
        writer.writeheader()
        writer.writerows(ordered)
    complete_rows = [r for r in ordered if all(r[c] is not None for c in ("open", "high", "low", "close"))]
    complete_path = args.output_dir / "nifty_commodities_complete_ohlc.csv"
    with complete_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close"])
        writer.writeheader()
        writer.writerows(complete_rows)
    provenance = {"dataset": "Nifty Commodities daily price index OHLC",
        "provider": "NSE Indices Limited", "index_page": INDEX_PAGE,
        "historical_data_page": SOURCE_PAGE, "endpoint": ENDPOINT,
        "endpoint_evidence": "https://liveindexsa.niftyindices.com/assets/js/IISLComponet.js function HistoricalData",
        "requested_start": start.isoformat(), "requested_end": end.isoformat(),
        "actual_start": ordered[0]["date"], "actual_end": ordered[-1]["date"],
        "rows": len(ordered), "identical_duplicates_removed": duplicates,
        "missing_values_by_column": {c: sum(r[c] is None for r in ordered) for c in ("open", "high", "low", "close")},
        "missing_value_policy": "Official '-' values become blank CSV cells. No filling. Complete-OHLC subset is supplied separately.",
        "complete_ohlc_file": complete_path.name,
        "complete_ohlc_sha256": sha256(complete_path.read_bytes()),
        "complete_ohlc_rows": len(complete_rows),
        "complete_ohlc_start": complete_rows[0]["date"],
        "complete_ohlc_end": complete_rows[-1]["date"],
        "price_basis": "Price index, not total return index; excludes reinvested dividends",
        "units": "Index points, not INR spot commodity prices",
        "calendar": "Observed sessions only; weekends/holidays are not fabricated or filled",
        "snapshot_cutoff_note": "Requested through 2026-11-10. November 10, 2026 is an official Diwali-Balipratipada trading holiday, so the last returned session is November 9.",
        "holiday_calendar_url": "https://www.nseindia.com/resources/exchange-communication-holidays",
        "prelaunch_note": "Includes prelaunch/back-calculated index observations. Launch date September 7, 2011; base date January 1, 2004 according to the official October 30, 2026 factsheet.",
        "factsheet_url": "https://www.niftyindices.com/Factsheet/ind_nifty_commodities.pdf",
        "csv_file": csv_path.name, "csv_sha256": sha256(csv_path.read_bytes()), "requests": requests}
    (args.output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(f"Saved {len(ordered)} observations {ordered[0]['date']} through {ordered[-1]['date']}")

if __name__ == "__main__":
    main()
