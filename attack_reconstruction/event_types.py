"""
Semantic classification of CDM EventType values.

Per the agreed design (see chat history, point 4): we do NOT hardcode a
whitelist that silently drops event types not on the list (that's the KAIROS
approach and it's the exact failure mode we're avoiding — it can silently cut
the causal chain at "elevate"/"inject", the two most important edges).

Instead:
  1. scan_event_types.py enumerates every EventType actually present in our
     target byte ranges (data-driven discovery, no assumptions).
  2. classify() below buckets *any* type (known or newly discovered) into a
     semantic category via keyword matching, rather than exact-name lookup.
  3. Every category is kept in the graph by default. Categories exist for
     analysis/visualization grouping (e.g. "which edges are control-flow vs
     data-flow"), not for filtering.

If classify() ever returns "other", that's a signal to go look at the type
name and add a keyword rule — not a signal to drop the edge.
"""

from __future__ import annotations

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    # privilege change -- this is where "elevate" almost certainly lives
    # (confirmed present in real data as EVENT_CHANGE_PRINCIPAL, 89,746
    # occurrences in the day5-7 window -- KAIROS's whitelist has NO category
    # for this at all, so it would have silently dropped every elevate edge).
    "privilege_change": ("CHANGE_PRINCIPAL",),

    # process/thread lifecycle -- control flow
    "control_flow": ("EXECUTE", "FORK", "CLONE", "EXIT", "UNIT", "MODIFY_PROCESS"),

    # memory mapping / shared memory / dynamic loading -- likely home of
    # "inject" (mmap+mprotect into another process, or shared-memory-based
    # injection). Confirmed present: EVENT_MMAP (1.4M), EVENT_MPROTECT (4,907).
    "memory_injection": ("MMAP", "MPROTECT", "LOADLIBRARY", "SHM"),

    # file data flow
    "file_io": (
        "READ", "WRITE", "OPEN", "CLOSE", "RENAME", "UNLINK", "LINK",
        "TRUNCATE", "MODIFY_FILE_ATTRIBUTES", "CREATE_OBJECT", "UMOUNT",
        "ADD_OBJECT_ATTRIBUTE",
    ),

    # network data flow
    "network_io": (
        "CONNECT", "ACCEPT", "SENDTO", "SENDMSG", "RECVFROM", "RECVMSG",
        "FLOWS_TO", "BIND",
    ),

    # registry (Windows-only in CDM, CADETS is FreeBSD -- kept for completeness)
    "registry": ("REGISTRYKEY",),

    # misc lifecycle / bookkeeping
    "other_known": ("SERVICEINSTALL", "BOOT", "LOGIN", "LOGOUT", "CHECK_FILE_ATTRIBUTES"),

    # low-level fd/seek/signal bookkeeping -- kept, not dropped, but rarely
    # causally interesting on its own (still shows up in "other" reporting
    # below so nothing is silently hidden)
    "syscall_bookkeeping": ("FCNTL", "LSEEK", "SIGNAL"),
}


def classify(event_type: str) -> str:
    """
    event_type: e.g. "EVENT_EXECUTE". Returns one of CATEGORY_KEYWORDS' keys,
    or "other" if no keyword matched (never drop -- just tag as unclassified
    so it surfaces in reporting for a manual look).
    """
    name = event_type.upper()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name:
                return category
    return "other"
