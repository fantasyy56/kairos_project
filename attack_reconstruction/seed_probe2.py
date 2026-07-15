"""
Follow-up probe after seed_probe.py's first pass came back with unexpected
gaps (no NetFlowObject for netrecon_fail_1a/1b or libdrakon_src; zero Subject
matches for nginx/vUgefal/sshd via cmdLine).

Two working hypotheses to check here:
  1. Subject.cmdLine is frequently null for this DTrace-based source; process
     identity instead lives in Event.properties.map["exec"] (seen in the raw
     sample: `"properties":{"map":{...,"exec":"python2.7","ppid":"1"}}`).
     -> redo the subject match against Event.properties.exec instead.
  2. The "missing" network seeds might still appear as *text* inside Event
     properties (e.g. as a connect() argument) even without a persisted
     NetFlowObject entity (short-lived/failed flows may skip full object
     creation on this DTrace source).
     -> do a raw substring scan for those IPs across all Event lines.

Run: python3 seed_probe2.py
"""

from __future__ import annotations

from collections import defaultdict

from config import RAW_RANGES
from raw_reader import iter_records, datum_type_and_body
from seeds import SEEDS

SUBJECT_NAMES = [s.value for s in SEEDS if s.entity_type == "subject"]
MISSING_IPS = ["154.145.113.18", "154.143.113.18", "152.111.159.139"]


def unwrap(v):
    return v.get("string") if isinstance(v, dict) else v


def main() -> None:
    exec_hits: defaultdict[str, list[dict]] = defaultdict(list)
    ip_text_hits: defaultdict[str, int] = defaultdict(int)
    ip_sample_events: dict[str, dict] = {}

    for record in iter_records(RAW_RANGES):
        short_type, body = datum_type_and_body(record)
        if short_type != "Event":
            continue

        props = body.get("properties")
        props_map = props.get("map") if isinstance(props, dict) else None
        exec_name = props_map.get("exec") if props_map else None

        if exec_name:
            for name in SUBJECT_NAMES:
                if name.lower() in exec_name.lower():
                    if len(exec_hits[name]) < 5:
                        exec_hits[name].append({
                            "exec": exec_name,
                            "subject": unwrap(body.get("subject")),
                            "type": body.get("type"),
                            "properties": props_map,
                        })

        # cheap textual scan for the missing IPs anywhere in properties/paths
        haystack_parts = []
        if props_map:
            haystack_parts.extend(props_map.values())
        for k in ("predicateObjectPath", "predicateObject2Path"):
            v = unwrap(body.get(k))
            if v:
                haystack_parts.append(v)
        if haystack_parts:
            haystack = " ".join(str(p) for p in haystack_parts)
            for ip in MISSING_IPS:
                if ip in haystack:
                    ip_text_hits[ip] += 1
                    if ip not in ip_sample_events:
                        ip_sample_events[ip] = {
                            "type": body.get("type"),
                            "properties": props_map,
                            "predicateObjectPath": unwrap(body.get("predicateObjectPath")),
                        }

    print("=== Subject identity via Event.properties.exec ===")
    for name in SUBJECT_NAMES:
        hits = exec_hits.get(name, [])
        print(f"  '{name}': {len(hits)} sample event(s) with matching exec")
        for h in hits:
            print(f"      type={h['type']}, subject_uuid={h['subject']}, exec={h['exec']!r}")

    print("\n=== Missing IP textual scan (anywhere in Event properties/paths) ===")
    for ip in MISSING_IPS:
        cnt = ip_text_hits.get(ip, 0)
        print(f"  {ip:16s} -> {cnt} matching events")
        if ip in ip_sample_events:
            print(f"      sample: {ip_sample_events[ip]}")


if __name__ == "__main__":
    main()
