#!/bin/zsh
set -e
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv-gui/bin/python ]]; then
  echo 'Install the GUI environment first / 请先按 docs/GUI.md 安装 GUI 环境。'
  read -k 1 '?Press any key to exit / 按任意键退出'
  exit 1
fi
exec .venv-gui/bin/python scripts/run_live_gui.py "$@"
