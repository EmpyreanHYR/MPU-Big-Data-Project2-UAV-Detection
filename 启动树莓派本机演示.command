#!/bin/zsh
set -e
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv-gui/bin/python ]]; then
  echo 'Install GUI dependencies first / 请先按 docs/GUI.md 安装依赖。'
  exit 1
fi
exec .venv-gui/bin/python scripts/launch_pi_gui.py "$@"
