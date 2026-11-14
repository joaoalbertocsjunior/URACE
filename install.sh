#!/usr/bin/env sh
# URACE installer — Linux, macOS, Windows (WSL)
# Usage: curl -fsSL https://raw.githubusercontent.com/joaoalbertocsjunior/URACE/main/install.sh | sh

set -e

URACE_VERSION="0.7.0"
VENV_DIR="${HOME}/.urace"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=11

# ── colour helpers ────────────────────────────────────────────────────────────
if [ -t 1 ]; then
  GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; RESET='\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; RESET=''
fi
info() { printf "${GREEN}[urace]${RESET} %s\n" "$*"; }
warn() { printf "${YELLOW}[urace]${RESET} %s\n" "$*"; }
die()  { printf "${RED}[urace] error:${RESET} %s\n" "$*" >&2; exit 1; }

# ── OS detection ──────────────────────────────────────────────────────────────
detect_os() {
  case "$(uname -s)" in
    Linux*)           OS=linux ;;
    Darwin*)          OS=macos ;;
    MINGW*|MSYS*|CYGWIN*) OS=windows_shell ;;
    *)                OS=unknown ;;
  esac
}

# ── Python version check ──────────────────────────────────────────────────────
find_python() {
  for cmd in python3 python python3.13 python3.12 python3.11; do
    if command -v "$cmd" >/dev/null 2>&1; then
      _ver=$("$cmd" -c "import sys; print(sys.version_info.major, sys.version_info.minor)" 2>/dev/null) || continue
      _major=$(echo "$_ver" | cut -d' ' -f1)
      _minor=$(echo "$_ver" | cut -d' ' -f2)
      if [ "$_major" -gt "$MIN_PYTHON_MAJOR" ] || \
         { [ "$_major" -eq "$MIN_PYTHON_MAJOR" ] && [ "$_minor" -ge "$MIN_PYTHON_MINOR" ]; }; then
        PYTHON_CMD="$cmd"
        return 0
      fi
    fi
  done
  return 1
}

# ── install via pipx (cleanest — handles PEP 668 automatically) ───────────────
try_pipx() {
  if command -v pipx >/dev/null 2>&1; then
    info "Installing via pipx..."
    pipx install "urace==${URACE_VERSION}" || pipx upgrade urace
    return 0
  fi
  return 1
}

# ── install into a dedicated venv at ~/.urace ─────────────────────────────────
install_venv() {
  info "Creating dedicated venv at ${VENV_DIR}..."
  "$PYTHON_CMD" -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install --quiet "urace==${URACE_VERSION}"

  # Wire up the launcher
  URACE_BIN="${VENV_DIR}/bin/urace"

  # Add to shell rc if not already present
  _export_line="export PATH=\"${VENV_DIR}/bin:\$PATH\""
  for rc in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.profile"; do
    if [ -f "$rc" ] && ! grep -qF "${VENV_DIR}/bin" "$rc" 2>/dev/null; then
      printf '\n# URACE\n%s\n' "${_export_line}" >> "$rc"
      info "Added PATH entry to ${rc}"
    fi
  done

  warn "Run this once in your current shell, or open a new terminal:"
  warn "  ${_export_line}"
}

# ── install inside an already-active venv ─────────────────────────────────────
install_active_venv() {
  info "Active venv detected — installing directly..."
  "$PYTHON_CMD" -m pip install --quiet "urace==${URACE_VERSION}"
}

# ── verify ────────────────────────────────────────────────────────────────────
verify() {
  _bin="${1:-urace}"
  if "$_bin" --version >/dev/null 2>&1 || command -v urace >/dev/null 2>&1; then
    info "urace ${URACE_VERSION} installed."
  else
    info "urace ${URACE_VERSION} installed (restart shell or source rc to use)."
  fi
}

# ── main ──────────────────────────────────────────────────────────────────────
main() {
  detect_os

  if [ "$OS" = "windows_shell" ]; then
    warn "Windows detected (non-WSL shell). Use WSL, or install directly:"
    warn "  pip install urace==${URACE_VERSION}"
    warn "  npm install -g urace-cli@${URACE_VERSION}"
    exit 0
  fi

  info "Installing URACE ${URACE_VERSION} on ${OS}..."

  if ! find_python; then
    die "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ not found.
  Linux:  sudo apt install python3-full  (or dnf/pacman/zypper)
  macOS:  brew install python  (or https://python.org)"
  fi

  info "Using ${PYTHON_CMD} ($("$PYTHON_CMD" --version 2>&1))"

  # Already inside a venv — install directly, no workarounds needed
  if "$PYTHON_CMD" -c "import sys; sys.exit(0 if hasattr(sys, 'real_prefix') or sys.base_prefix != sys.prefix else 1)" 2>/dev/null; then
    install_active_venv
    verify
  # pipx available — use it (handles PEP 668, Debian/Ubuntu, externally-managed)
  elif try_pipx; then
    verify
  # Fall back: create ~/.urace venv
  else
    install_venv
    verify "${VENV_DIR}/bin/urace"
  fi

  info ""
  info "Next steps:"
  info "  export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY"
  info "  urace start"
  info "  urace"
  info ""
  info "Full docs: https://github.com/joaoalbertocsjunior/URACE"
}

main "$@"
