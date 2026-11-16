# paths.sh: the same places as tools/common/paths.py, for bash scripts. Source it at the top of a script:
#   . "$(dirname "${BASH_SOURCE[0]}")/../common/paths.sh"        (from a script in tools/<area>/)
# Sets REPO, MEDIA, PIPE (the pipeline python), EDIT (the editing python), VISION, ACCENT, SYNTH (music made in code), FFMPEG, NODE.
# MEDIA and the venvs come from config/paths.toml (key = "value" lines), else the defaults paths.py uses.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
_cfg="$REPO/config/paths.toml"
_key() { [ -f "$_cfg" ] && sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$_cfg" | head -1; }
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) _win=1 ;; *) _win=0 ;; esac
MEDIA="$(_key media)"; [ -n "$MEDIA" ] || { [ $_win = 1 ] && MEDIA="C:/Studio" || MEDIA="$HOME/Studio"; }
MEDIA="${MEDIA/#\~/$HOME}"
_py() { [ $_win = 1 ] && echo "$1/Scripts/python.exe" || echo "$1/bin/python"; }
_v="$(_key venv_pipeline)"; PIPE="$(_py "${_v:-$REPO/tools/.venv}")"
_v="$(_key venv_edit)";     EDIT="$(_py "${_v:-$MEDIA/envs/edit}")"
_v="$(_key venv_vision)";   VISION="$(_py "${_v:-$MEDIA/envs/vision}")"
_v="$(_key venv_accent)";   ACCENT="$(_py "${_v:-$MEDIA/envs/accent}")"
_v="$(_key venv_synth)";    SYNTH="$(_py "${_v:-$MEDIA/envs/synth}")"
FFMPEG="$(_key ffmpeg)"; FFMPEG="${FFMPEG:-ffmpeg}"
NODE="$(_key node)"; NODE="${NODE:-node}"
export REPO MEDIA PIPE EDIT VISION ACCENT SYNTH FFMPEG NODE
