"""
Causal chain extraction over the in-memory provenance graph (graph_builder.py).

Two operations:

  1. resolve_seeds(): map each structured Seed (seeds.py) -- an IP, a file path,
     or a process image name -- onto the concrete node uuid(s) the graph builder
     discovered for it. A seed that resolves to zero uuids is flagged; for the
     CADETS-E3 attack the only unresolved seeds are the ones whose events fall in
     the crash gap (see the discussion section on the forensic ceiling), which is
     exactly the signal we want to surface, not hide.

  2. link_stages(): connect two entities through the graph with a time-respecting
     search. A causal chain is a sequence of events e_1..e_k whose timestamps are
     non-decreasing and where consecutive events share an entity. We try three
     progressively weaker notions of "connected", strongest first:

       (a) forward causal   -- a path that follows edges only along their
           normalized causal direction (out_adj) with non-decreasing time.
       (b) information-flow  -- a path that may traverse an edge from EITHER
           endpoint (undirected), still time-ordered. This is required because
           CDM's subject->object convention points some information-flow edges
           "backwards" for our purpose: EVENT_EXECUTE is proc->file, so linking a
           dropped payload file to the process that executed it means traversing
           that edge in reverse. Directionality does not constrain chain
           membership; only sharing an entity and time ordering do.
       (c) structural        -- undirected connectivity ignoring time (weakest;
           reported honestly as "structural, not time-ordered").

     The undirected search is bidirectional (meet-in-the-middle): a forward
     frontier from src and a backward frontier from dst grow toward each other,
     which lets us afford a larger total hop budget at ~sqrt cost and avoids the
     single-direction hub blow-up.

reconstruct_narrative() stitches consecutive-stage seeds into an end-to-end
chain and reports, per ground-truth stage, whether it was recovered, by which
link class, and if not recovered, whether the reason is a genuine miss or the
(data-level, algorithm-independent) crash gap.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from config import ns_to_et
from graph_builder import ProvenanceGraph, Edge
from seeds import Seed, SEEDS, seeds_by_stage
from memguard import check_budget, MemoryBudgetExceeded


# ---------------------------------------------------------------------------
# Seed resolution
# ---------------------------------------------------------------------------
@dataclass
class ResolvedSeed:
    seed: Seed
    uuids: set[str] = field(default_factory=set)

    @property
    def found(self) -> bool:
        return bool(self.uuids)


def resolve_seeds(g: ProvenanceGraph,
                  seeds: list[Seed] = SEEDS) -> dict[str, ResolvedSeed]:
    """seed.id -> ResolvedSeed (with the node uuid(s) it maps to)."""
    resolved: dict[str, ResolvedSeed] = {}
    for s in seeds:
        rs = ResolvedSeed(seed=s)
        if s.entity_type == "netflow":
            ip = s.value.split(":")[0]
            rs.uuids |= g.addr_to_uuids.get(ip, set())
        elif s.entity_type == "file":
            rs.uuids |= g.path_to_uuids.get(s.value, set())
        elif s.entity_type == "subject":
            # process image name may match several distinct pids; keep them all
            rs.uuids |= g.exec_to_uuids.get(s.value, set())
        resolved[s.id] = rs
    return resolved


# ---------------------------------------------------------------------------
# Time-respecting search
# ---------------------------------------------------------------------------
# Sentinels for the "no edge yet" ends of a partial walk. A forward root has no
# last edge (may continue with any ts); a backward root (the dst) has no suffix
# edge (any last edge may precede it).
_NEG = -1
_POS = 1 << 62

# Traversal guards. Routing an attack causal chain THROUGH a system-wide hub
# (a log file / pipe / daemon touched by tens of thousands of unrelated events)
# has essentially no evidentiary value -- such a node would connect almost
# everything to everything -- and it is also what makes an undirected BFS blow
# up combinatorially. So we refuse to EXPAND OUT OF an interior node whose
# undirected degree exceeds _HUB_DEGREE (roots are always expanded, since a seed
# must be left even if it happens to be busy). _MAX_VISITS is a hard safety cap
# on frontier size: if hit, the search reports "not connected within budget"
# rather than running unbounded. Both are honest search-budget parameters, not
# result fudging: they can only make a link HARDER to claim, never easier.
_HUB_DEGREE = 1500
_MAX_VISITS = 80_000

# How often (in visited-node count) to poll process RSS inside the BFS hot
# loops below. A getrusage() syscall is cheap, but not FREE -- checking every
# single node would add measurable overhead over tens of thousands of visits,
# so we sample every _MEM_CHECK_EVERY nodes. This is deliberately much more
# frequent than _MAX_VISITS is reached in normal cases, because the failure
# mode we're guarding against (a seed like "sshd" resolving to ~2000 uuids,
# each becoming a simultaneously-expanded BFS root) can blow up memory much
# faster than it blows up the visited-node COUNT (_MAX_VISITS counts distinct
# nodes, not the frontier/queue objects or per-node state that also pile up).
_MEM_CHECK_EVERY = 2_000


def _degree(g: ProvenanceGraph, node: str) -> int:
    return len(g.out_adj.get(node, ())) + len(g.in_adj.get(node, ()))


@dataclass
class _SN:
    """A node's best state in one frontier."""
    ts: int          # fwd: earliest ts of the LAST edge used to arrive here
                     # bwd: latest   ts of the FIRST edge of the suffix to dst
    depth: int
    edge_idx: int    # edge connecting this node to its parent (-1 for a root)
    parent: str      # parent node uuid ("" for a root)


