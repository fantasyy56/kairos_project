"""
Configuration for the custom CADETS E3 attack-chain reconstruction pipeline.

Design decisions (confirmed with user, see chat history):
1. Ground-truth seeds are NOT reused from KAIROS's code. They are re-extracted
   from the official DARPA TC ground truth report
   (`ground truth/TC_Ground_Truth_Report_E3_Update.pdf`, section 3.1) — see seeds.py.
2. Event-type handling is NOT a hardcoded drop-whitelist. Types are discovered
   by scanning the real data (scan_event_types.py) then bucketed into semantic
   categories (event_types.py). Nothing is silently dropped by default.
3. Storage: in-memory only for now (no PostgreSQL). Revisit if/when scale requires it.
"""

import os
from datetime import datetime, timezone, timedelta

DATA_ROOT = "/Users/fantinli/coding/project1/kairos_project/data"

# The entire capture window (2018-04-02 ~ 2018-04-13) falls within EDT
# (US/Eastern DST was in effect the whole time), so a fixed UTC-4 offset is safe.
ET = timezone(timedelta(hours=-4))


def et_to_ns(et_str: str) -> int:
    """"2018-04-06 11:18:26" (ET, seconds, or with a .frac of ANY precision,
    e.g. the 9-digit-nanosecond timestamps quoted straight from the ground
    truth PDF in ATTACK_WINDOWS_REFERENCE) -> epoch nanoseconds."""
    if "." in et_str:
        base, frac = et_str.split(".", 1)
        # datetime.strptime's %f only accepts up to 6 digits (microseconds);
        # truncate/pad so nanosecond-precision input strings parse cleanly.
        # We recover the sub-microsecond remainder separately below so no
        # precision is silently dropped.
        frac6 = (frac + "000000")[:6]
        dt = datetime.strptime(f"{base}.{frac6}", "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=ET)
        sub_us_ns = int((frac + "000000000")[6:9])  # digits 7-9 -> ns remainder
        return int(round(dt.timestamp() * 1e9)) + sub_us_ns
    dt = datetime.strptime(et_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ET)
    return int(round(dt.timestamp() * 1e9))


def ns_to_et(ns: int) -> str:
    """epoch nanoseconds -> "2018-04-06 11:18:26.123456" (ET)."""
    return datetime.fromtimestamp(int(ns) / 1e9, tz=ET).strftime("%Y-%m-%d %H:%M:%S.%f")


def _p(group_dir: str, fname: str) -> str:
    return os.path.join(DATA_ROOT, group_dir, fname)


# ---------------------------------------------------------------------------
# Raw file layout
# ---------------------------------------------------------------------------
# The 10 shard files published by DARPA are NOT independent/parallel files —
# they are 3 chronologically continuous capture *sessions*, each split into
# <4.4GB transfer chunks (confirmed by sampling first/last event timestamp of
# every shard, see tools/locate_time_offsets.py):
#
#   official   (.json, .json.1, .json.2)  : 2018-04-02 18:07 -> 2018-04-06 12:08
#   official-1 (.json, .json.1..4)        : 2018-04-06 14:01 -> 2018-04-11 15:16
#   official-2 (.json, .json.1)           : 2018-04-11 16:36 -> 2018-04-13 17:35
#
# There is a ~1h52m GAP between official.json.2 (ends 2018-04-06 12:08:59) and
# official-1.json (starts 2018-04-06 14:01:12 ET). This lines up almost exactly
# with the "CADETS crashed, cause unknown, 12:20-14:00 ET" entry in
# `ground truth/operational_event_log.md`, and with the attack timeline's
# "inject sshd:809 failed" event (~12:04-12:08). Working hypothesis: the audit
# daemon itself died in the crash the injection attempt triggered, and capture
# only resumed after reboot. This gap is real signal, not missing data on our end.

# Each entry: byte range within one physical file to stream.
# start/end were located via binary search on `"timestampNanos":` occurrences
# (see tools/locate_time_offsets.py) so we don't have to scan whole multi-GB
# files linearly just to find where day 5 / day 8 boundaries fall.
RAW_RANGES = [
    dict(
        path=_p("ta1-cadets-e3-official.json", "ta1-cadets-e3-official.json.1"),
        start=2696059845, end=None,
        covers="2018-04-05 00:00:00 ~ 2018-04-05 13:35:17 ET",
    ),
    dict(
        path=_p("ta1-cadets-e3-official.json", "ta1-cadets-e3-official.json.2"),
        start=0, end=None,
        covers="2018-04-05 13:35:17 ~ 2018-04-06 12:08:59 ET",
    ),
    # >>> GAP: 2018-04-06 12:08:59 ~ 2018-04-06 14:01:12 ET (crash/reboot, no audit data) <<<
    dict(
        path=_p("ta1-cadets-e3-official-1.json", "ta1-cadets-e3-official-1.json"),
        start=0, end=None,
        covers="2018-04-06 14:01:12 ~ 2018-04-07 13:30:14 ET",
    ),
    dict(
        path=_p("ta1-cadets-e3-official-1.json", "ta1-cadets-e3-official-1.json.1"),
        start=0, end=2188636607,
        covers="2018-04-07 13:30:14 ~ 2018-04-08 00:00:00 ET",
    ),
]

# Overall logical window being reconstructed: day5, day6, day7 (US/Eastern)
WINDOW_START_ET = "2018-04-05 00:00:00"
WINDOW_END_ET = "2018-04-08 00:00:00"

# Attack sub-window, cross-checked identical in KAIROS's evaluation.py and
# attack_investigation.py (kept only as a reference marker, not as ground truth
# source — our seed list in seeds.py is independently derived from the PDF).
ATTACK_WINDOWS_REFERENCE = [
    ("2018-04-06 11:18:26.126177915", "2018-04-06 11:33:35.116170745"),
    ("2018-04-06 11:33:35.116170745", "2018-04-06 11:48:42.606135188"),
    ("2018-04-06 11:48:42.606135188", "2018-04-06 12:03:50.186115455"),
    ("2018-04-06 12:03:50.186115455", "2018-04-06 14:01:32.489584227"),
]

# Directions that need reversing (object is semantically the initiator).
# This is a fixed CDM schema property (confirmed against cdm.pdf / CDM18 avdl
# semantics), not a heuristic we're guessing at, so it stays a small constant.
EDGE_REVERSED = {
    "EVENT_ACCEPT",
    "EVENT_RECVFROM",
    "EVENT_RECVMSG",
}

def attack_focused_ranges(byte_budget: int = 1_500_000_000,
                          pre_crash_frac: float = 0.6) -> list[dict]:
    """
    Build a byte-bounded range list that is GUARANTEED to contain the attack
    window, sized by a total byte budget rather than a time margin -- unlike
    `--sample N` (raw_reader.iter_records' per-range line cap), which reads
    the FIRST N lines of each range and therefore never reaches the attack
    data at all: RAW_RANGES[1] spans ~22.5h/~3.4GB and the attack starts
    ~96.3% of the way through it (see kairos-research/Memory.md §14/§15), so
    any `--sample` far short of reading nearly the whole range misses the
    attack window entirely -- which is why every `--sample` smoke test has 0
    causally-linked stages.

    This needs no time-based margin computation at all, because of a
    structural fact already documented in RAW_RANGES' `covers` comments: the
    two shards straddling the crash gap end/start EXACTLY at the crash
    boundary --
      - RAW_RANGES[1] (...official.json.2) ends exactly at the crash
        (2018-04-06 12:08:59) -- so its TAIL, for however many bytes we can
        afford, IS attack-window + however much pre-attack context the
        budget buys (ground-truth stages 1-6 live in the last ~196MB of this
        3.4GB file; a bigger budget buys strictly MORE real surrounding
        context, not unrelated data).
      - RAW_RANGES[2] (...official-1.json) starts exactly at crash recovery
        (14:01:12) -- so its HEAD, for however many bytes we can afford, IS
        the immediate aftermath (ground-truth stages 9-11 live in the first
        ~67MB of this file).
    We just split `byte_budget` between the two sides (pre_crash_frac to the
    r1 tail, the rest to the r2 head) and take exactly that many bytes off
    each natural boundary. RAW_RANGES[0] and [3] (day5-early / day7-late) are
    dropped entirely: no ground-truth seed falls there, and the whole point
    is to spend the budget on data that can actually contain attack signal.
    """
    r1 = RAW_RANGES[1]
    r1_size = os.path.getsize(r1["path"])
    budget_r1 = int(byte_budget * pre_crash_frac)
    tail_start = max(r1.get("start", 0), r1_size - budget_r1)

    r2 = RAW_RANGES[2]
    r2_size = os.path.getsize(r2["path"])
    budget_r2 = byte_budget - budget_r1
    head_end = min(r2_size, r2.get("start", 0) + budget_r2)

    return [
        dict(path=r1["path"], start=tail_start, end=None,
             covers=f"pre-crash tail, last {r1_size - tail_start:,} bytes "
                    f"of official.json.2, ending at the crash (12:08:59) "
                    f"-- contains ground-truth stages 1-6"),
        dict(path=r2["path"], start=r2.get("start", 0), end=head_end,
             covers=f"post-crash head, first {head_end - r2.get('start', 0):,} "
                    f"bytes of official-1.json, starting at recovery "
                    f"(14:01:12) -- contains ground-truth stages 9-11"),
    ]


# ---------------------------------------------------------------------------
# Graph-build time window
# ---------------------------------------------------------------------------
# The entity index (uuid -> identity) and path resolution are always built over
# the FULL RAW_RANGES so seed resolution never misses an object. Materializing
# an *edge* for every one of the ~12.4M Events in day5-7 as Python objects,
# however, is memory-heavy and unnecessary for this targeted reconstruction:
# every ground-truth attack step (and its immediate benign context) falls inside
# 2018-04-06. So by default we only turn Events within this window into graph
# edges. This is a coarse TIME filter only -- it never filters by event type,
# so it does not reintroduce the KAIROS whitelist failure mode. Set to None to
# build edges over the entire RAW_RANGES (needs substantially more RAM).
GRAPH_EDGE_WINDOW_ET = ("2018-04-06 00:00:00", "2018-04-07 00:00:00")
