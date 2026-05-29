import json, pathlib
r = json.loads(pathlib.Path('logs/training/2026-05-29/191724_EURUSD_H4_exp-010/report.json').read_text())
import pprint

print('=== METRICS ===')
pprint.pprint(r['metrics'])

print()
print('=== BACKTEST ===')
pprint.pprint(r['strategyBacktest'])

print()
print('=== WALK FORWARD FOLDS ===')
for fold in r['walkForwardSelection']['foldSummaries']:
    print(f"Fold {fold['fold']}: trainRows={fold['trainRows']} valRows={fold['validationRows']}")
    for t, m in fold['thresholdMetrics'].items():
        print(f"  thr={t}: PF={m['profitFactor']:.3f}  trades={m['totalTrades']}  WR={m['winRate']:.2f}  DD={m['maxDrawdownPct']:.2f}%")

print()
print('=== WALK FORWARD SELECTION ===')
ws = r['walkForwardSelection']
print(f"threshold={ws.get('selectedThreshold')}  mode={ws.get('thresholdMode','?')}  folds={ws.get('foldCount','?')}")

print()
print('=== AVAILABLE KEYS ===')
print([k for k in r.keys()])

if 'featureImportances' in r:
    print()
    print('=== FEATURE IMPORTANCE (top 12) ===')
    fi = sorted(r['featureImportances'].items(), key=lambda x: -x[1])[:12]
    for f, v in fi:
        print(f'  {f}: {v:.4f}')