def _incident(g: ProvenanceGraph, node: str, undirected: bool):
    """Yield (edge, other_endpoint) for edges usable to leave `node`.

    Directed: only edges leaving `node` along the normalized causal direction.
    Undirected: also edges pointing INTO `node` (traversed against direction),
    which is what lets an EXECUTE (proc->file) edge be walked file->proc, etc.
    """
    for eidx in g.out_adj.get(node, ()):
        e = g.edges[eidx]
        yield e, e.dst
    if undirected:
        for eidx in g.in_adj.get(node, ()):
            e = g.edges[eidx]
            yield e, e.src


def _directed_forward(g: ProvenanceGraph,
                      src_uuids: set[str],
                      dst_uuids: set[str],
                      hop_limit: int) -> Optional[list[Edge]]:
    """Strongest class: a forward, causal-direction-only, time-ordered path."""
    if not src_uuids or not dst_uuids:
        return None
    q = deque()
    parent: dict[str, tuple[int, str]] = {}   # node -> (edge_idx, prev_node)
    best_ts: dict[str, int] = {}
    for u in src_uuids:
        q.append((u, _NEG, 0))
        best_ts[u] = _NEG
        parent[u] = (-1, "")
    # MEMORY GUARD: a monotonic insert counter, checked INSIDE the inner edge
    # loop (not just once per outer pop) every _MEM_CHECK_EVERY insertions.
    # Two earlier bugs this fixes:
    #   1) checking only once per outer-loop pop is too late when a SINGLE
    #      node (e.g. one especially busy root among the ~2000 that a
    #      "sshd"-style seed resolves to -- roots are always expanded,
    #      _HUB_DEGREE only guards INTERIOR nodes) fans out into tens of
    #      thousands of new entries within that one inner loop.
    #   2) using `len(dict) % N == 0` can skip N entirely if the dict grows by
    #      more than one entry between checks (exactly the scenario in #1),
    #      so a monotonic counter incremented per-insertion is used instead.
    n_inserts = 0
    while q:
        node, arrive_ts, depth = q.popleft()
        if node in dst_uuids and parent[node][0] != -1:
            return _walk_parents(g, parent, node)
        if depth >= hop_limit:
            continue
        # do not route through an interior hub (see _HUB_DEGREE note)
        if depth > 0 and _degree(g, node) > _HUB_DEGREE:
            continue
        if len(best_ts) > _MAX_VISITS:
            break
        for eidx in g.out_adj.get(node, ()):
            e = g.edges[eidx]
            if arrive_ts != _NEG and e.ts < arrive_ts:
                continue
            nxt = e.dst
            if nxt not in best_ts or e.ts < best_ts[nxt]:
                best_ts[nxt] = e.ts
                parent[nxt] = (eidx, node)
                n_inserts += 1
                if n_inserts % _MEM_CHECK_EVERY == 0:
                    check_budget()
                if nxt in dst_uuids:
                    return _walk_parents(g, parent, nxt)
                q.append((nxt, e.ts, depth + 1))
    return None


def _walk_parents(g: ProvenanceGraph,
                  parent: dict[str, tuple[int, str]],
                  end: str) -> list[Edge]:
    path: list[Edge] = []
    node = end
    while parent[node][0] != -1:
        eidx, prev = parent[node]
        path.append(g.edges[eidx])
        node = prev
    path.reverse()
    return path


