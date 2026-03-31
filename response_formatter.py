from __future__ import annotations

import json
import sys


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print(raw)
        return 0

    status = payload.get("status")
    url = payload.get("url")
    service_date = payload.get("service_date")
    assembled = payload.get("assembled_service") or {}
    service_date = service_date or assembled.get("service_date")
    observance = assembled.get("observance") or assembled.get("description") or service_date

    if status == "generated":
        print(f"Created booklet for {observance}.")
        if url:
            print(url)
        return 0
    if status == "updated":
        print(f"Updated booklet for {observance or service_date}.")
        if url:
            print(url)
        return 0
    if status == "exists":
        print(f"Booklet already exists for {service_date}.")
        if url:
            print(url)
        return 0
    if status == "found":
        print(f"Booklet link for {service_date}:")
        if url:
            print(url)
        return 0
    if status == "not_found":
        print(payload.get("message", "Booklet not found."))
        return 0
    if status == "dry_run":
        print(f"Dry run ready for {observance or service_date}.")
        if url:
            print(url)
        return 0

    print(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
