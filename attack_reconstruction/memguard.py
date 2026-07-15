"""
Shared process-memory watchdog utility.

Long BFS-style graph searches (chains.py's _grow_frontier / _directed_forward)
can fan out into a memory blow-up much faster than one would expect from the
underlying graph size -- e.g. a "stage" seed whose exec-name identity (like
`sshd`) actually matches ~2000 distinct process nodes accumulated over 3 days
turns into ~2000 simultaneously-expanded BFS roots, and if even one of those
happens to be a busy node, the frontier can balloon into tens of GB within a
few seconds -- well past the point where recovering the memory later helps,
because by then the OS itself has usually started swapping/thrashing (which
has previously frozen this machine solid at ~48GB used).

check_budget() is meant to be called periodically (every ~1-2k inner-loop
iterations is cheap enough: a single getrusage() syscall) from any
memory-sensitive hot loop. Hitting the budget raises MemoryBudgetExceeded,
which callers should treat as a normal, catchable "search gave up, budget
exceeded" outcome -- NOT let propagate into a crash -- so the rest of the
reconstruction can keep going and report that one stage/link as unresolved
for this reason, instead of taking the whole run (and potentially the whole
machine) down with it.
"""

from __future__ import annotations

import os
import resource
import sys
from typing import Optional

# Default ceiling, in GB of this PROCESS's own resident memory (not system-
# wide). 20GB matches the user's explicit ask: stop well before the ~48GB
# level that previously froze the machine, leaving headroom for the OS/other
# apps. Override with the RECON_MEMORY_BUDGET_GB env var (reconstruct.py's
# --memory-budget-gb flag sets this) if a different ceiling is needed.
DEFAULT_MEMORY_BUDGET_GB = 20.0
_ENV_VAR = "RECON_MEMORY_BUDGET_GB"


def memory_budget_gb() -> float:
    """Resolve the active memory budget: env var override, else the default."""
    raw = os.environ.get(_ENV_VAR)
    if raw:
        try:
            val = float(raw)
            if val > 0:
                return val
        except ValueError:
            pass
    return DEFAULT_MEMORY_BUDGET_GB


def rss_gb() -> float:
    """Current process peak resident set size, in GB.

    ru_maxrss's UNIT is platform-defined (not a function of how large the
    value happens to be): macOS always reports bytes, Linux always reports
    KB. We branch on sys.platform rather than guessing from the magnitude of
    the number -- a magnitude-based heuristic used earlier in this project
    misclassified any macOS RSS under ~9.3GB as "must be KB", inflating
    *displayed* memory by ~1024x (a log-cosmetics bug only; it never affected
    real memory usage, but it's exactly the kind of mistake that would make
    a "stop at 20GB" guard either fire immediately or never fire at all, so
    it must not be repeated here).
    """
    kb_or_b = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = (1024 ** 3) if sys.platform == "darwin" else (1024 ** 2)
    return kb_or_b / divisor


class MemoryBudgetExceeded(RuntimeError):
    """Raised by check_budget() when this process's RSS crosses the ceiling.

    Soft/catchable by design -- see module docstring.
    """

    def __init__(self, rss: float, budget: float):
        self.rss = rss
        self.budget = budget
        super().__init__(
            f"memory budget exceeded: this process's RSS={rss:.2f}GB > "
            f"budget={budget:.2f}GB")


def check_budget(budget_gb: Optional[float] = None) -> None:
    """Raise MemoryBudgetExceeded if current RSS exceeds budget_gb.

    Cheap enough (one getrusage syscall, no I/O) to call every 1-2k
    iterations from any hot loop that can plausibly fan out unboundedly.
    """
    budget = budget_gb if budget_gb is not None else memory_budget_gb()
    rss = rss_gb()
    if rss > budget:
        raise MemoryBudgetExceeded(rss, budget)