def _grow_frontier(g: ProvenanceGraph, roots: set[str], hop_cap: int,
                   enforce_time: bool, forward: bool) -> dict[str, _SN]:
    """Undirected time-respecting frontier (used for both ends of the bidi search).

    forward=True  keeps the EARLIEST last-edge ts (maximizes future slack).
    forward=False keeps the LATEST first-edge ts (maximizes past slack); an edge
                  may be taken only if its ts <= the current first-edge ts.
    """
    seed_ts = _NEG if forward else _POS
    state: dict[str, _SN] = {}
    q = deque()
    for r in roots:
        state[r] = _SN(ts=seed_ts, depth=0, edge_idx=-1, parent="")
        q.append(r)
    # MEMORY GUARD: see the detailed comment in _directed_forward -- same two
    # bugs fixed here (check inside the inner edge loop, per insertion, with
    # a monotonic counter rather than `len(state) % N` which can skip N).
    n_inserts = 0
    while q:
        node = q.popleft()
        st = state[node]
        if st.depth >= hop_cap:
            continue
        # never route through an interior hub; roots (depth 0) are always
        # expanded so a seed can be left even when it is a busy entity
        if st.depth > 0 and _degree(g, node) > _HUB_DEGREE:
            continue
        if len(state) > _MAX_VISITS:
            break
        for e, other in _incident(g, node, undirected=True):
            if enforce_time and st.ts != seed_ts:
                if forward and e.ts < st.ts:
                    continue
                if not forward and e.ts > st.ts:
                    continue
            prev = state.get(other)
            better = (prev is None
                      or (forward and e.ts < prev.ts)
                      or (not forward and e.ts > prev.ts))
            if better:
                state[other] = _SN(ts=e.ts, depth=st.depth + 1,
                                   edge_idx=e.idx, parent=node)
                n_inserts += 1
                if n_inserts % _MEM_CHECK_EVERY == 0:
                    check_budget()
                q.append(other)
    return state


def _bidirectional(g: ProvenanceGraph,
                   src_uuids: set[str],
                   dst_uuids: set[str],
                   hop_limit: int,
                   enforce_time: bool) -> Optional[list[Edge]]:
    """Meet-in-the-middle undirected search (information-flow / structural class).

    Returns [] when src and dst already share a node (0-hop connected).
    """
    if not src_uuids or not dst_uuids:
        return None
    if src_uuids & dst_uuids:
        return []
    fwd_cap = hop_limit - hop_limit // 2
    bwd_cap = hop_limit // 2
    fwd = _grow_frontier(g, src_uuids, fwd_cap, enforce_time, forward=True)
    bwd = _grow_frontier(g, dst_uuids, bwd_cap, enforce_time, forward=False)

    best: Optional[tuple[int, str]] = None
    for node, fs in fwd.items():
        bs = bwd.get(node)
        if bs is None:
            continue
        if enforce_time and fs.ts != _NEG and bs.ts != _POS and fs.ts > bs.ts:
            # prefix's last edge would occur after the suffix's first edge
            continue
        total = fs.depth + bs.depth
        if total == 0:
            continue
        if best is None or total < best[0]:
            best = (total, node)
    if best is None:
        return None

    meet = best[1]
    # prefix: meet -> ... -> src, then reversed to src -> ... -> meet
    fedges: list[Edge] = []
    node = meet
    while fwd[node].edge_idx != -1:
        fedges.append(g.edges[fwd[node].edge_idx])
        node = fwd[node].parent
    fedges.reverse()
    # suffix: meet -> ... -> dst (parents already point toward dst)
    bedges: list[Edge] = []
    node = meet
    while bwd[node].edge_idx != -1:
        bedges.append(g.edges[bwd[node].edge_idx])
        node = bwd[node].parent
    return fedges + bedges


# ---------------------------------------------------------------------------
# End-to-end narrative reconstruction
# ---------------------------------------------------------------------------
@dataclass
class StageResult:
    stage: int
    seed: Seed
    found: bool
    linked_from_prev: Optional[bool]       # None if this is the first found stage
    link_kind: Optional[str] = None        # "forward" | "infoflow" | "structural" | None
    path_from_prev: list[Edge] = field(default_factory=list)
    note: str = ""


# Human-readable label per link class, strongest first.
_LINK_LABEL = {
    "forward":    "正向因果连通（时间单调、沿因果方向）",
    "infoflow":   "信息流连通（含逆向边，时间单调）",
    "structural": "结构连通（时间非单调，弱证据）",
    "budget_exceeded": "未判定：BFS 搜索触发内存预算上限被中止（非不连通，需加大预算或缩小 hop_limit 重试）",
}


