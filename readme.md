# ExpansionSim

Simple 2D space expansion visualizer.

Requirements
- Python 3.8+
- See `requirements.txt`

To tart
1. Install dependencies:
   pip install -r requirements.txt
2. Run the simulator:
   python sim2d.py

Controls
- SPACE: pause / resume simulation
- +/- : increase / decrease dot size
- S: save snapshot to `snapshots/`
- ESC or window close: quit

Files
- `sim2d.py` — simulation logic and example setup
- `ui.py` — HUD/graph and rendering runner
- `requirements.txt` — Python dependencies
- `snapshots/` — JSON snapshots written during runs

Future plans:
- Save other variables to snapshots
- Visualise and replay old snapshots
- Better snapshot filing
- Add in redshift calculations
- Add in different cosmologies
- Add in early universe properties.