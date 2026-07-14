"""
monte_carlo.py
==============
B3 Bonus — Monte Carlo Simulation
Projects NAV growth over 5 years with uncertainty bands
for all 40 schemes using Geometric Brownian Motion (GBM)

Deliverables:
  - monte_carlo_results.csv  → project root
  - reports/chart_monte_carlo_top5.png
  - reports/chart_monte_carlo_all_funds.png

Run:
    python monte_carlo.py
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
# PROC            = "data/processed"
# REP             = "reports"
from pathlib import Path

BASE_DIR = Path(__file__).parent
PROC     = BASE_DIR / "data" / "processed"
REP      = BASE_DIR / "reports"
SIMULATIONS     = 1000          # number of Monte Carlo paths
HORIZON_YEARS   = 5             # projection horizon
TRADING_DAYS    = 252           # trading days per year
HORIZON_DAYS    = TRADING_DAYS * HORIZON_YEARS
CONFIDENCE_BANDS = [5, 25, 50, 75, 95]   # percentiles to plot
SEED            = 42            # reproducibility

os.makedirs(REP, exist_ok=True)
np.random.seed(SEED)

# ─────────────────────────────────────────────────────────────
# STEP 1 — Load and prepare data
# ─────────────────────────────────────────────────────────────
print("="*65)
print("  B3 BONUS — Monte Carlo NAV Simulation")
print("="*65)
print(f"\n  Simulations     : {SIMULATIONS:,}")
print(f"  Horizon         : {HORIZON_YEARS} years ({HORIZON_DAYS} trading days)")
print(f"  Confidence bands: {CONFIDENCE_BANDS}")
print()

fm  = pd.read_csv(f"{PROC}/01_fund_master.csv")
nav = pd.read_csv(f"{PROC}/02_nav_history.csv", parse_dates=["date"])

nav_wide   = nav.pivot_table(index="date", columns="amfi_code",
                              values="nav").sort_index()
daily_ret  = nav_wide.pct_change().dropna(how="all")

print(f"  Loaded: {nav_wide.shape[1]} schemes | "
      f"{len(daily_ret)} trading days of returns")


# ─────────────────────────────────────────────────────────────
# STEP 2 — Monte Carlo via Geometric Brownian Motion (GBM)
# ─────────────────────────────────────────────────────────────
def simulate_gbm(mu_daily: float, sigma_daily: float,
                 s0: float, n_days: int, n_sims: int) -> np.ndarray:
    """
    Geometric Brownian Motion simulation.

    GBM formula:
      S(t+1) = S(t) × exp((μ - σ²/2)Δt + σ√Δt × Z)
      where Z ~ N(0,1)

    Parameters:
        mu_daily    : mean daily log return
        sigma_daily : std of daily log returns
        s0          : starting NAV
        n_days      : number of days to simulate
        n_sims      : number of simulation paths

    Returns:
        np.ndarray of shape (n_days+1, n_sims)
        Row 0 = s0 for all simulations
    """
    dt = 1   # daily steps

    # Daily drift and diffusion terms
    drift     = (mu_daily - 0.5 * sigma_daily**2) * dt
    diffusion = sigma_daily * np.sqrt(dt)

    # Random standard normal shocks: shape (n_days, n_sims)
    Z = np.random.standard_normal((n_days, n_sims))

    # Daily returns: e^(drift + diffusion*Z)
    daily_factors = np.exp(drift + diffusion * Z)

    # Build price paths: shape (n_days+1, n_sims)
    paths = np.empty((n_days + 1, n_sims))
    paths[0] = s0

    for t in range(1, n_days + 1):
        paths[t] = paths[t-1] * daily_factors[t-1]

    return paths


# ─────────────────────────────────────────────────────────────
# STEP 3 — Run simulation for all 40 schemes
# ─────────────────────────────────────────────────────────────
print("\n  Running simulations ...")
print(f"  {'Scheme':<40} {'μ (ann%)':<12} {'σ (ann%)':<12} "
      f"{'S0':>8} {'P50 (5yr)':>12} {'P5 (5yr)':>11} {'P95 (5yr)':>11}")
print("  " + "-"*107)

results = []

for code_id in nav_wide.columns:
    ret    = daily_ret[code_id].dropna()
    series = nav_wide[code_id].dropna()

    if len(ret) < 30:
        continue

    # Log return parameters (GBM uses log returns)
    log_ret   = np.log(1 + ret)
    mu_daily  = log_ret.mean()
    sig_daily = log_ret.std()
    s0        = series.iloc[-1]

    # Annualised for display
    mu_ann  = mu_daily  * TRADING_DAYS * 100
    sig_ann = sig_daily * np.sqrt(TRADING_DAYS) * 100

    # Run GBM
    paths = simulate_gbm(mu_daily, sig_daily, s0,
                         HORIZON_DAYS, SIMULATIONS)

    # Final NAV distribution (last row = day 1260)
    final_navs = paths[-1]

    # Percentiles of final NAV
    pcts = {p: np.percentile(final_navs, p) for p in CONFIDENCE_BANDS}

    # Expected return and risk metrics
    expected_return_pct = ((pcts[50] / s0) - 1) * 100
    prob_profit = (final_navs > s0).mean() * 100
    max_sim_nav = final_navs.max()
    min_sim_nav = final_navs.min()

    # Get fund metadata
    fm_row = fm[fm["amfi_code"] == code_id]
    name      = fm_row["scheme_name"].values[0]   if len(fm_row) else "Unknown"
    fund_house= fm_row["fund_house"].values[0]    if len(fm_row) else ""
    sub_cat   = fm_row["sub_category"].values[0]  if len(fm_row) else ""
    plan      = fm_row["plan"].values[0]           if len(fm_row) else ""
    risk_cat  = fm_row["risk_category"].values[0] if len(fm_row) else ""

    print(f"  {name[:40]:<40} {mu_ann:>10.2f}%  {sig_ann:>10.2f}%  "
          f"{s0:>8.2f}  {pcts[50]:>10.2f}  {pcts[5]:>10.2f}  {pcts[95]:>10.2f}")

    results.append({
        "amfi_code"         : code_id,
        "scheme_name"       : name,
        "fund_house"        : fund_house,
        "sub_category"      : sub_cat,
        "plan"              : plan,
        "risk_category"     : risk_cat,
        "latest_nav"        : round(s0, 4),
        "mu_annual_pct"     : round(mu_ann, 3),
        "sigma_annual_pct"  : round(sig_ann, 3),
        "p5_nav_5yr"        : round(pcts[5],  2),
        "p25_nav_5yr"       : round(pcts[25], 2),
        "p50_nav_5yr"       : round(pcts[50], 2),
        "p75_nav_5yr"       : round(pcts[75], 2),
        "p95_nav_5yr"       : round(pcts[95], 2),
        "expected_return_5yr_pct": round(expected_return_pct, 2),
        "prob_profit_pct"   : round(prob_profit, 1),
        "max_simulated_nav" : round(max_sim_nav, 2),
        "min_simulated_nav" : round(min_sim_nav, 2),
        "simulations"       : SIMULATIONS,
    })

results_df = pd.DataFrame(results).sort_values(
    "expected_return_5yr_pct", ascending=False
).reset_index(drop=True)
results_df.index = results_df.index + 1

# Save CSV deliverable
results_df.to_csv("monte_carlo_results.csv", index=False)
print(f"\n  Saved -> monte_carlo_results.csv ({len(results_df)} funds)")


# ─────────────────────────────────────────────────────────────
# STEP 4 — Chart 1: Top 5 Funds — Full Path with Bands
# ─────────────────────────────────────────────────────────────
print("\n  Building Chart 1 — Top 5 funds with uncertainty bands ...")

top5 = results_df.head(5)
colors = ["#2196F3","#4CAF50","#E63946","#FF9800","#9C27B0"]

fig, axes = plt.subplots(1, 5, figsize=(22, 8))
fig.patch.set_facecolor("#0D1B2A")

for i, (_, row) in enumerate(top5.iterrows()):
    ax = axes[i]
    ax.set_facecolor("#0D2137")

    # Re-run GBM for this fund to get full paths
    fm_row  = fm[fm["amfi_code"] == row["amfi_code"]]
    ret     = daily_ret[row["amfi_code"]].dropna()
    log_ret = np.log(1 + ret)
    paths   = simulate_gbm(
        log_ret.mean(), log_ret.std(),
        row["latest_nav"], HORIZON_DAYS, SIMULATIONS
    )

    # Time axis in years
    t = np.linspace(0, HORIZON_YEARS, HORIZON_DAYS + 1)

    # Plot percentile bands
    p5  = np.percentile(paths, 5,  axis=1)
    p25 = np.percentile(paths, 25, axis=1)
    p50 = np.percentile(paths, 50, axis=1)
    p75 = np.percentile(paths, 75, axis=1)
    p95 = np.percentile(paths, 95, axis=1)

    # Outer band (5–95%)
    ax.fill_between(t, p5, p95, alpha=0.12,
                    color=colors[i], label="5–95% band")
    # Inner band (25–75%)
    ax.fill_between(t, p25, p75, alpha=0.25,
                    color=colors[i], label="25–75% band")
    # Median path
    ax.plot(t, p50, color=colors[i], linewidth=2.5,
            label="Median (P50)")
    # Extremes
    ax.plot(t, p5,  color=colors[i], linewidth=0.8,
            linestyle=":", alpha=0.6)
    ax.plot(t, p95, color=colors[i], linewidth=0.8,
            linestyle=":", alpha=0.6)
    # Starting NAV line
    ax.axhline(row["latest_nav"], color="white",
               linestyle="--", linewidth=1, alpha=0.5,
               label=f"Current NAV: ₹{row['latest_nav']:.0f}")

    # Annotations
    ax.annotate(f"P95: ₹{p95[-1]:.0f}",
                xy=(HORIZON_YEARS, p95[-1]),
                xytext=(HORIZON_YEARS-0.8, p95[-1]),
                fontsize=7, color="lime",
                arrowprops=dict(arrowstyle="->", color="lime", lw=0.8))
    ax.annotate(f"P50: ₹{p50[-1]:.0f}",
                xy=(HORIZON_YEARS, p50[-1]),
                xytext=(HORIZON_YEARS-0.8, p50[-1]),
                fontsize=7, color=colors[i],
                arrowprops=dict(arrowstyle="->", color=colors[i], lw=0.8))
    ax.annotate(f"P5: ₹{p5[-1]:.0f}",
                xy=(HORIZON_YEARS, p5[-1]),
                xytext=(HORIZON_YEARS-0.8, p5[-1]),
                fontsize=7, color="tomato",
                arrowprops=dict(arrowstyle="->", color="tomato", lw=0.8))

    # Styling
    short_name = row["scheme_name"].replace(" Direct Growth","").replace(" Regular Growth","")
    ax.set_title(f"{short_name[:28]}\n({row['sub_category']})",
                 fontsize=9, color="white", fontweight="bold", pad=8)
    ax.set_xlabel("Years", fontsize=9, color="#B0C4DE")
    ax.set_ylabel("NAV (₹)", fontsize=9, color="#B0C4DE")
    ax.tick_params(colors="#B0C4DE", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#1565C0")

    # Stats box
    stats_text = (f"μ = {row['mu_annual_pct']:.1f}%/yr\n"
                  f"σ = {row['sigma_annual_pct']:.1f}%/yr\n"
                  f"P(profit) = {row['prob_profit_pct']:.0f}%")
    ax.text(0.03, 0.97, stats_text,
            transform=ax.transAxes, fontsize=7.5,
            color="#00B4D8", verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="#0A1628", alpha=0.8,
                      edgecolor="#1565C0"))

fig.suptitle(
    f"Monte Carlo NAV Projection — Top 5 Funds | "
    f"{SIMULATIONS:,} Simulations × {HORIZON_YEARS}-Year Horizon\n"
    "Geometric Brownian Motion | Bands: 5th–95th percentile",
    fontsize=14, fontweight="bold", color="white", y=1.01
)
plt.tight_layout()
out1 = f"{REP}/chart_monte_carlo_top5.png"
plt.savefig(out1, dpi=150, bbox_inches="tight",
            facecolor="#0D1B2A")
plt.close()
print(f"  Saved -> {out1}")


# ─────────────────────────────────────────────────────────────
# STEP 5 — Chart 2: All 40 Funds — Expected Return vs Risk
# ─────────────────────────────────────────────────────────────
print("  Building Chart 2 — Expected return vs risk scatter ...")

fig, axes = plt.subplots(1, 2, figsize=(18, 8))
fig.patch.set_facecolor("#0D1B2A")

# Scatter: Expected 5yr Return vs Annual Sigma
ax1 = axes[0]
ax1.set_facecolor("#0D2137")

sub_cats = results_df["sub_category"].unique()
cmap     = plt.cm.Set2(np.linspace(0, 1, len(sub_cats)))
cat_color = dict(zip(sub_cats, cmap))

for _, row in results_df.iterrows():
    ax1.scatter(
        row["sigma_annual_pct"],
        row["expected_return_5yr_pct"],
        s=180, alpha=0.85,
        color=cat_color[row["sub_category"]],
        edgecolors="white", linewidth=0.5
    )
    ax1.annotate(
        row["scheme_name"][:15],
        (row["sigma_annual_pct"], row["expected_return_5yr_pct"]),
        fontsize=5.5, color="#B0C4DE",
        xytext=(3, 3), textcoords="offset points"
    )

# Quadrant lines
ax1.axhline(results_df["expected_return_5yr_pct"].mean(),
            color="yellow", linestyle="--", linewidth=1,
            label="Avg Expected Return")
ax1.axvline(results_df["sigma_annual_pct"].mean(),
            color="orange", linestyle="--", linewidth=1,
            label="Avg Risk")

# Quadrant labels
ax_xlim = ax1.get_xlim()
ax_ylim = ax1.get_ylim()
mid_x = results_df["sigma_annual_pct"].mean()
mid_y = results_df["expected_return_5yr_pct"].mean()
ax1.text(mid_x*0.5, mid_y*1.2, "Low Risk\nHigh Return",
         fontsize=8, color="lime", alpha=0.7)
ax1.text(mid_x*1.3, mid_y*1.2, "High Risk\nHigh Return",
         fontsize=8, color="#FF9800", alpha=0.7)
ax1.text(mid_x*0.5, mid_y*0.5, "Low Risk\nLow Return",
         fontsize=8, color="#4FC3F7", alpha=0.7)
ax1.text(mid_x*1.3, mid_y*0.5, "High Risk\nLow Return",
         fontsize=8, color="tomato", alpha=0.7)

legend_patches = [mpatches.Patch(color=cat_color[c], label=c)
                  for c in sub_cats]
ax1.legend(handles=legend_patches, fontsize=7,
           loc="lower right", framealpha=0.3,
           labelcolor="white")
ax1.set_title("Expected 5yr Return vs Annualised Risk\n(All 40 Funds)",
              fontsize=12, color="white", fontweight="bold")
ax1.set_xlabel("Annualised Sigma — Risk (%)", color="#B0C4DE")
ax1.set_ylabel("Expected 5yr Return (%)", color="#B0C4DE")
ax1.tick_params(colors="#B0C4DE")
for sp in ax1.spines.values():
    sp.set_edgecolor("#1565C0")

# Bar: P5 / P50 / P95 for top 10
ax2 = axes[1]
ax2.set_facecolor("#0D2137")

top10 = results_df.head(10)
names = [n[:22] for n in top10["scheme_name"]]
x = np.arange(len(top10))
w = 0.25

bars1 = ax2.bar(x - w, top10["p5_nav_5yr"],  w, label="P5 (Worst)",
                color="#E63946", alpha=0.85, edgecolor="white")
bars2 = ax2.bar(x,     top10["p50_nav_5yr"], w, label="P50 (Median)",
                color="#2196F3", alpha=0.85, edgecolor="white")
bars3 = ax2.bar(x + w, top10["p95_nav_5yr"], w, label="P95 (Best)",
                color="#4CAF50", alpha=0.85, edgecolor="white")

ax2.set_xticks(x)
ax2.set_xticklabels(names, rotation=35, ha="right",
                    fontsize=7.5, color="#B0C4DE")
ax2.tick_params(axis="y", colors="#B0C4DE")
ax2.set_title("5-Year NAV Projections — Top 10 Funds\n"
              "(P5 = Worst | P50 = Median | P95 = Best)",
              fontsize=12, color="white", fontweight="bold")
ax2.set_ylabel("Projected NAV (₹)", color="#B0C4DE")
ax2.legend(fontsize=9, framealpha=0.3, labelcolor="white")
for sp in ax2.spines.values():
    sp.set_edgecolor("#1565C0")

fig.suptitle(
    "Monte Carlo Simulation — 5-Year NAV Outlook | "
    f"{SIMULATIONS:,} Simulations | GBM Model",
    fontsize=14, fontweight="bold", color="white"
)
plt.tight_layout()
out2 = f"{REP}/chart_monte_carlo_all_funds.png"
plt.savefig(out2, dpi=150, bbox_inches="tight",
            facecolor="#0D1B2A")
plt.close()
print(f"  Saved -> {out2}")


# ─────────────────────────────────────────────────────────────
# STEP 6 — Print Summary Table
# ─────────────────────────────────────────────────────────────
print()
print("="*65)
print("  MONTE CARLO RESULTS — TOP 10 FUNDS")
print("="*65)
print(f"\n  {'Rank':<5} {'Scheme':<35} {'Exp 5yr%':>9} "
      f"{'P5 NAV':>9} {'P50 NAV':>9} {'P95 NAV':>9} "
      f"{'P(profit)':>10}")
print("  " + "-"*93)
for _, row in results_df.head(10).iterrows():
    print(f"  {_:<5} {row['scheme_name'][:35]:<35} "
          f"{row['expected_return_5yr_pct']:>8.1f}%  "
          f"₹{row['p5_nav_5yr']:>8.0f}  "
          f"₹{row['p50_nav_5yr']:>8.0f}  "
          f"₹{row['p95_nav_5yr']:>8.0f}  "
          f"{row['prob_profit_pct']:>8.1f}%")

print()
print("="*65)
print("  B3 COMPLETE")
print("="*65)
print(f"  monte_carlo_results.csv         -> project root")
print(f"  chart_monte_carlo_top5.png      -> reports/")
print(f"  chart_monte_carlo_all_funds.png -> reports/")
print()
# print("  Git commit:")
# print('  git add monte_carlo.py monte_carlo_results.csv reports/')
# print('  git commit -m "B3: Monte Carlo NAV simulation complete"')
# print('  git push origin main')