# paths.sh: the same places as tools/common/paths.py, for bash scripts. Source it at the top of a script:
#   . "$(dirname "${BASH_SOURCE[0]}")/../common/paths.sh"        (from a script in tools/<area>/)
# Sets REPO, MEDIA, PIPE (the pipeline python), EDIT (the editing python), VISION, ACCENT, SYNTH (music made in code), FFMPEG,
# FFPROBE, NODE, NPX, UV (the studio's own copies in MEDIA/apps), and the studio's environment: its program folders first on PATH,
# every cache inside MEDIA (the same as paths.py's studio_env).
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
APPS="$MEDIA/apps"; CACHE="$MEDIA/cache"
# the studio's own programs (tools/setup/apps.py), first on PATH: never the computer's own uv, Node or ffmpeg
if [ $_win = 1 ]; then
  _a="$(cygpath -u "$APPS" 2>/dev/null || echo "$APPS")"; _bins="$_a/uv:$_a/node:$_a/ffmpeg/bin"; _x=.exe; _c=.cmd
else
  _bins="$APPS/uv:$APPS/node/bin:$APPS/ffmpeg/bin"; _x=; _c=
fi
_app() { _v="$(_key "$1")"; if [ -n "$_v" ]; then echo "$_v"; elif [ -e "$APPS/$2" ]; then echo "$APPS/$2"; else echo "$3"; fi; }
if [ $_win = 1 ]; then _nb=node; else _nb=node/bin; fi
FFMPEG="$(_app ffmpeg "ffmpeg/bin/ffmpeg$_x" ffmpeg)"
FFPROBE="$(_app ffprobe "ffmpeg/bin/ffprobe$_x" ffprobe)"
NODE="$(_app node "$_nb/node$_x" node)"
NPX="$(_app npx "$_nb/npx$_c" npx)"
UV="$(_app uv "uv/uv$_x" uv)"
case ":$PATH:" in *":$_bins:"*) ;; *) PATH="$_bins:$PATH" ;; esac
# every cache inside MEDIA (the same variables as paths.py's studio_env)
UV_CACHE_DIR="$CACHE/uv"; UV_PYTHON_INSTALL_DIR="$APPS/python"; UV_MANAGED_PYTHON=1; UV_NO_CONFIG=1
UV_PYTHON_INSTALL_BIN=0; UV_PYTHON_INSTALL_REGISTRY=0; UV_CREDENTIALS_DIR="$MEDIA/secrets/uv"
npm_config_cache="$CACHE/npm"; npm_config_userconfig="$APPS/node/studio.npmrc"; npm_config_update_notifier=false; npm_config_fund=false
HF_HOME="$MEDIA/models/hf"; TORCH_HOME="$MEDIA/models/torch"; U2NET_HOME="$MEDIA/models/u2net"
YOLO_CONFIG_DIR="$CACHE/ultralytics"; MPLCONFIGDIR="$CACHE/matplotlib"; XDG_CACHE_HOME="$CACHE"
export REPO MEDIA PIPE EDIT VISION ACCENT SYNTH FFMPEG FFPROBE NODE NPX UV APPS CACHE PATH UV_CACHE_DIR UV_PYTHON_INSTALL_DIR \
  UV_MANAGED_PYTHON UV_NO_CONFIG UV_PYTHON_INSTALL_BIN UV_PYTHON_INSTALL_REGISTRY UV_CREDENTIALS_DIR npm_config_cache npm_config_userconfig npm_config_update_notifier npm_config_fund HF_HOME TORCH_HOME \
  U2NET_HOME YOLO_CONFIG_DIR MPLCONFIGDIR XDG_CACHE_HOME
