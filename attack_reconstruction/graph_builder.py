"""
Single-pass streaming construction of the in-memory provenance graph.

One linear scan over config.RAW_RANGES does everything, so we never touch the
~16GB of raw data more than once:

  * every CDM *object* record  -> a Node (entities.node_from_object)
  * every CDM *Event* record   -> back-fills path/exec identity onto the object
                                   nodes it references, AND (if it falls inside
                                   the graph edge time window) becomes one or two
                                   directed causal Edges.

Memory bound (see the SEED_IPS/SEED_PATHS/SEED_EXECS guard below): identity
back-fill (path_to_uuids / exec_to_uuids / addr_to_uuids, and the Node objects
they'd otherwise force into existence) is only done UNCONDITIONALLY inside the
day6 edge window (GRAPH_EDGE_WINDOW_ET). Outside that window -- i.e. days 5
and 7, ~2 of the ~3 scanned days -- it is only done for values that exactly
match one of the fixed lookup targets in seeds.py, since resolve_seeds()
(chains.py) never queries anything else. This keeps peak RSS roughly
proportional to "1 day of edges + 15 seed hits" instead of "3 days of every
distinct path/exec-name/IP ever seen", with byte-for-byte identical seed
resolution / reconstruction output.

Direction semantics (CDM v18):
  Default causal direction is subject --> predicateObject (the subject acts on /
  writes to the object). For read-like events (config.EDGE_REVERSED: ACCEPT,
  RECVFROM, RECVMSG) information flows object --> subject, so we flip the edge.
  A single Event may carry BOTH predicateObject and predicateObject2 (e.g.
  rename src+dst); each yields its own edge with the same direction rule, so we
  never silently drop the 2nd object the way a predicateObject-only builder would.

Storage is plain Python (in-memory only, per the agreed design). UUIDs are kept
as strings; adjacency is stored as uuid -> list[edge_index] for both directions
to support the bidirectional BFS in chains.py.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from config import RAW_RANGES, EDGE_REVERSED, GRAPH_EDGE_WINDOW_ET, et_to_ns, ns_to_et
from raw_reader import iter_records, datum_type_and_body, unwrap
from entities import Node, node_from_object, OBJECT_TYPES
from event_types import classify
from seeds import SEEDS
from memguard import rss_gb as _rss_gb, check_budget, MemoryBudgetExceeded

# ---------------------------------------------------------------------------
# MEMORY GUARD: full-range identity back-fill (path_to_uuids / exec_to_uuids /
# addr_to_uuids + the Node objects they imply) used to run UNCONDITIONALLY
# for every one of the ~12.4M events across all 3 captured days, even though
# resolve_seeds() (chains.py) only ever looks up the ~15 fixed values below.
# That is what drove memory into the tens-of-GB range on a full run. Outside
# the day6 edge window (GRAPH_EDGE_WINDOW_ET) we now only index/keep a node
# when its path/exec_name/remote_address EXACTLY matches one of these seed
# values -- seed resolution results are therefore IDENTICAL to before, but we
# stop paying for the ~2 days' worth of irrelevant paths/exec-names/objects
# that were never queried. Inside the edge window, behavior is unchanged
# (full back-fill), since those nodes become real edge endpoints and need
# good labels for the report.
# ---------------------------------------------------------------------------
SEED_IPS = frozenset(s.value.split(":")[0] for s in SEEDS if s.entity_type == "netflow")
SEED_PATHS = frozenset(s.value for s in SEEDS if s.entity_type == "file")
SEED_EXECS = frozenset(s.value for s in SEEDS if s.entity_type == "subject")


@dataclass
class Edge:
    __slots__ = ("idx", "src", "dst", "etype", "category", "ts", "path", "event_uuid")
    idx: int
    src: str            # source node uuid (causal origin, after direction normalization)
    dst: str            # destination node uuid
    etype: str          # CDM EventType, e.g. EVENT_WRITE
    category: str       # semantic bucket from event_types.classify
    ts: int             # timestampNanos
    path: Optional[str]  # predicateObjectPath for this edge's object, if any
    event_uuid: Optional[str]


class ProvenanceGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.out_adj: dict[str, list[int]] = {}   # uuid -> outgoing edge indices
        self.in_adj: dict[str, list[int]] = {}    # uuid -> incoming edge indices
        # identity indexes for seed resolution (built during the pass)
        self.addr_to_uuids: dict[str, set[str]] = {}   # "1.2.3.4" -> netflow uuids
        self.path_to_uuids: dict[str, set[str]] = {}   # "/tmp/x" -> object uuids
        self.exec_to_uuids: dict[str, set[str]] = {}   # "nginx"  -> subject uuids
        # diagnostics
        self.stats: dict[str, int] = {}

    # -- node helpers --------------------------------------------------------
    def _ensure_node(self, uuid: str, kind: str = "Unknown") -> Node:
        n = self.nodes.get(uuid)
        if n is None:
            n = Node(uuid=uuid, kind=kind)
            self.nodes[uuid] = n
        return n

    def _add_object(self, short_type: str, body: dict) -> None:
        node = node_from_object(short_type, body, unwrap)
        if node is None:
            return
        existing = self.nodes.get(node.uuid)
        if existing is None:
            self.nodes[node.uuid] = node
        else:
            # object re-declared (happens across shards); keep first identity but
            # merge back-filled sets so we never lose a path/exec name
            existing.paths |= node.paths
            existing.exec_names |= node.exec_names
            node = existing
        # MEMORY GUARD: only index into addr_to_uuids when the address is one
        # of the fixed seed IPs (seeds.py) -- that dict is exclusively read by
        # resolve_seeds() for exact IP lookups, so indexing every one of the
        # (potentially huge, over 3 days) distinct remote addresses this host
        # ever talked to is pure waste. The Node itself is still created/kept
        # either way, so day6-window netflow edges keep their full ip:port
        # label in the report -- only the seed-lookup side index is pruned.
        if short_type == "NetFlowObject" and node.remote_address in SEED_IPS:
            self.addr_to_uuids.setdefault(node.remote_address, set()).add(node.uuid)

    # -- edge construction ---------------------------------------------------
    def _add_edge(self, src: str, dst: str, etype: str, ts: int,
                  path: Optional[str], event_uuid: Optional[str]) -> None:
        # ensure endpoint nodes exist even if their object record never appears
        # in our window (e.g. a long-lived daemon declared before day6)
        self._ensure_node(src)
        self._ensure_node(dst)
        idx = len(self.edges)
        self.edges.append(Edge(
            idx=idx, src=src, dst=dst, etype=etype, category=classify(etype),
            ts=ts, path=path, event_uuid=event_uuid,
        ))
        self.out_adj.setdefault(src, []).append(idx)
        self.in_adj.setdefault(dst, []).append(idx)


def _event_paths(body: dict) -> tuple[Optional[str], Optional[str]]:
    p1 = unwrap(body.get("predicateObjectPath"))
    p2 = unwrap(body.get("predicateObject2Path"))
    return (p1 if isinstance(p1, str) else None,
            p2 if isinstance(p2, str) else None)


def _exec_name(body: dict) -> Optional[str]:
    props = body.get("properties")
    pmap = props.get("map") if isinstance(props, dict) else None
    name = pmap.get("exec") if isinstance(pmap, dict) else None
    return name if isinstance(name, str) and name else None


def build_graph(edge_window_et: Optional[tuple[str, str]] = GRAPH_EDGE_WINDOW_ET,
                progress_every: int = 2_000_000,
                max_lines_per_range: Optional[int] = None,
                ranges: Optional[list[dict]] = None) -> ProvenanceGraph:
    """
    Stream `ranges` (default: config.RAW_RANGES) once and return a
    fully-built ProvenanceGraph.

    edge_window_et: (start_et, end_et) restricting which Events become edges.
      None -> build edges over the entire range (much higher memory).
      Node identity + path/exec resolution: full unconditional back-fill
      inside this window; outside it, only for values matching a fixed
      seeds.py lookup target (see the SEED_IPS/SEED_PATHS/SEED_EXECS guard
      near the top of this module) -- seed resolution is still exhaustive
      over the full range, just without indexing everything else too.

    max_lines_per_range: SMOKE-TEST ONLY. If set, caps how many lines are read
      from EACH raw shard range (bounds both runtime and memory, since node
      identity indexes otherwise grow over the full ~13M-line scan). Note this
      caps from the START of each range -- if `ranges` is the default
      RAW_RANGES, this means results are NOT meaningful for evaluation, since
      most seeds (and the whole attack window) live far into their shard and
      won't be reached (see kairos-research/Memory.md §14/§15; use
      config.attack_focused_ranges() via the `ranges` param instead if you
      need the sample to actually touch attack data). Use None (default) for
      a real reconstruction run.

    ranges: override the shard ranges to scan. Defaults to config.RAW_RANGES.
      Pass config.attack_focused_ranges() to build a small graph that is
      guaranteed to contain the attack window's edges.
    """
    g = ProvenanceGraph()
    ranges = ranges if ranges is not None else RAW_RANGES
    win_lo = win_hi = None
    if edge_window_et is not None:
        win_lo = et_to_ns(edge_window_et[0])
        win_hi = et_to_ns(edge_window_et[1])

    if max_lines_per_range is not None:
        print(f"[SAMPLE MODE] capping each of {len(ranges)} shard ranges to "
              f"{max_lines_per_range:,} lines (~{max_lines_per_range * len(ranges):,} "
              f"lines total). This bounds memory/runtime for a smoke test only -- "
              f"seed resolution / reconstruction results from this run are NOT "
              f"representative of the full dataset.")

    t0 = time.time()
    n_lines = n_events = n_edges_pre = 0

    for record in iter_records(ranges, max_lines_per_range=max_lines_per_range):
        n_lines += 1
        short_type, body = datum_type_and_body(record)
        if short_type is None:
            continue

        if short_type in OBJECT_TYPES:
            g._add_object(short_type, body)

        elif short_type == "Event":
            n_events += 1
            ts = body.get("timestampNanos")
            ts_int = int(ts) if ts is not None else None
            in_window = (win_lo is None or ts_int is None
                        or (win_lo <= ts_int < win_hi))

            subj = unwrap(body.get("subject"))
            obj1 = unwrap(body.get("predicateObject"))
            obj2 = unwrap(body.get("predicateObject2"))
            p1, p2 = _event_paths(body)

            # --- back-fill identity onto nodes ---
            # MEMORY GUARD: inside the day6 edge window, back-fill
            # unconditionally (matches original behavior -- these nodes are
            # real edge endpoints and need good labels). OUTSIDE the window
            # (days 5 and 7, ~2 of the ~3 scanned days), only back-fill /
            # index a path or exec_name that EXACTLY matches one of the
            # fixed seeds.py lookup values -- resolve_seeds() never queries
            # anything else, so indexing every other one of the millions of
            # distinct paths/exec-names seen on those two extra days (and
            # eagerly creating a Node for each) was pure unused memory.
            if subj:
                exec_name = _exec_name(body)
                if exec_name and (in_window or exec_name in SEED_EXECS):
                    node = g._ensure_node(subj, "Subject")
                    node.exec_names.add(exec_name)
                    g.exec_to_uuids.setdefault(exec_name, set()).add(subj)
            for obj, path in ((obj1, p1), (obj2, p2)):
                if obj and path and (in_window or path in SEED_PATHS):
                    node = g._ensure_node(obj)
                    node.paths.add(path)
                    g.path_to_uuids.setdefault(path, set()).add(obj)

            # --- materialize edges (only inside the edge window) ---
            if ts_int is None or not in_window or not subj:
                continue
            ts = ts_int

            etype = body.get("type", "UNKNOWN")
            reverse = etype in EDGE_REVERSED
            euuid = body.get("uuid")
            for obj, path in ((obj1, p1), (obj2, p2)):
                if not obj:
                    continue
                n_edges_pre += 1
                if reverse:
                    g._add_edge(obj, subj, etype, ts, path, euuid)
                else:
                    g._add_edge(subj, obj, etype, ts, path, euuid)

        if progress_every and n_lines % progress_every == 0:
            print(f"  ...{n_lines:,} lines  ({time.time() - t0:.0f}s)  "
                  f"nodes={len(g.nodes):,} edges={len(g.edges):,}  "
                  f"rss={_rss_gb():.2f}GB")
            # MEMORY GUARD: bail out (loudly, before the OS starts thrashing)
            # if this process's own RSS crosses the budget (default 20GB, see
            # memguard.py) -- graph building is normally light (<2GB observed
            # on a full 3-day run), so tripping here means something is
            # abnormal (e.g. a raw shard far larger than expected) and it is
            # far safer to stop now than to keep growing.
            check_budget()

    g.stats = {
        "lines": n_lines,
        "events": n_events,
        "nodes": len(g.nodes),
        "edges": len(g.edges),
    }
    if g.edges:
        tmin = min(e.ts for e in g.edges)
        tmax = max(e.ts for e in g.edges)
        print(f"\n=== graph built in {time.time() - t0:.1f}s ===")
        print(f"lines={n_lines:,} events={n_events:,} "
              f"nodes={len(g.nodes):,} edges={len(g.edges):,}")
        print(f"edge time span: {ns_to_et(tmin)} ~ {ns_to_et(tmax)} ET")
    return g
