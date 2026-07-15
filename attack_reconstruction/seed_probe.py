"""
One-pass probe: locate our structured seeds (seeds.py) in the real day5-7
data, to resolve the open questions flagged earlier:
  - which of the two netrecon-failed IP spellings (154.145 vs 154.143) is real
  - what cid/uuid sshd (target of the failed injection) actually has
  - confirm nginx / vUgefal subjects exist and grab their identifying info

File paths are NOT on FileObject anymore in CDM v18 (removed in the schema
history, moved onto the Event record instead), so file seeds are matched via
Event.predicateObjectPath / predicateObject2Path, not FileObject fields.

Run: python3 seed_probe.py
"""

from __future__ import annotations

from collections import defaultdict

from config import RAW_RANGES
from raw_reader import iter_records, datum_type_and_body
from seeds import SEEDS

NETFLOW_SEEDS = {s.value.split(":")[0]: s for s in SEEDS if s.entity_type == "netflow"}
FILE_SEEDS = {s.value: s for s in SEEDS if s.entity_type == "file"}
SUBJECT_SEEDS = {s.value: s for s in SEEDS if s.entity_type == "subject"}


def main() -> None:
    netflow_hits: dict[str, dict] = {}
    file_hits: defaultdict[str, int] = defaultdict(int)
    subject_hits: dict[str, list[dict]] = defaultdict(list)

    seen_uuid_to_cmdline: dict[str, str] = {}

    for record in iter_records(RAW_RANGES):
        short_type, body = datum_type_and_body(record)
        if short_type is None:
            continue

        if short_type == "NetFlowObject":
            remote = body.get("remoteAddress")
            local = body.get("localAddress")
            for addr in (remote, local):
                if addr in NETFLOW_SEEDS and addr not in netflow_hits:
                    netflow_hits[addr] = {
                        "uuid": body.get("uuid"),
                        "localAddress": local,
                        "localPort": body.get("localPort"),
                        "remoteAddress": remote,
                        "remotePort": body.get("remotePort"),
                    }

        elif short_type == "Subject":
            cmdline_wrap = body.get("cmdLine")
            cmdline = cmdline_wrap.get("string") if isinstance(cmdline_wrap, dict) else None
            uuid = body.get("uuid")
            if cmdline:
                seen_uuid_to_cmdline[uuid] = cmdline
                for name, seed in SUBJECT_SEEDS.items():
                    if name.lower() in cmdline.lower():
                        subject_hits[name].append({
                            "uuid": uuid,
                            "cid": body.get("cid"),
                            "cmdLine": cmdline,
                            "parentSubject": body.get("parentSubject"),
                        })

        elif short_type == "Event":
            for path_key in ("predicateObjectPath", "predicateObject2Path"):
                path_val = body.get(path_key)
                if isinstance(path_val, dict):
                    path_val = path_val.get("string")
                if path_val and path_val in FILE_SEEDS:
                    file_hits[path_val] += 1

    print("=== NetFlow seed matches ===")
    for addr, seed in NETFLOW_SEEDS.items():
        hit = netflow_hits.get(addr)
        print(f"  {seed.id:20s} {addr:16s} -> {hit if hit else 'NOT FOUND'}")

    print("\n=== File path seed matches (event count referencing path) ===")
    for path, seed in FILE_SEEDS.items():
        print(f"  {seed.id:25s} {path:20s} -> {file_hits.get(path, 0)} events")

    print("\n=== Subject seed matches (cmdLine substring) ===")
    for name, hits in subject_hits.items():
        # de-dup by uuid, show up to 5 distinct processes
        by_uuid = {h['uuid']: h for h in hits}
        print(f"  '{name}': {len(by_uuid)} distinct subject uuid(s)")
        for h in list(by_uuid.values())[:5]:
            print(f"      cid={h['cid']}, uuid={h['uuid']}, cmdLine={h['cmdLine']!r}")


if __name__ == "__main__":
    main()
