import json, sys

path = sys.argv[1]
d = json.load(open(path))

wf = d["walkForwardSelection"]
print("CV Folds:")
for fs in wf.get("foldSummaries", []):
    fold = fs["fold"]
    m45 = fs["thresholdMetrics"].get("0.45", {})
    m50 = fs["thresholdMetrics"].get("0.50", {})
    t45 = m45.get("totalTrades", 0)
    pf45 = round(m45.get("profitFactor", 0), 3)
    dd45 = round(m45.get("maxDrawdownPct", 0), 2)
    t50 = m50.get("totalTrades", 0)
    pf50 = round(m50.get("profitFactor", 0), 3)
    print(f"  Fold {fold}:  @0.45 trades={t45} PF={pf45} DD={dd45}%  |  @0.50 trades={t50} PF={pf50}")

print()
for t in wf.get("thresholdDiagnostics", []):
    thr = t["threshold"]
    mPF = round(t["medianProfitFactor"], 3)
    mDD = round(t["medianMaxDrawdownPct"], 2)
    mT = t["medianTrades"]
    print(f"  CV thr={thr}: medPF={mPF}  medTrades={mT}  medDD={mDD}%")

print()
print("Selected threshold:", wf.get("selectedThreshold"))

sb = d["strategyBacktest"]
print(f"TEST: trades={sb['totalTrades']}  WR={sb['winRate']:.1%}  PF={sb['profitFactor']:.3f}  DD={sb['maxDrawdownPct']:.2f}%")