def link_stages(g: ProvenanceGraph,
                src_uuids: set[str],
                dst_uuids: set[str],
                hop_limit: int) -> tuple[Optional[str], list[Edge]]:
    """
    Try to connect two entity sets, strongest link class first:
      1. forward    -- causal-direction-only, time-ordered  (_directed_forward)
      2. infoflow   -- undirected (may cross edges backward), time-ordered
      3. structural -- undirected, ignoring time
    Returns (link_kind, path). link_kind is None if unreachable within hop_limit.

    MEMORY GUARD: if any of the three BFS attempts trips the memguard RSS
    ceiling (default 20GB -- see memguard.py), we stop trying WEAKER link
    classes too (they only explore even more of the graph) and report
    link_kind="budget_exceeded" instead of letting the exception escape --
    this is what previously let one over-connected seed (e.g. "sshd" ->
    ~2000 uuids) balloon memory to ~48GB and freeze the machine.
    """
    try:
        p = _directed_forward(g, src_uuids, dst_uuids, hop_limit)
        if p is not None:
            return "forward", p
        p = _bidirectional(g, src_uuids, dst_uuids, hop_limit, enforce_time=True)
        if p is not None:
            return "infoflow", p
        p = _bidirectional(g, src_uuids, dst_uuids, hop_limit, enforce_time=False)
        if p is not None:
            return "structural", p
        return None, []
    except MemoryBudgetExceeded as exc:
        print(f"  [MEMORY GUARD] link search aborted: {exc}")
        return "budget_exceeded", []


def reconstruct_narrative(g: ProvenanceGraph,
                          hop_limit: int = 8) -> list[StageResult]:
    """
    Walk the ground-truth stages in order; for each resolved stage, try to link
    it to the previous resolved stage via link_stages (forward -> info-flow ->
    structural). Unresolved stages are reported with a diagnosis (crash-gap vs
    genuine miss). A larger hop_limit than the old forward-only search is safe
    here because the undirected link uses a bidirectional meet-in-the-middle
    search (each side only explores ~hop_limit/2 layers).
    """
    resolved = resolve_seeds(g)
    ordered = seeds_by_stage()

    results: list[StageResult] = []
    prev_uuids: Optional[set[str]] = None

    for s in ordered:
        rs = resolved[s.id]

        # crash-gap steps are unrecoverable at the STEP level regardless of
        # whether the entity trivially resolves (e.g. the sshd daemon exists all
        # day, but the injection event into it is in the audit gap). This is the
        # algorithm-independent forensic ceiling; never count it as recovered.
        if s.in_crash_gap:
            note = ("不可恢复：该步动作落在 04-06 12:08:59~14:01:12 崩溃缺口内，"
                    "审计层缺失，非提取器漏检（见讨论·取证盲区）")
            if rs.found:
                note += f"（实体本身可解析到 {len(rs.uuids)} 个 uuid，但注入/发起动作缺失）"
            results.append(StageResult(stage=s.stage, seed=s, found=False,
                                       linked_from_prev=None, note=note))
            continue

        if not rs.found:
            results.append(StageResult(
                stage=s.stage, seed=s, found=False, linked_from_prev=None,
                note="未解析：数据中未找到对应实体（需复核种子取值）"))
            continue

        linked: Optional[bool] = None
        link_kind: Optional[str] = None
        path: list[Edge] = []
        if prev_uuids is not None:
            link_kind, path = link_stages(g, prev_uuids, rs.uuids, hop_limit)
            if link_kind is None:
                linked = False
                note = "与上一阶段在图中不连通（hop 限内）"
            else:
                # forward / info-flow count as a genuine causal link; a
                # structural-only (time-broken) link is reported but not counted.
                linked = link_kind in ("forward", "infoflow")
                note = _LINK_LABEL[link_kind]
                if not path:
                    note += "（与上一阶段共享同一实体，0 跳）"
        else:
            note = "链起点"

        results.append(StageResult(stage=s.stage, seed=s, found=True,
                                    linked_from_prev=linked, link_kind=link_kind,
                                    path_from_prev=path, note=note))
        prev_uuids = rs.uuids

    return results


def format_edge(g: ProvenanceGraph, e: Edge) -> str:
    src = g.nodes.get(e.src)
    dst = g.nodes.get(e.dst)
    slabel = src.label() if src else e.src[:8]
    dlabel = dst.label() if dst else e.dst[:8]
    path = f" [{e.path}]" if e.path else ""
    return f"{slabel} --{e.etype}--> {dlabel}{path}  @{ns_to_et(e.ts)}"
