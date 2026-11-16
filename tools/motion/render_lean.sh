#!/usr/bin/env bash
# `npx remotion render` from one bundle whose public/ is a directory junction to the public dir (lean_bundle.mjs): no copy of it per
# render (a long video's public dir can hold several GB, and a copy per preview fills the disk). Same arguments as `npx remotion render`
# after the entry point, minus --public-dir. Run it inside with_remotion_lock.sh, from tools/motion:
#   bash with_remotion_lock.sh "<video> preview" bash render_lean.sh <the video's public dir> <Composition> <out.mp4> --muted \
#        --frames=a-b --scale=0.6666666666666666 --gl=angle --concurrency=6
# The bundle is deleted when the render ends, however it ends. QA_COPY=1 renders the old way (src/index.ts + --public-dir, a copy).
# (--gl=angle is the Windows GPU path; on macOS leave --gl out or use the platform's default.)
. "$(dirname "${BASH_SOURCE[0]}")/../common/paths.sh"
cd "$(dirname "$0")" || exit 1
pub=$1
shift
if [ "$QA_COPY" = "1" ]; then
  exec npx remotion render src/index.ts "$@" "--public-dir=$pub"
fi
mkdir -p "$MEDIA/tmp"
export TEMP="$MEDIA/tmp" TMP="$MEDIA/tmp" TMPDIR="$MEDIA/tmp"
line=$("$NODE" lean_bundle.mjs make "$pub" | grep '^{"serveUrl"' | tail -1)
url=$(printf '%s' "$line" | "$NODE" -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{try{console.log(JSON.parse(s).serveUrl)}catch(e){}})')
if [ -z "$url" ]; then
  echo "render_lean.sh: the lean bundle failed (rerun with QA_COPY=1 for the old copy)" >&2
  exit 1
fi
trap '"$NODE" lean_bundle.mjs clean "$url" >/dev/null' EXIT
echo "render_lean.sh: one bundle, public dir by junction: $url"
npx remotion render "$url" "$@"
