#!/usr/bin/env sh
# URACE installer — Linux, macOS, Windows (WSL)
# Usage: curl -fsSL https://raw.githubusercontent.com/joaoalbertocsjunior/URACE/main/install.sh | sh

set -e

URACE_VERSION="0.7.0"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=11

# ── colour helpers ────────────────────────────────────────────────────────────
if [ -t 1 ]; then
  GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; RESET='\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; RESET=''
fi
info()    { printf "${GREEN}[urace]${RESET} %s\n" "$*"; }
warn()    { printf "${YELLOW}[urace]${RESET} %s\n" "$*"; }
die()     { printf "${RED}[urace] error:${RESET} %s\n" "$*" >&2; exit 1; }

# ── OS detection ─────────────────────────────────────────────────────────────
detect_os() {
  case "$(uname -s)" in
    Linux*)  OS=linux ;;
    Darwin*) OS=macos ;;
    MINGW*|MSYS*|CYGWIN*) OS=windows_shell ;;
    *)       OS=unknown ;;
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

# ── pip availability ──────────────────────────────────────────────────────────
find_pip() {
  if "$PYTHON_CMD" -m pip --version >/dev/null 2>&1; then
    PIP_CMD="$PYTHON_CMD -m pip"
    return 0
  fi
  return 1
}

# ── main ──────────────────────────────────────────────────────────────────────
main() {
  detect_os

  if [ "$OS" = "windows_shell" ]; then
    warn "Windows detected (non-WSL shell). For best results use WSL or run directly:"
    warn "  pip install urace==${URACE_VERSION}"
    warn "  npm install -g urace-cli@${URACE_VERSION}"
    exit 0
  fi

  info "Installing URACE ${URACE_VERSION} on ${OS}..."

  if ! find_python; then
    die "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ not found.
  Linux:  sudo apt install python3  (or dnf/pacman/zypper)
  macOS:  brew install python  (or https://python.org)"
  fi

  info "Using ${PYTHON_CMD} ($("$PYTHON_CMD" --version 2>&1))"

  if ! find_pip; then
    die "pip not found. Install it: ${PYTHON_CMD} -m ensurepip --upgrade"
  fi

  # Prefer --user install to avoid needing sudo; fall back without flag if
  # inside a virtualenv or if --user is unsupported (e.g. some CI images).
  if "$PYTHON_CMD" -c "import sys; sys.exit(0 if hasattr(sys, 'real_prefix') or sys.base_prefix != sys.prefix else 1)" 2>/dev/null; then
    PIP_FLAGS=""
    info "Virtual environment detected — installing without --user"
  else
    PIP_FLAGS="--user"
  fi

  # shellcheck disable=SC2086
  $PIP_CMD install $PIP_FLAGS "urace==${URACE_VERSION}" || \
    $PIP_CMD install "urace==${URACE_VERSION}"

  # Verify
  if command -v urace >/dev/null 2>&1; then
    info "urace $(urace --version 2>/dev/null || echo ${URACE_VERSION}) installed successfully."
  else
    # --user installs land in ~/.local/bin on Linux, ~/Library/Python/X.Y/bin on macOS
    warn "urace installed but not found in PATH."
    if [ "$OS" = "linux" ]; then
      warn "Add to PATH: export PATH=\"\$HOME/.local/bin:\$PATH\""
    elif [ "$OS" = "macos" ]; then
      _pyver=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
      warn "Add to PATH: export PATH=\"\$HOME/Library/Python/${_pyver}/bin:\$PATH\""
    fi
  fi

  info ""
  info "Next steps:"
  info "  export ANTHROPIC_API_KEY=..."
  info "  urace start"
  info "  urace"
  info ""
  info "Full docs: https://github.com/joaoalbertocsjunior/URACE"
}

main "$@"
