"""
End-to-end attack-chain reconstruction for CADETS E3 (Nginx Backdoor w/ Drakon).

Pipeline:
  1. build_graph()          -- one streaming pass over the raw shards
  2. resolve_seeds()        -- structured seeds (seeds.py) -> concrete node uuids
  3. reconstruct_narrative()-- link resolved stages into a causal chain via
                               time-respecting BFS
  4. report + JSON dump     -- human-readable narrative and a machine-readable
                               reconstruction (nodes/edges/stage table) for the
                               downstream sequence model and for the paper's
                               attack-narrative-recovery experiment (GAP_S6_CAN).

Run:  python3 reconstruct.py
      python3 reconstruct.py --sample 200000        # smoke test: bounded
                                                      # memory/time, but NEVER
                                                      # reaches the attack
                                                      # window (see Memory.md
                                                      # §14/§15) -- code-path
                                                      # only, 0 chain links
                                                      # expected.
      python3 reconstruct.py --focus-attack           # smoke test that DOES
                                                       # contain the attack
                                                       # window: narrows to the
                                                       # tail of the pre-crash
                                                       # shard + head of the
                                                       # post-crash shard,
                                                       # default 1.5GB budget.
      python3 reconstruct.py --focus-attack 2000000000 # same, but with an
                                                       # explicit byte budget
                                                       # (bigger budget -> more
                                                       # real surrounding
                                                       # context included).
                                                       # Meaningful for testing
                                                       # chain-linking logic,
                                                       # NOT for full recall.
Out:  prints a stage-by-stage report; writes reconstruction.json alongside
      (reconstruction.sample.json when --sample/--focus-attack is used, so a
      real run's output is never clobbered by a smoke-test run).
"""

from __future__ import annotations

import argparse
import json
import os

from config import ns_to_et, GRAPH_EDGE_WINDOW_ET, attack_focused_ranges
from graph_builder import build_graph
from chains import (
    resolve_seeds, reconstruct_narrative, format_edge, StageResult,
)
from memguard import memory_budget_gb


def _print_seed_resolution(g, resolved) -> None:
    print("\n" + "=" * 72)
    print("SEED RESOLUTION (structured seed -> concrete node uuid)")
    print("=" * 72)
    for s in sorted(resolved.values(), key=lambda r: r.seed.stage):
        seed = s.seed
        tag = "OK " if s.found else "MISS"
        n = len(s.uuids)
        sample = next(iter(s.uuids))[:12] + "..." if s.uuids else "-"
        print(f"  [{tag}] stage{seed.stage:>2} {seed.id:22s} {seed.value:20s} "
              f"-> {n} uuid(s) {sample}  ({seed.outcome})")


def _print_narrative(g, results: list[StageResult]) -> None:
    print("\n" + "=" * 72)
    print("RECONSTRUCTED ATTACK NARRATIVE (stage by stage)")
    print("=" * 72)
    for r in results:
        head = f"stage {r.stage:>2}  {r.seed.role}"
        if not r.found:
            print(f"\n[✗ 不可恢复] {head}")
            print(f"           {r.note}")
            continue
        link = ""
        if r.linked_from_prev is True:
            kind = {"forward": "正向因果", "infoflow": "信息流(含逆向边)"}.get(
                r.link_kind, "因果")
            link = f"(← 与上一阶段{kind}连通，{len(r.path_from_prev)} 跳)"
        elif r.linked_from_prev is False:
            if r.link_kind is None:
                link = "(← 未与上一阶段连通)"
            elif r.link_kind == "budget_exceeded":
                link = "(← 搜索因触发内存预算上限被中止，未判定)"
            else:
                link = "(← 仅结构连通，时间非单调)"
        print(f"\n[✓ 已恢复] {head} {link}")
        if r.note and r.linked_from_prev is not True:
            print(f"           {r.note}")
        for e in r.path_from_prev:
            print(f"           {format_edge(g, e)}")


