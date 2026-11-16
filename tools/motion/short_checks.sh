# The rest of standard/SHORTS.md's checks on a finished built Short (every check run, never the quick ones only): the 2-fps crops
# sheet, a 1-fps sheet at 200x356 (the mid-shot read: the 2-fps sheet's small cells hide a head on the edge), the phone view of frame 1,
# measure_edit, the reuse check, and headless browsers left behind. The chain before it (render, captions, score, qa_render, qa_holds,
# word sheet) covers the rest; the framing review (frame_review_at.py) and audit_short.py --cuts run before the render.
#   bash tools/motion/short_checks.sh <id> <folder> <export name with version>
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../common/paths.sh"
cd "$REPO" || exit 1
export PYTHONUTF8=1
id=$1; dir=$2; name=$3
P=$PIPE; E=$EDIT
DJ=$MEDIA/videos/$dir; F=$DJ/export/$name.mp4; R=$DJ/review/checks_$name
mkdir -p "$R"
[ -f "$F" ] || { echo "no export $F"; exit 1; }
"$FFMPEG" -hide_banner -loglevel error -y -i "$F" -vf "fps=2,scale=180:320,tile=13x4" -frames:v 1 "$R/crops_2fps.jpg"
"$FFMPEG" -hide_banner -loglevel error -y -i "$F" -vf "fps=1,scale=200:356,drawtext=text='%{pts\:hms}':fontcolor=yellow:fontsize=16:x=4:y=4:box=1:boxcolor=black@0.6,tile=10x6" -frames:v 1 "$R/mid_1fps.jpg"
"$P" tools/footage/phone_view.py "$F" 0.05 "$R/phone_frame1.png" > /dev/null 2>&1 || echo "phone view failed"
"$E" tools/qa/measure_edit.py "$F" "$R/measure" > "$R/measure.log" 2>&1 || echo "measure_edit failed"
tail -8 "$R/measure.log"
"$P" tools/motion/reuse_check.py "$id" --out "$R/reuse.md" > /dev/null 2>&1 || echo "reuse check failed"
grep -m 12 -E "^- |^## " "$R/reuse.md" 2>/dev/null
# headless browsers a render left running (they hold memory and slow the next job)
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    powershell -NoProfile -Command "\$h = @(Get-Process chrome-headless-shell,msedge -ErrorAction SilentlyContinue | Where-Object { \$_.Path -like '*remotion*' -or \$_.ProcessName -eq 'chrome-headless-shell' }); 'headless left: ' + \$h.Count" ;;
  *)
    echo "headless left: $(ps -axo command= | grep -c '[c]hrome-headless-shell')" ;;
esac
echo "-> $R"
