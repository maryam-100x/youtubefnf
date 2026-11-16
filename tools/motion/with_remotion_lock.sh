#!/usr/bin/env bash
# Any Remotion command (a render, proof stills, a probe) as the one Remotion job: it waits for its turn among every chat's heavy jobs
# (tools/pipeline/heavy.py: a render runs alone, no cut-out, finish or other render beside it, no headless browser of another tool),
# holds a ticket for the command, drops it after. Run it in the background, from tools/motion:
#   bash with_remotion_lock.sh "<what>" <command> [args...]
#   e.g. bash with_remotion_lock.sh "proof stills" env QA_COMP=ShortTemplate node stills.mjs <dir> 0.5 0 60
. "$(dirname "${BASH_SOURCE[0]}")/../common/paths.sh"
HEAVY_PY="$REPO/tools/pipeline/heavy.py"
TICKETS="$MEDIA/tmp/heavy"
what=$1; shift
# the ticket names the process that holds it: on Windows (Git Bash / MSYS) the shell's Windows pid, elsewhere its own pid
if [ -r "/proc/$$/winpid" ]; then mypid=$(cat /proc/$$/winpid); else mypid=$$; fi
"$PIPE" "$HEAVY_PY" take render "$what" "$mypid" || exit 1
echo "remotion free at $(date +%H:%M:%S) (ticket $TICKETS/$mypid.json): $what"
"$@"
rc=$?
# the job's leftovers in the temp folder (browser profiles, bundles), cleared while the ticket is still held
SWEEP="$REPO/tools/pipeline/rtmp_sweep.py"
[ -f "$SWEEP" ] && "$PIPE" "$SWEEP" --min-age 0 --quiet
rm -f "$TICKETS/$mypid.json"
echo "ticket dropped $(date +%H:%M:%S), exit $rc"
exit $rc
