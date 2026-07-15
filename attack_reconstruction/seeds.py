"""
Custom ground-truth seed list for CADETS E3 (Nginx Backdoor w/ Drakon In-Memory),
independently re-extracted from:

    ground truth/TC_Ground_Truth_Report_E3_Update.pdf, section 3.1
        "20180406 1100 CADETS - Nginx Backdoor w/ Drakon In-Memory"

This intentionally does NOT reuse KAIROS's flat keyword lists from
evaluation.py / attack_investigation.py (which are incomplete/inconsistent
with each other and with the official report). Every entry below carries a
semantic role, causal stage, and success/failure outcome, so downstream BFS
can distinguish "attempted but failed" edges from ones that actually
propagated the compromise.

Cross-validated against `ground truth/operational_event_log.md`: the
"CADETS crashed, cause unknown, 12:20-14:00 ET" entry lines up with the
sshd injection failure (~12:04-12:08) immediately preceding it, and with a
~1h52m gap in the raw capture itself (see config.py RAW_RANGES). This is an
independent corroboration that the injection attempt likely crashed the box.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Seed:
    id: str                     # stable short id for referencing in code/graphs
    entity_type: str            # "netflow" | "file" | "subject"
    value: str                  # IP:port, file path, or process name
    role: str                   # human-readable semantic role in the attack
    stage: int                  # ordinal position in the causal chain (for BFS seeding order)
    outcome: str                # "success" | "failed" | "n/a" -- outcome IN REALITY per the PDF
    in_crash_gap: bool = False  # True if this step's defining ACTION falls in the
                                # 2018-04-06 12:08:59~14:01:12 audit crash gap and is
                                # therefore physically unrecoverable from audit data,
                                # REGARDLESS of whether the entity itself trivially
                                # resolves elsewhere (e.g. sshd the daemon exists all
                                # day, but the injection event into it is in the gap).
                                # This is the algorithm-independent forensic ceiling;
                                # see paper discussion "崩溃诱导的取证盲区" and config.py.
    notes: Optional[str] = None


SEEDS: list[Seed] = [
    Seed(
        id="exploit_src",
        entity_type="netflow",
        value="81.49.200.166:80",
        role="攻击者发起 exploit 连接（HTTP POST 打 nginx）",
        stage=1,
        outcome="success",
    ),
    Seed(
        id="nginx",
        entity_type="subject",
        value="nginx",
        role="被利用的初始进程",
        stage=1,
        outcome="success",
    ),
    Seed(
        id="shellcode_server",
        entity_type="netflow",
        value="78.205.235.65:80",
        role="nginx 被控后连接取 shellcode",
        stage=2,
        outcome="success",
    ),
    Seed(
        id="loader_drakon_src",
        entity_type="netflow",
        value="200.36.109.214:80",
        role="投递 loaderDrakon",
        stage=3,
        outcome="success",
    ),
    Seed(
        id="drakon_bin_src",
        entity_type="netflow",
        value="139.123.0.113:80",
        role="投递 drakon.freebsd.x64（即 vUgefal 二进制）",
        stage=4,
        outcome="success",
    ),
    Seed(
        id="vugefal_dropped_path",
        entity_type="file",
        value="/tmp/vUgefal",
        role="drakon 可执行文件落地路径",
        stage=5,
        outcome="success",
    ),
    Seed(
        id="vugefal_root_process",
        entity_type="subject",
        value="vUgefal",
        role="elevate 后的 root 进程，后续所有恶意动作的发起点",
        stage=6,
        outcome="success",
    ),
    Seed(
        id="netrecon_fail_1a",
        entity_type="netflow",
        value="154.145.113.18:80",
        role="netrecon 尝试①（失败）——PDF 'Event Log' 小节写法",
        stage=7,
        outcome="failed",
        in_crash_gap=True,
        notes="Official PDF has a self-inconsistent digit between its Event "
              "Log section and Addresses table for this IP (2nd/4th octet "
              "differs: 154.145 vs 154.143). Both variants kept as OR-seeds. "
              "Confirmed 0 hits in raw data (byte-level exhaustive): this step "
              "is in the crash gap, not a missed spelling.",
    ),
    Seed(
        id="netrecon_fail_1b",
        entity_type="netflow",
        value="154.143.113.18:80",
        role="netrecon 尝试①（失败）——PDF 'Addresses' 小节写法",
        stage=7,
        outcome="failed",
        in_crash_gap=True,
        notes="See netrecon_fail_1a note — same event, two spellings in the "
              "source PDF. Also 0 hits (crash gap).",
    ),
    Seed(
        id="netrecon_success",
        entity_type="netflow",
        value="61.167.39.128:80",
        role="netrecon 尝试②（成功）",
        stage=8,
        outcome="success",
    ),
    Seed(
        id="libdrakon_src",
        entity_type="netflow",
        value="152.111.159.139:80",
        role="投递 libdrakon.freebsd.x64.so",
        stage=9,
        outcome="success",
        in_crash_gap=True,
        notes="Succeeded in reality per the PDF, but 0 hits in raw data: the "
              "delivery falls inside the crash gap, so it is unrecoverable from "
              "audit regardless of extractor quality.",
    ),
    Seed(
        id="libdrakon_dropped_path",
        entity_type="file",
        value="/var/log/devc",
        role="libdrakon.so 落地路径，用于注入",
        stage=10,
        outcome="success",
    ),
    Seed(
        id="sshd_inject_target",
        entity_type="subject",
        value="sshd",
        role="注入目标（PID 809），注入失败；紧随其后 CADETS 系统崩溃"
             "（12:20-14:00 ET，见 operational_event_log.md），推测为因果关联",
        stage=11,
        outcome="failed",
        in_crash_gap=True,
        notes="pid=809 per PDF. NOTE: the sshd *daemon* trivially resolves (it "
              "runs all day, ~1900 pids), but the INJECTION event into it is in "
              "the crash gap -> the step is unrecoverable even though the entity "
              "exists. Do not count entity-resolution as step-recovery here.",
    ),
]


def seeds_by_stage() -> list[Seed]:
    return sorted(SEEDS, key=lambda s: s.stage)


def seed_values_by_type() -> dict[str, set[str]]:
    """Convenience lookup: entity_type -> set of raw values, for quick membership tests."""
    out: dict[str, set[str]] = {}
    for s in SEEDS:
        out.setdefault(s.entity_type, set()).add(s.value)
    return out
