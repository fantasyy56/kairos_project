"""
Streaming reader over the raw CDM18 JSON-lines shards.

Each physical file is a sequence of independent JSON objects, one per line,
of the form:

    {"datum": {"<avro-union-type>": {...fields...}}, "CDMVersion": "18", "source": "..."}

This module only ever reads the configured byte sub-ranges (see config.RAW_RANGES)
and streams line-by-line, never loading a whole file into memory.
"""

from __future__ import annotations

import os
from typing import Iterator, Optional

import orjson

CHUNK_SIZE = 8 * 1024 * 1024  # 8MB read chunks


def iter_lines(path: str, start: int = 0, end: Optional[int] = None) -> Iterator[bytes]:
    """
    Yield raw lines (without newline) from `path`, restricted to byte range
    [start, end). If start > 0, the partial line at `start` is discarded (we
    seek forward to the next '\\n' first) since `start` was located via binary
    search and may land mid-record. If end is None, reads to EOF, but if end
    falls mid-line we discard the trailing partial line too, for symmetry with
    how the *next* range's start is computed by the same binary search logic.
    """
    file_size = os.path.getsize(path)
    if end is None:
        end = file_size

    with open(path, "rb") as f:
        pos = start
        if pos > 0:
            f.seek(pos)
            # discard partial line
            partial = f.readline()
            pos += len(partial)

        buf = b""
        while pos < end:
            to_read = min(CHUNK_SIZE, end - pos)
            chunk = f.read(to_read)
            if not chunk:
                break
            pos += len(chunk)
            buf += chunk
            *lines, buf = buf.split(b"\n")
            for line in lines:
                line = line.rstrip(b"\r")
                if line:
                    yield line
        # trailing partial line at the end of range is intentionally dropped
        # (mirrors the "discard partial line at start" behavior of the next
        # range, so no line is double counted and no line is corrupted).


def iter_records(ranges: list[dict],
                  max_lines_per_range: Optional[int] = None) -> Iterator[dict]:
    """
    Yield parsed JSON dicts across a list of {"path", "start", "end"} ranges,
    in the order given (ranges are expected to already be chronologically
    ordered upstream, in config.RAW_RANGES).

    max_lines_per_range: if set, stop after this many lines from EACH range
    (not a global total). This is deliberately per-range rather than a single
    global cap so a sampled run still touches every shard -- including the
    day6 attack-window shards -- instead of exhausting the whole budget on the
    chronologically-first (pre-attack) range and never reaching the attack
    data at all. Intended for smoke-testing the pipeline on bounded
    memory/time, NOT for producing evaluable reconstruction results (most
    seeds will not resolve on a small sample).
    """
    for r in ranges:
        n = 0
        for line in iter_lines(r["path"], r.get("start", 0), r.get("end")):
            if max_lines_per_range is not None and n >= max_lines_per_range:
                break
            n += 1
            try:
                yield orjson.loads(line)
            except orjson.JSONDecodeError:
                # Extremely rare malformed line (e.g. truncated by a chunk
                # boundary bug) -- skip rather than crash a multi-GB scan.
                continue


def _extract_ts(record: dict) -> Optional[int]:
    """Best-effort timestampNanos of a parsed record (only Event-shaped
    records carry one; other CDM object types don't)."""
    datum = record.get("datum")
    if not datum:
        return None
    for _, body in datum.items():
        if isinstance(body, dict):
            ts = body.get("timestampNanos")
            if ts is not None:
                try:
                    return int(ts)
                except (TypeError, ValueError):
                    return None
    return None


def probe_timestamp(path: str, offset: int, end: int,
                     max_probe_lines: int = 2000) -> Optional[int]:
    """
    Seek to `offset` within `path` and return the first timestampNanos found
    within the next `max_probe_lines` lines (skipping non-Event records,
    which have no timestamp), or None if none found in that window.
    """
    for i, line in enumerate(iter_lines(path, offset, end)):
        if i >= max_probe_lines:
            break
        try:
            rec = orjson.loads(line)
        except orjson.JSONDecodeError:
            continue
        ts = _extract_ts(rec)
        if ts is not None:
            return ts
    return None


def find_offset_for_time(path: str, start: int, end: int, target_ns: int,
                          granularity: int = 2_000_000) -> int:
    """
    Binary-search within byte range [start, end) of `path` for a byte offset
    close to where timestampNanos crosses `target_ns`, without a linear scan
    of a multi-GB shard. Resolves to within `granularity` bytes (default 2MB
    -- plenty for locating an attack-window boundary with a few minutes of
    margin). If a probe window is too sparse to find any timestamp, narrows
    toward the lower half rather than failing.
    """
    lo, hi = start, end
    while hi - lo > granularity:
        mid = (lo + hi) // 2
        ts = probe_timestamp(path, mid, end)
        if ts is None:
            hi = mid
            continue
        if ts < target_ns:
            lo = mid
        else:
            hi = mid
    return lo


def unwrap(value):
    """
    Avro union-typed scalars are serialized as a single-key dict, e.g.
    {"string": "foo"}, {"long": 123}, or
    {"com.bbn.tc.schema.avro.cdm18.UUID": "AAAA-..."}.
    Returns the bare scalar, or None/the original value if not a union wrapper.
    """
    if isinstance(value, dict) and len(value) == 1:
        return next(iter(value.values()))
    return value


def datum_type_and_body(record: dict) -> tuple[Optional[str], Optional[dict]]:
    """
    Each record's "datum" field is a single-key dict where the key is the
    fully qualified Avro union type name, e.g.
    "com.bbn.tc.schema.avro.cdm18.Event". Returns (short_type_name, body_dict).
    """
    datum = record.get("datum")
    if not datum:
        return None, None
    for full_type, body in datum.items():
        short_type = full_type.rsplit(".", 1)[-1]
        return short_type, body
    return None, None
