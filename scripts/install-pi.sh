#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
data_dir="$HOME/.local/share/pokegotchi"
autostart_dir="$HOME/.config/autostart"
desktop_file="$autostart_dir/pokegotchi.desktop"

mkdir -p "$data_dir" "$autostart_dir"
python3 -m venv "$data_dir/venv"
"$data_dir/venv/bin/python" -m pip install -r "$project_dir/requirements.txt"
cp "$project_dir/scripts/pokegotchi.desktop" "$desktop_file"
awk -v project="$project_dir" -v venv="$data_dir/venv" '
    /^Exec=/ {
        print "Exec=env \"PYTHONPATH=" project "/src\" \"" venv "/bin/python\" -m pokegotchi.main"
        next
    }
    { print }
' "$desktop_file" > "$desktop_file.tmp"
mv "$desktop_file.tmp" "$desktop_file"
