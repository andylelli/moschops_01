import json, pathlib, pprint

# Load EXP-010 report
r010 = json.loads(pathlib.Path('logs/training/2026-05-29/191724_EURUSD_H4_exp-010/report.json').read_text())
print("=== EXP-010 KEYS ===")
print(list(r010.keys()))

# Check walkForwardSelection structure
ws = r010['walkForwardSelection']
print("\n=== WALK FORWARD SELECTION KEYS ===")
print(list(ws.keys()))

# Find feature importances somewhere
for run_dir in pathlib.Path('logs/training/2026-05-29').iterdir():
    if 'exp-010' in run_dir.name:
        files = list(run_dir.iterdir())
        print(f"\n=== EXP-010 DIR FILES ===")
        for f in files:
            print(f"  {f.name}  ({f.stat().st_size} bytes)")
        break
