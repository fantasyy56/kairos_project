#!/bin/bash
# Independent, detached memory watchdog.
#
# WHY THIS SCRIPT EXISTS (as opposed to relying only on memguard.py):
#   1. memguard.py can only check its own process's RSS at specific
#      checkpoints inside reconstruct.py's own code -- if a checkpoint is
#      missed (as happened once already) or the process hangs in a single
#      C-level call (e.g. a huge dict resize) with no Python bytecode
#      running, the in-process guard never gets a chance to fire.
#   2. CodeBuddy itself (the IDE/agent host) can ALSO balloon in memory
#      (observed 32GB) and nothing inside reconstruct.py can ever watch
#      that. It needs to be watched externally.
#   3. This script is launched with `setsid` so it is NOT a child of the
#      current shell/session. If this terminal, this CodeBuddy conversation,
#      or the whole CodeBuddy app is closed/killed/restarted, this watchdog
#      keeps running untouched -- exactly the property needed to guard
#      against a CodeBuddy memory blowup, since something has to survive
#      CodeBuddy itself to act on it.
#
# This machine has only 16GB physical RAM + 8GB swap (confirmed via
# `sysctl vm.swapusage` / `memory_pressure`), so budgets are deliberately
# conservative -- leaving headroom for the OS + other apps + CodeBuddy.
#
# Usage:
#   setsid nohup ./watchdog.sh > /tmp/watchdog.log 2>&1 &
#
# Env overrides:
#   RECON_KILL_GB      RSS budget for reconstruct.py before we kill it (default 6)
#   CODEBUDDY_WARN_GB  RSS-sum budget for all "CodeBuddy CN" processes before
#                       we warn (default 10)
#   POLL_SECONDS        polling interval (default 5)

set -u

RECON_KILL_GB="${RECON_KILL_GB:-6}"
CODEBUDDY_WARN_GB="${CODEBUDDY_WARN_GB:-10}"
POLL_SECONDS="${POLL_SECONDS:-5}"
LOGFILE="${WATCHDOG_LOG:-/tmp/watchdog.log}"

RECON_KILL_KB=$(( $(printf '%.0f' "$(echo "$RECON_KILL_GB * 1024 * 1024" | bc)") ))
CODEBUDDY_WARN_KB=$(( $(printf '%.0f' "$(echo "$CODEBUDDY_WARN_GB * 1024 * 1024" | bc)") ))

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

log "=== watchdog started (pid=$$, detached) ==="
log "reconstruct.py kill threshold: ${RECON_KILL_GB}GB RSS"
log "CodeBuddy CN warn threshold:   ${CODEBUDDY_WARN_GB}GB RSS (sum of all its processes)"
log "poll interval: ${POLL_SECONDS}s"

CB_LAST_WARN_TS=0

while true; do
    sleep "$POLL_SECONDS"

    # ---- 1. reconstruct.py: kill directly if it exceeds budget ----
    for pid in $(pgrep -f "python3?.*reconstruct\.py" 2>/dev/null); do
        rss_kb=$(ps -o rss= -p "$pid" 2>/dev/null | tr -d ' ')
        [ -z "$rss_kb" ] && continue
        rss_gb=$(echo "scale=2; $rss_kb/1024/1024" | bc)
        if [ "$rss_kb" -gt "$RECON_KILL_KB" ]; then
            log "!!! reconstruct.py pid=$pid RSS=${rss_gb}GB > ${RECON_KILL_GB}GB budget -- KILLING NOW"
            kill -TERM "$pid" 2>/dev/null
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                log "    pid=$pid did not exit after SIGTERM, sending SIGKILL"
                kill -9 "$pid" 2>/dev/null
            fi
            log "    pid=$pid terminated by watchdog"
        fi
    done

    # ---- 2. CodeBuddy CN: sum RSS across all its processes, warn only ----
    cb_total_kb=$(ps aux 2>/dev/null | grep "CodeBuddy CN" | grep -v grep | awk '{s+=$6} END {print s+0}')
    if [ "$cb_total_kb" -gt "$CODEBUDDY_WARN_KB" ]; then
        now_ts=$(date +%s)
        # rate-limit the warning to once per 60s so it doesn't spam
        if [ $(( now_ts - CB_LAST_WARN_TS )) -ge 60 ]; then
            cb_total_gb=$(echo "scale=2; $cb_total_kb/1024/1024" | bc)
            log "!!! CodeBuddy CN total RSS=${cb_total_gb}GB > ${CODEBUDDY_WARN_GB}GB -- MANUAL RESTART RECOMMENDED"
            osascript -e "display notification \"CodeBuddy 内存占用已达 ${cb_total_gb}GB，建议尽快重启\" with title \"内存看门狗警告\" sound name \"Basso\"" 2>/dev/null
            CB_LAST_WARN_TS=$now_ts
        fi
    fi
done
