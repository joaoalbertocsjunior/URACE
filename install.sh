#!/usr/bin/env sh
# URACE installer — downloads the pre-built binary or builds from source.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/urace/urace/main/install.sh | sh
#   sh install.sh [--prefix /usr/local] [--version 0.9.3]
#
# Installs to PREFIX/bin (default: ~/.local/bin).
# Falls back to `cargo install urace` if no pre-built binary is available.

set -e

REPO="urace/urace"
PREFIX="${INSTALL_PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
REQUESTED_VERSION="${URACE_VERSION:-latest}"

if [ -t 1 ]; then
  GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; NC=''
fi
info()  { printf "${GREEN}[urace]${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}[urace]${NC} %s\n" "$*"; }
error() { printf "${RED}[urace]${NC} %s\n" "$*" >&2; exit 1; }

# Parse flags
while [ $# -gt 0 ]; do
  case "$1" in
    --prefix)  PREFIX="$2"; BIN_DIR="$PREFIX/bin"; shift 2 ;;
    --version) REQUESTED_VERSION="$2"; shift 2 ;;
    *) error "Unknown flag: $1" ;;
  esac
done

detect_target() {
  _os="$(uname -s)"
  _arch="$(uname -m)"
  case "$_os" in
    Linux)
      case "$_arch" in
        x86_64)  echo "x86_64-unknown-linux-musl" ;;
        aarch64) echo "aarch64-unknown-linux-musl" ;;
        armv7l)  echo "armv7-unknown-linux-musleabihf" ;;
        *)       echo "" ;;
      esac ;;
    Darwin)
      case "$_arch" in
        x86_64)  echo "x86_64-apple-darwin" ;;
        arm64)   echo "aarch64-apple-darwin" ;;
        *)       echo "" ;;
      esac ;;
    MINGW*|CYGWIN*|MSYS*)
      echo "x86_64-pc-windows-msvc" ;;
    *)
      echo "" ;;
  esac
}

install_from_release() {
  _target="$(detect_target)"
  [ -z "$_target" ] && return 1

  if [ "$REQUESTED_VERSION" = "latest" ]; then
    _version="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
      | grep '"tag_name"' | sed 's/.*"tag_name": "\(.*\)".*/\1/')"
  else
    _version="$REQUESTED_VERSION"
  fi
  [ -z "$_version" ] && return 1

  _archive="urace-${_version}-${_target}.tar.gz"
  _url="https://github.com/$REPO/releases/download/${_version}/${_archive}"
  _tmp="$(mktemp -d)"

  info "Downloading urace $_version for $_target..."
  if ! curl -fsSL "$_url" | tar -xz -C "$_tmp" 2>/dev/null; then
    warn "Pre-built binary not found for $_target — falling back to cargo install"
    rm -rf "$_tmp"
    return 1
  fi

  mkdir -p "$BIN_DIR"
  install -m 755 "$_tmp/urace" "$BIN_DIR/urace"
  rm -rf "$_tmp"
  info "Installed urace $_version to $BIN_DIR/urace"
  return 0
}

install_from_cargo() {
  if ! command -v cargo >/dev/null 2>&1; then
    error "cargo not found. Install Rust first: https://rustup.rs — then re-run this script."
  fi
  info "Building from source via cargo (this takes a few minutes)..."
  if [ "$REQUESTED_VERSION" = "latest" ]; then
    cargo install urace --root "$PREFIX" --quiet
  else
    cargo install urace --version "$REQUESTED_VERSION" --root "$PREFIX" --quiet
  fi
  info "Installed urace to $BIN_DIR/urace"
}

main() {
  info "Installing URACE..."

  install_from_release || install_from_cargo

  # PATH hint if needed
  case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
      warn "Add $BIN_DIR to your PATH:"
      warn "  export PATH=\"\$PATH:$BIN_DIR\""
      for _rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$_rc" ] && ! grep -qF "$BIN_DIR" "$_rc" 2>/dev/null; then
          printf '\n# URACE\nexport PATH="$PATH:%s"\n' "$BIN_DIR" >> "$_rc"
          info "Added PATH entry to $_rc"
          break
        fi
      done ;;
  esac

  info ""
  info "Run: urace --help"
  info "Docs: https://github.com/urace/urace"
}

main "$@"
