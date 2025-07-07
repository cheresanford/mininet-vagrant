#!/usr/bin/env python3
import argparse, csv, glob, os, numpy as np, matplotlib.pyplot as plt

def read_tput(csvfile):
    # iperf -y C: coluna 8 (index 7) = Mbps
    return [float(r[7]) for r in csv.reader(open(csvfile)) if r]

def jain(xs):
    s1 = sum(xs); s2 = sum(x*x for x in xs); n = len(xs)
    return (s1**2) / (n * s2) if s2 else 0

parser = argparse.ArgumentParser()
parser.add_argument('--dirs', nargs='+', required=True)
parser.add_argument('--out',  default='comp_summary.png')
args = parser.parse_args()

fig, ax = plt.subplots()
for d in args.dirs:
    flows = sorted(glob.glob(os.path.join(d, '*.csv')))
    thr = [np.mean(read_tput(f)) for f in flows]
    if not thr: continue
    fairness = jain(thr)
    efficiency = sum(thr)
    ax.scatter(fairness, efficiency, s=120, label=os.path.basename(d))

ax.set_xlabel('Fairness (Jain index)')
ax.set_ylabel('Efficiency (Σ throughput, Mbps)')
ax.set_xlim(0,1.05); ax.set_ylim(bottom=0)
ax.grid(True); ax.legend()
plt.savefig(args.out, bbox_inches='tight')
print('=>', args.out)
