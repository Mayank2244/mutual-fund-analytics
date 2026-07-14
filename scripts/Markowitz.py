"""
markowitz.py
============
B4 Bonus — Markowitz Efficient Frontier Portfolio Optimisation
for 5 selected funds across different equity categories.

Methodology:
  1. Compute daily returns for 5 selected funds
  2. Calculate expected returns, covariance matrix
  3. Generate 10,000 random portfolios (Monte Carlo)
  4. Compute efficient frontier using scipy optimization
  5. Find: Minimum Variance Portfolio, Maximum Sharpe Portfolio
  6. Plot efficient frontier with uncertainty bands
  7. Save all results to CSV

Deliverables:
  markowitz_results.csv       -> project root
  reports/chart_efficient_frontier.png
  reports/chart_portfolio_weights.png
  reports/chart_correlation_heatmap.png

Run:
    python markowitz.py
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
# PROC         = "data/processed"
# REP          = "reports"
from pathlib import Path

BASE_DIR = Path(__file__).parent
PROC     = BASE_DIR / "data" / "processed"
REP      = BASE_DIR / "reports"
N_PORTFOLIOS = 10000       # random portfolios to simulate
TRADING_DAYS = 252
RF_RATE      = 0.065       # risk-free rate 6.5% (RBI repo proxy)
SEED         = 42

os.makedirs(REP, exist_ok=True)
np.random.seed(SEED)

# ─────────────────────────────────────────────────────────────
# STEP 1 — Load data and select 5 funds
# ─────────────────────────────────────────────────────────────
print("=" * 65)
print("  B4 BONUS — Markowitz Efficient Frontier")
print("=" * 65)

fm  = pd.read_csv(f"{PROC}/01_fund_master.csv")
nav = pd.read_csv(f"{PROC}/02_nav_history.csv", parse_dates=["date"])

nav_wide  = nav.pivot_table(
    index="date", columns="amfi_code", values="nav"
).sort_index()
daily_ret = nav_wide.pct_change().dropna(how="all")

# 5 funds — one per major equity category for diversification
FUND_SELECTION = {
    119551: {"name": "SBI Bluechip Regular",        "category": "Large Cap"},
    100033: {"name": "HDFC Mid-Cap Opportunities",  "category": "Mid Cap"},
    119598: {"name": "SBI Small Cap Regular",       "category": "Small Cap"},
    120843: {"name": "Kotak Flexicap Regular",      "category": "Flexi Cap"},
    148569: {"name": "Mirae Asset Tax Saver",       "category": "ELSS"},
}

CODES = list(FUND_SELECTION.keys())
NAMES = [FUND_SELECTION[c]["name"]     for c in CODES]
CATS  = [FUND_SELECTION[c]["category"] for c in CODES]
N     = len(CODES)

# Align returns
ret_df = daily_ret[CODES].dropna()
ret_df.columns = NAMES

print(f"\n  Selected Funds ({N}):")
print(f"  {'Fund':<35} {'Category':<15} {'Ann Return':>11} {'Ann Vol':>9}")
print("  " + "-"*73)
for i, name in enumerate(NAMES):
    r = ret_df[name]
    ann_ret = r.mean() * TRADING_DAYS * 100
    ann_vol = r.std()  * np.sqrt(TRADING_DAYS) * 100
    print(f"  {name:<35} {CATS[i]:<15} {ann_ret:>9.2f}%  {ann_vol:>7.2f}%")

print(f"\n  Data: {len(ret_df):,} trading days")

# ─────────────────────────────────────────────────────────────
# STEP 2 — Expected returns and covariance matrix
# ─────────────────────────────────────────────────────────────

# Annualised expected returns vector (μ)
mu = ret_df.mean() * TRADING_DAYS

# Annualised covariance matrix (Σ)
cov = ret_df.cov() * TRADING_DAYS

print(f"\n  Expected Annual Returns (μ):")
for name, val in mu.items():
    print(f"    {name:<35} : {val*100:.2f}%")

print(f"\n  Covariance Matrix (Σ) — diagonal = variance:")
print(cov.round(6).to_string())

# ─────────────────────────────────────────────────────────────
# STEP 3 — Portfolio metrics helper functions
# ─────────────────────────────────────────────────────────────

def portfolio_return(weights: np.ndarray) -> float:
    """Annualised portfolio return = w^T × μ"""
    return float(np.dot(weights, mu))


def portfolio_volatility(weights: np.ndarray) -> float:
    """Annualised portfolio volatility = sqrt(w^T × Σ × w)"""
    return float(np.sqrt(weights @ cov.values @ weights))


def portfolio_sharpe(weights: np.ndarray) -> float:
    """Sharpe ratio = (Rp - Rf) / σp"""
    rp = portfolio_return(weights)
    sp = portfolio_volatility(weights)
    return (rp - RF_RATE) / sp if sp > 0 else 0.0


# ─────────────────────────────────────────────────────────────
# STEP 4 — Generate N_PORTFOLIOS random portfolios
# ─────────────────────────────────────────────────────────────
print(f"\n  Generating {N_PORTFOLIOS:,} random portfolios ...")

rand_returns = np.zeros(N_PORTFOLIOS)
rand_vols    = np.zeros(N_PORTFOLIOS)
rand_sharpes = np.zeros(N_PORTFOLIOS)
rand_weights = np.zeros((N_PORTFOLIOS, N))

for i in range(N_PORTFOLIOS):
    w = np.random.dirichlet(np.ones(N))   # random weights summing to 1
    rand_weights[i]  = w
    rand_returns[i]  = portfolio_return(w)
    rand_vols[i]     = portfolio_volatility(w)
    rand_sharpes[i]  = portfolio_sharpe(w)

print(f"  Done. Return range: {rand_returns.min()*100:.1f}% – "
      f"{rand_returns.max()*100:.1f}%")
print(f"        Vol range   : {rand_vols.min()*100:.1f}% – "
      f"{rand_vols.max()*100:.1f}%")
print(f"        Sharpe range: {rand_sharpes.min():.2f} – "
      f"{rand_sharpes.max():.2f}")


# ─────────────────────────────────────────────────────────────
# STEP 5 — Scipy optimization for efficient frontier
# ─────────────────────────────────────────────────────────────
print(f"\n  Running scipy optimization ...")

# Constraints: weights sum to 1
constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

# Bounds: 0% to 40% per fund (no short selling, max 40% concentration)
bounds = tuple((0.0, 0.40) for _ in range(N))

# Initial equal weights
w0 = np.array([1/N] * N)


def neg_sharpe(weights):
    """Negative Sharpe for minimization."""
    return -portfolio_sharpe(weights)


def min_vol(weights):
    """Portfolio volatility for minimization."""
    return portfolio_volatility(weights)


# ── A. Maximum Sharpe Ratio Portfolio ──────────────────────
res_sharpe = minimize(
    neg_sharpe, w0,
    method="SLSQP",
    bounds=bounds,
    constraints=constraints,
    options={"maxiter": 1000, "ftol": 1e-9}
)
w_max_sharpe = res_sharpe.x
w_max_sharpe = np.clip(w_max_sharpe, 0, 1)
w_max_sharpe /= w_max_sharpe.sum()

ret_max_sharpe = portfolio_return(w_max_sharpe)
vol_max_sharpe = portfolio_volatility(w_max_sharpe)
shr_max_sharpe = portfolio_sharpe(w_max_sharpe)

print(f"\n  Maximum Sharpe Portfolio:")
print(f"    Return     : {ret_max_sharpe*100:.2f}%")
print(f"    Volatility : {vol_max_sharpe*100:.2f}%")
print(f"    Sharpe     : {shr_max_sharpe:.3f}")
print(f"    Weights:")
for name, w in zip(NAMES, w_max_sharpe):
    print(f"      {name:<35} : {w*100:.1f}%")


# ── B. Minimum Variance Portfolio ──────────────────────────
res_minvol = minimize(
    min_vol, w0,
    method="SLSQP",
    bounds=bounds,
    constraints=constraints,
    options={"maxiter": 1000, "ftol": 1e-9}
)
w_min_vol = res_minvol.x
w_min_vol = np.clip(w_min_vol, 0, 1)
w_min_vol /= w_min_vol.sum()

ret_min_vol = portfolio_return(w_min_vol)
vol_min_vol = portfolio_volatility(w_min_vol)
shr_min_vol = portfolio_sharpe(w_min_vol)

print(f"\n  Minimum Variance Portfolio:")
print(f"    Return     : {ret_min_vol*100:.2f}%")
print(f"    Volatility : {vol_min_vol*100:.2f}%")
print(f"    Sharpe     : {shr_min_vol:.3f}")
print(f"    Weights:")
for name, w in zip(NAMES, w_min_vol):
    print(f"      {name:<35} : {w*100:.1f}%")


# ── C. Efficient Frontier curve ────────────────────────────
# Find minimum variance for each target return level
target_returns = np.linspace(
    ret_min_vol + 0.005,
    mu.max() * 0.95,
    50
)
ef_vols    = []
ef_returns = []
ef_weights = []

for target_r in target_returns:
    cons = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1},
        {"type": "eq", "fun": lambda w, tr=target_r: portfolio_return(w) - tr},
    ]
    res = minimize(
        min_vol, w0,
        method="SLSQP",
        bounds=bounds,
        constraints=cons,
        options={"maxiter": 500, "ftol": 1e-9}
    )
    if res.success:
        ef_vols.append(portfolio_volatility(res.x))
        ef_returns.append(target_r)
        ef_weights.append(res.x)

ef_vols    = np.array(ef_vols)
ef_returns = np.array(ef_returns)

print(f"\n  Efficient frontier: {len(ef_vols)} points computed")

# ── D. Equal-weight portfolio (benchmark comparison) ───────
w_equal       = np.array([1/N] * N)
ret_equal     = portfolio_return(w_equal)
vol_equal     = portfolio_volatility(w_equal)
shr_equal     = portfolio_sharpe(w_equal)

print(f"\n  Equal-Weight Portfolio (Benchmark):")
print(f"    Return     : {ret_equal*100:.2f}%")
print(f"    Volatility : {vol_equal*100:.2f}%")
print(f"    Sharpe     : {shr_equal:.3f}")


# ─────────────────────────────────────────────────────────────
# STEP 6 — Save results CSV
# ─────────────────────────────────────────────────────────────
portfolios_summary = pd.DataFrame({
    "portfolio_type"    : ["Max Sharpe", "Min Variance", "Equal Weight"],
    "ann_return_pct"    : [ret_max_sharpe*100, ret_min_vol*100, ret_equal*100],
    "ann_volatility_pct": [vol_max_sharpe*100, vol_min_vol*100, vol_equal*100],
    "sharpe_ratio"      : [shr_max_sharpe, shr_min_vol, shr_equal],
}).round(4)

for i, name in enumerate(NAMES):
    portfolios_summary[f"weight_{name.replace(' ','_')}"] = [
        w_max_sharpe[i]*100,
        w_min_vol[i]*100,
        w_equal[i]*100,
    ]

portfolios_summary.to_csv("markowitz_results.csv", index=False)
print(f"\n  Saved -> markowitz_results.csv")


# ─────────────────────────────────────────────────────────────
# STEP 7 — Chart 1: Efficient Frontier
# ─────────────────────────────────────────────────────────────
print("\n  Building Chart 1 — Efficient Frontier ...")

fig, ax = plt.subplots(figsize=(14, 9))
fig.patch.set_facecolor("#0D1B2A")
ax.set_facecolor("#0D2137")

# Random portfolios — colored by Sharpe ratio
sc = ax.scatter(
    rand_vols * 100, rand_returns * 100,
    c=rand_sharpes, cmap="RdYlGn",
    alpha=0.4, s=8, zorder=1
)
cbar = plt.colorbar(sc, ax=ax, pad=0.02)
cbar.set_label("Sharpe Ratio", color="white", fontsize=11)
cbar.ax.yaxis.set_tick_params(color="white")
plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

# Efficient frontier line
ax.plot(
    ef_vols * 100, ef_returns * 100,
    "w-", linewidth=3, zorder=5, label="Efficient Frontier"
)

# Capital Market Line (from Rf to Max Sharpe)
x_cml = np.linspace(0, vol_max_sharpe * 100 * 1.5, 100)
y_cml = RF_RATE * 100 + shr_max_sharpe * x_cml
ax.plot(x_cml, y_cml, "--", color="#00B4D8",
        linewidth=1.8, zorder=4, label="Capital Market Line")

# Risk-free rate point
ax.scatter(0, RF_RATE * 100, marker="*",
           s=200, color="#FFD700", zorder=10,
           label=f"Risk-Free Rate ({RF_RATE*100:.1f}%)")

# Max Sharpe portfolio
ax.scatter(
    vol_max_sharpe * 100, ret_max_sharpe * 100,
    marker="*", s=500, color="#FFD700",
    zorder=10, edgecolors="black", linewidth=1,
    label=f"Max Sharpe (SR={shr_max_sharpe:.2f})"
)
ax.annotate(
    f"Max Sharpe\nSR={shr_max_sharpe:.2f}\nR={ret_max_sharpe*100:.1f}%\nσ={vol_max_sharpe*100:.1f}%",
    xy=(vol_max_sharpe*100, ret_max_sharpe*100),
    xytext=(vol_max_sharpe*100 + 1.5, ret_max_sharpe*100 + 1),
    fontsize=9, color="#FFD700", fontweight="bold",
    arrowprops=dict(arrowstyle="->", color="#FFD700", lw=1.5),
    bbox=dict(boxstyle="round,pad=0.4", fc="#0A1628",
              ec="#FFD700", alpha=0.9)
)

# Min Variance portfolio
ax.scatter(
    vol_min_vol * 100, ret_min_vol * 100,
    marker="D", s=300, color="#00B4D8",
    zorder=10, edgecolors="white", linewidth=1,
    label=f"Min Variance (σ={vol_min_vol*100:.1f}%)"
)
ax.annotate(
    f"Min Variance\nR={ret_min_vol*100:.1f}%\nσ={vol_min_vol*100:.1f}%",
    xy=(vol_min_vol*100, ret_min_vol*100),
    xytext=(vol_min_vol*100 - 4, ret_min_vol*100 + 2),
    fontsize=9, color="#00B4D8", fontweight="bold",
    arrowprops=dict(arrowstyle="->", color="#00B4D8", lw=1.5),
    bbox=dict(boxstyle="round,pad=0.4", fc="#0A1628",
              ec="#00B4D8", alpha=0.9)
)

# Equal-weight portfolio
ax.scatter(
    vol_equal * 100, ret_equal * 100,
    marker="s", s=250, color="#FF9800",
    zorder=10, edgecolors="white", linewidth=1,
    label=f"Equal Weight (20% each)"
)
ax.annotate(
    f"Equal Weight\nR={ret_equal*100:.1f}%\nσ={vol_equal*100:.1f}%",
    xy=(vol_equal*100, ret_equal*100),
    xytext=(vol_equal*100 + 1, ret_equal*100 - 3),
    fontsize=9, color="#FF9800", fontweight="bold",
    arrowprops=dict(arrowstyle="->", color="#FF9800", lw=1.5),
    bbox=dict(boxstyle="round,pad=0.4", fc="#0A1628",
              ec="#FF9800", alpha=0.9)
)

# Individual fund points
fund_colors = ["#E63946","#4CAF50","#9C27B0","#00B4D8","#FFD700"]
for i, (name, cat) in enumerate(zip(NAMES, CATS)):
    w_single  = np.eye(N)[i]
    r_single  = portfolio_return(w_single)
    v_single  = portfolio_volatility(w_single)
    ax.scatter(v_single*100, r_single*100,
               marker="^", s=200, color=fund_colors[i],
               zorder=8, edgecolors="white", linewidth=0.8)
    ax.annotate(f"{name[:20]}\n({cat})",
                xy=(v_single*100, r_single*100),
                xytext=(v_single*100 + 0.3, r_single*100 + 0.5),
                fontsize=7.5, color=fund_colors[i])

# Labels and styling
ax.set_xlabel("Annualised Volatility — Risk (%)",
              fontsize=12, color="#B0C4DE")
ax.set_ylabel("Annualised Return (%)",
              fontsize=12, color="#B0C4DE")
ax.set_title(
    "Markowitz Efficient Frontier — 5 Equity Funds\n"
    f"{N_PORTFOLIOS:,} Random Portfolios | Bounds: 0–40% per fund | "
    f"Rf = {RF_RATE*100:.1f}%",
    fontsize=14, fontweight="bold", color="white", pad=15
)
ax.tick_params(colors="#B0C4DE")
ax.legend(fontsize=9, loc="lower right", framealpha=0.3,
          labelcolor="white", facecolor="#0D1B2A",
          edgecolor="#1565C0")
for spine in ax.spines.values():
    spine.set_edgecolor("#1565C0")

# Gridlines
ax.grid(True, alpha=0.15, color="white")

plt.tight_layout()
out1 = f"{REP}/chart_efficient_frontier.png"
plt.savefig(out1, dpi=150, bbox_inches="tight", facecolor="#0D1B2A")
plt.close()
print(f"  Saved -> {out1}")


# ─────────────────────────────────────────────────────────────
# STEP 8 — Chart 2: Portfolio Weights Comparison
# ─────────────────────────────────────────────────────────────
print("  Building Chart 2 — Portfolio weights comparison ...")

fig, axes = plt.subplots(1, 3, figsize=(18, 7))
fig.patch.set_facecolor("#0D1B2A")

portfolio_data = [
    ("Maximum Sharpe", w_max_sharpe, "#FFD700",
     f"Return: {ret_max_sharpe*100:.1f}%\nVol: {vol_max_sharpe*100:.1f}%\nSharpe: {shr_max_sharpe:.2f}"),
    ("Minimum Variance", w_min_vol, "#00B4D8",
     f"Return: {ret_min_vol*100:.1f}%\nVol: {vol_min_vol*100:.1f}%\nSharpe: {shr_min_vol:.2f}"),
    ("Equal Weight", w_equal, "#FF9800",
     f"Return: {ret_equal*100:.1f}%\nVol: {vol_equal*100:.1f}%\nSharpe: {shr_equal:.2f}"),
]

short_names = [n.split(" ")[0] + "\n" + " ".join(n.split(" ")[1:3])
               for n in NAMES]

for ax, (title, weights, color, stats) in zip(axes, portfolio_data):
    ax.set_facecolor("#0D2137")

    bars = ax.bar(
        range(N), weights * 100,
        color=[fund_colors[i] for i in range(N)],
        edgecolor="white", linewidth=0.8, alpha=0.9
    )
    # Value labels on bars
    for bar, w in zip(bars, weights):
        if w > 0.005:
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + 0.5,
                    f"{w*100:.1f}%",
                    ha="center", va="bottom",
                    fontsize=10, color="white",
                    fontweight="bold")

    # Equal weight reference line
    ax.axhline(100/N, color="white", linestyle="--",
               linewidth=1.2, alpha=0.5,
               label=f"Equal weight ({100/N:.0f}%)")

    ax.set_xticks(range(N))
    ax.set_xticklabels(short_names, fontsize=8, color="#B0C4DE")
    ax.set_ylabel("Portfolio Weight (%)", fontsize=10, color="#B0C4DE")
    ax.set_title(title, fontsize=13, fontweight="bold",
                 color=color, pad=10)
    ax.set_ylim(0, 50)
    ax.tick_params(axis="y", colors="#B0C4DE")
    for sp in ax.spines.values():
        sp.set_edgecolor("#1565C0")

    # Stats annotation box
    ax.text(0.98, 0.97, stats,
            transform=ax.transAxes, fontsize=10,
            color=color, va="top", ha="right",
            bbox=dict(boxstyle="round,pad=0.5",
                      fc="#0A1628", ec=color, alpha=0.9))

fig.suptitle(
    "Portfolio Weight Allocation — Three Optimal Portfolios\n"
    "(Max Sharpe vs Min Variance vs Equal Weight)",
    fontsize=14, fontweight="bold", color="white", y=1.01
)
plt.tight_layout()
out2 = f"{REP}/chart_portfolio_weights.png"
plt.savefig(out2, dpi=150, bbox_inches="tight", facecolor="#0D1B2A")
plt.close()
print(f"  Saved -> {out2}")


# ─────────────────────────────────────────────────────────────
# STEP 9 — Chart 3: Correlation Heatmap
# ─────────────────────────────────────────────────────────────
print("  Building Chart 3 — Correlation heatmap ...")

fig, ax = plt.subplots(figsize=(9, 7))
fig.patch.set_facecolor("#0D1B2A")
ax.set_facecolor("#0D2137")

corr_matrix = ret_df.corr()
mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)

sns.heatmap(
    corr_matrix, annot=True, fmt=".3f",
    cmap="coolwarm", center=0, vmin=-1, vmax=1,
    linewidths=0.8, linecolor="#0D1B2A",
    ax=ax, cbar_kws={"shrink": 0.8,
                     "label": "Pearson Correlation"},
    annot_kws={"size": 11, "weight": "bold"}
)

ax.set_title(
    "Pairwise Correlation of Daily Returns\n"
    "(Low correlation = better diversification)",
    fontsize=13, fontweight="bold", color="white", pad=12
)
ax.tick_params(colors="#B0C4DE", labelsize=9)
plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
plt.setp(ax.get_yticklabels(), rotation=0)

# Add diversification note
fig.text(
    0.5, -0.02,
    "Note: Near-zero correlations across all pairs indicate strong "
    "diversification benefit in this portfolio",
    ha="center", fontsize=10, color="#B0C4DE", style="italic"
)

plt.tight_layout()
out3 = f"{REP}/chart_correlation_heatmap_markowitz.png"
plt.savefig(out3, dpi=150, bbox_inches="tight", facecolor="#0D1B2A")
plt.close()
print(f"  Saved -> {out3}")


# ─────────────────────────────────────────────────────────────
# STEP 10 — Final Summary
# ─────────────────────────────────────────────────────────────
print()
print("=" * 65)
print("  MARKOWITZ OPTIMISATION RESULTS")
print("=" * 65)
print(f"\n  {'Metric':<25} {'Max Sharpe':>13} {'Min Variance':>14} {'Equal Weight':>14}")
print("  " + "-"*68)
print(f"  {'Annual Return':<25} {ret_max_sharpe*100:>12.2f}%  {ret_min_vol*100:>13.2f}%  {ret_equal*100:>13.2f}%")
print(f"  {'Annual Volatility':<25} {vol_max_sharpe*100:>12.2f}%  {vol_min_vol*100:>13.2f}%  {vol_equal*100:>13.2f}%")
print(f"  {'Sharpe Ratio':<25} {shr_max_sharpe:>13.3f}  {shr_min_vol:>13.3f}  {shr_equal:>13.3f}")
print()
print(f"  {'Portfolio Weights':}")
for i, name in enumerate(NAMES):
    print(f"    {name:<35} {w_max_sharpe[i]*100:>8.1f}%   {w_min_vol[i]*100:>8.1f}%   {w_equal[i]*100:>8.1f}%")

print()
print("=" * 65)
print("  B4 COMPLETE")
print("=" * 65)
print(f"  markowitz_results.csv                    -> project root")
print(f"  chart_efficient_frontier.png             -> reports/")
print(f"  chart_portfolio_weights.png              -> reports/")
print(f"  chart_correlation_heatmap_markowitz.png  -> reports/")
print()
# print("  Git commit:")
# print('  git add markowitz.py markowitz_results.csv reports/')
# print('  git commit -m "B4: Markowitz Efficient Frontier complete"')
# print('  git push origin main')