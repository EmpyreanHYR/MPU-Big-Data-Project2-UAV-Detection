#!/bin/zsh
set -e
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv-gui/bin/python ]]; then
  echo '请先按 docs/GUI.md 安装独立 GUI 环境。'
  read -k 1 '?按任意键退出'
  exit 1
fi
exec .venv-gui/bin/python scripts/run_gui.py "$@"
