# GUI configurations / 界面配置

Copy templates into the ignored `outputs/` directory before filling in real paths.
Run commands from the repository root. Paths inside configurations are relative
to the working directory unless absolute. Tokens belong in the GUI or
`PINP2_GUI_TOKEN`, never in a configuration committed to Git.

| Template | Copy to | Purpose |
|---|---|---|
| [h10-profile.example.json](h10-profile.example.json) | `outputs/gui_h10_profile.json` | SSH launcher; the source video is on the client |
| [pi-local.example.json](pi-local.example.json) | `outputs/gui_pi_local.json` | Native Pi GUI; source media and model are already on the Pi |

For a device-free generated fixture, use `scripts/prepare_gui_smoke_demo.py`.
It creates both `demo.json` (12-image replay) and `timestamp_demo.json`
(one synthetic timestamp filtering example). It never supplies model predictions.

See the [reproduction guide](../../docs/GUI_REPRODUCIBILITY.md) for installation,
model prerequisites and checks, and the [GUI guide](../../docs/GUI.md) for controls.