def _dump_json(g, resolved, results: list[StageResult], out_path: str) -> None:
    def edge_dict(e):
        return {
            "src": e.src, "dst": e.dst,
            "src_label": g.nodes[e.src].label() if e.src in g.nodes else None,
            "dst_label": g.nodes[e.dst].label() if e.dst in g.nodes else None,
            "type": e.etype, "category": e.category,
            "ts": e.ts, "ts_et": ns_to_et(e.ts), "path": e.path,
            "event_uuid": e.event_uuid,
        }

    payload = {
        "graph_stats": g.stats,
        "edge_window_et": GRAPH_EDGE_WINDOW_ET,
        "seeds": [
            {
                "id": r.seed.id, "stage": r.seed.stage, "value": r.seed.value,
                "role": r.seed.role, "outcome": r.seed.outcome,
                "resolved": r.found, "uuids": sorted(r.uuids),
            }
            for r in sorted(resolved.values(), key=lambda x: x.seed.stage)
        ],
        "stages": [
            {
                "stage": r.stage, "seed_id": r.seed.id, "role": r.seed.role,
                "found": r.found, "linked_from_prev": r.linked_from_prev,
                "link_kind": r.link_kind,
                "note": r.note,
                "path": [edge_dict(e) for e in r.path_from_prev],
            }
            for r in results
        ],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n[written] {out_path}")


def _print_summary(results: list[StageResult]) -> None:
    # Collapse to DISTINCT ground-truth stages (a stage may carry several seed
    # spellings, e.g. the two netrecon-fail IPs, or exploit_src+nginx). Step-level
    # accounting is what the paper's forensic-ceiling argument is about.
    stages: dict[int, list[StageResult]] = {}
    for r in results:
        stages.setdefault(r.stage, []).append(r)

    total = len(stages)
    gap_stages = sorted(st for st, rs in stages.items()
                        if all(r.seed.in_crash_gap for r in rs))
    recoverable = total - len(gap_stages)
    # a recoverable stage counts as recovered if any of its seeds resolved
    recovered = sum(1 for st, rs in stages.items()
                    if st not in gap_stages and any(r.found for r in rs))
    linked = sum(1 for st, rs in stages.items()
                 if any(r.linked_from_prev is True for r in rs))
    fwd = sum(1 for st, rs in stages.items()
              if any(r.link_kind == "forward" for r in rs))
    info = sum(1 for st, rs in stages.items()
               if any(r.link_kind == "infoflow" for r in rs))
    struct = sum(1 for st, rs in stages.items()
                 if any(r.link_kind == "structural" for r in rs))

    print("\n" + "=" * 72)
    print("SUMMARY (step-level, over distinct ground-truth stages)")
    print("=" * 72)
    print(f"  distinct ground-truth stages   : {total}")
    print(f"  unrecoverable (crash gap)      : {len(gap_stages)}  stages {gap_stages}")
    print(f"  recoverable ceiling            : {recoverable}")
    print(f"  of which recovered in data     : {recovered}")
    print(f"  causally linked to prev stage  : {linked}  "
          f"(正向 {fwd} + 信息流 {info}；另有结构连通 {struct})")
    print(f"  data-recoverability ceiling  ρ_data = {recoverable}/{total} "
          f"= {recoverable / total:.2f}")
    print("  (ρ_data 是与算法无关的数据上界；崩溃缺口吞掉了本步骤后 3 个动作，")
    print("   见论文讨论·崩溃诱导的取证盲区小节)")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--sample", type=int, default=None, metavar="N",
        help="SMOKE TEST: cap each raw shard range to the FIRST N lines. "
             "Bounds memory/runtime, but for RAW_RANGES[1] the attack window "
             "starts ~96%% of the way through a ~22.5h/~4M-line range, so no "
             "N short of nearly the full range ever reaches it -- expect 0 "
             "chain links. Only proves the code path doesn't crash. Use "
             "--focus-attack to actually exercise chain-linking on real "
             "attack data.")
    p.add_argument(
        "--focus-attack", type=int, nargs="?", const=1_500_000_000, default=None,
        metavar="BYTE_BUDGET",
        help="SMOKE TEST: narrow to just the tail of the pre-crash shard "
             "(ending at the crash, 12:08:59) + head of the post-crash shard "
             "(starting at recovery, 14:01:12), spending BYTE_BUDGET total "
             "bytes across the two (default 1.5GB, 60%% pre-crash / 40%% "
             "post-crash). This DOES contain the real attack-window edges, "
             "and a bigger budget buys strictly more real surrounding "
             "context (never unrelated data), so it meaningfully tests the "
             "BFS chain-linking logic under whatever memory budget you give "
             "it -- but drops day5-early/day7-late entirely, so it is not a "
             "full-range seed-resolution test.")
    p.add_argument(
        "--memory-budget-gb", type=float, default=None, metavar="GB",
        help="Abort a graph-build or BFS chain-link step (not the whole "
             "process) once THIS PROCESS's own RSS exceeds GB, instead of "
             "growing unbounded until the OS starts swapping/thrashing "
             "(observed to freeze the machine at ~48GB used). Default 20.0 "
             "(memguard.DEFAULT_MEMORY_BUDGET_GB); can also be set via the "
             "RECON_MEMORY_BUDGET_GB env var. An aborted link step is "
             "reported per-stage as 'budget_exceeded' rather than crashing "
             "the run.")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    sample = args.sample
    if sample is not None and sample <= 0:
        raise SystemExit("--sample must be a positive integer")

    if args.memory_budget_gb is not None:
        if args.memory_budget_gb <= 0:
            raise SystemExit("--memory-budget-gb must be a positive number")
        os.environ["RECON_MEMORY_BUDGET_GB"] = str(args.memory_budget_gb)
    print(f"[memory guard] budget = {memory_budget_gb():.1f}GB "
          f"(this process's own RSS; abort-and-continue, not a hard kill)")

    ranges = None
    if args.focus_attack is not None:
        ranges = attack_focused_ranges(byte_budget=args.focus_attack)
        print(f"[FOCUS-ATTACK MODE] narrowed to {len(ranges)} byte ranges "
              f"around the attack window (byte budget "
              f"{args.focus_attack:,}) -- day5-early/day7-late dropped "
              f"entirely:")
        for r in ranges:
            print(f"    {r['path']}\n      [{r['start']}:{r['end']}]  {r['covers']}")

    out_path = os.path.join(
        os.path.dirname(__file__),
        "reconstruction.sample.json" if (sample or ranges) else "reconstruction.json",
    )

    print("Building provenance graph (one streaming pass over raw shards)...")
    print(f"edge window: {GRAPH_EDGE_WINDOW_ET}")
    g = build_graph(max_lines_per_range=sample, ranges=ranges)

    resolved = resolve_seeds(g)
    _print_seed_resolution(g, resolved)

    results = reconstruct_narrative(g)
    _print_narrative(g, results)
    _print_summary(results)
    _dump_json(g, resolved, results, out_path)


if __name__ == "__main__":
    main()
