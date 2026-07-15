"""
Diagnostic pass over the target byte ranges (day5-7, see config.RAW_RANGES).

Purpose: data-driven discovery, BEFORE we build the graph, to validate:
  1. What CDM record types actually appear, and how many of each.
  2. Full EventType distribution (not KAIROS's 7-type whitelist) + our
     semantic bucket per event_types.classify().
  3. Whether predicateObject2 is ever populated (dual-object events KAIROS's
     graph-building would silently ignore).
  4. Min/max timestamp actually observed, as a sanity check against the byte
     ranges we picked via binary search in config.py.

Run: python3 scan_event_types.py
"""

from __future__ import annotations

import time
from collections import Counter

from config import RAW_RANGES
from raw_reader import iter_records, datum_type_and_body
from event_types import classify


def ns_to_et_str(ns: int) -> str:
    from datetime import datetime
    from config import ET
    return datetime.fromtimestamp(int(ns) / 1e9, tz=ET).strftime("%Y-%m-%d %H:%M:%S.%f")


def main() -> None:
    t0 = time.time()

    record_type_counts: Counter = Counter()
    event_type_counts: Counter = Counter()
    category_counts: Counter = Counter()
    predicate_object2_present = 0
    total_events = 0
    total_lines = 0
    min_ts = None
    max_ts = None

    for line_no, record in enumerate(iter_records(RAW_RANGES)):
        total_lines += 1
        short_type, body = datum_type_and_body(record)
        if short_type is None:
            continue
        record_type_counts[short_type] += 1

        if short_type == "Event":
            total_events += 1
            etype = body.get("type", "UNKNOWN")
            event_type_counts[etype] += 1
            category_counts[classify(etype)] += 1

            if body.get("predicateObject2") is not None:
                predicate_object2_present += 1

            ts = body.get("timestampNanos")
            if ts is not None:
                if min_ts is None or ts < min_ts:
                    min_ts = ts
                if max_ts is None or ts > max_ts:
                    max_ts = ts

        if total_lines % 2_000_000 == 0:
            elapsed = time.time() - t0
            print(f"  ...{total_lines:,} lines scanned ({elapsed:.0f}s elapsed)")

    elapsed = time.time() - t0
    print(f"\n=== scan complete in {elapsed:.1f}s ===")
    print(f"total lines: {total_lines:,}")
    print(f"total Event records: {total_events:,}")
    print(f"predicateObject2 populated: {predicate_object2_present:,} "
          f"({100 * predicate_object2_present / max(total_events, 1):.2f}%)")
    if min_ts and max_ts:
        print(f"observed timestamp range: {ns_to_et_str(min_ts)} ~ {ns_to_et_str(max_ts)} ET")

    print("\n--- record type counts ---")
    for rtype, cnt in record_type_counts.most_common():
        print(f"  {rtype:25s} {cnt:>12,}")

    print("\n--- EventType distribution (full, not a whitelist) ---")
    for etype, cnt in event_type_counts.most_common():
        cat = classify(etype)
        print(f"  {etype:35s} {cnt:>12,}   [{cat}]")

    print("\n--- semantic category totals ---")
    for cat, cnt in category_counts.most_common():
        print(f"  {cat:20s} {cnt:>12,}")


if __name__ == "__main__":
    main()
