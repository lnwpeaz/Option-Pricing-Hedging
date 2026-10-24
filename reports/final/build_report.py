"""Build the milestone-6 PDF and matching Markdown from verified local results.

Document production only. Uses the bundled ReportLab/Pillow runtime; never runs
pricing experiments or changes their numerical artifacts. Paths are repo-relative.
"""
import csv
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                               SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EX = ROOT / "reports/examples"
OUTPUT = ROOT / "output/pdf/option_pricing_hedging_research_report.pdf"
WIDTH = A4[0] - 112
NAVY = colors.HexColor("#142E45")
TEAL = colors.HexColor("#007E80")
PALE = colors.HexColor("#F0F5F8")


def load_json(path):
    return json.loads(path.read_text())


def load_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def f(value, digits=5):
    return f"{float(value):.{digits}f}"


def ci(row, name="rmse", digits=5):
    return f"[{f(row[name + '_ci_low'], digits)}, {f(row[name + '_ci_high'], digits)}]"


def main():
    evidence = load_json(ROOT / "reports/verification/final-report-evidence.json")
    assert evidence["contract_review_call_put_integrals_passed"]
    for name, expected in evidence["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    mc = load_json(EX / "milestone-2b/summary.json")
    stress = load_json(EX / "research-validation/summary.json")
    summary = load_json(EX / "milestone-5/summary.json")
    metrics = load_csv(EX / "milestone-5/metrics.csv")
    pairs = load_csv(EX / "milestone-5/paired_comparisons.csv")
    cases = load_csv(EX / "milestone-5/scenarios.csv")
    metric = {(int(r["scenario_id"]), r["premium_basis"]): r for r in metrics}
    example = load_csv(EX / "contract-review/pricing/baseline.csv")
    emc = load_json(EX / "contract-review/monte-carlo/summary.json")
    emetrics = load_csv(EX / "contract-review/hedging/metrics.csv")
    emetric = {(int(r["scenario_id"]), r["premium_basis"]): r for r in emetrics}
    manifest = load_json(EX / "milestone-5/manifest.json")

    for name, filename in (("Report", "Arial.ttf"), ("Report-Bold", "Arial Bold.ttf"),
                           ("Mono", "Courier New.ttf")):
        pdfmetrics.registerFont(TTFont(name, "/System/Library/Fonts/Supplemental/" + filename))
    pdfmetrics.registerFontFamily("Report", normal="Report", bold="Report-Bold",
                                  italic="Report", boldItalic="Report-Bold")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("ReportBody", fontName="Report", fontSize=9.8, leading=13.5,
                              textColor=NAVY, spaceAfter=8, alignment=TA_LEFT))
    styles.add(ParagraphStyle("ReportTitle", fontName="Report-Bold", fontSize=25, leading=29,
                              textColor=NAVY, spaceAfter=13))
    styles.add(ParagraphStyle("ReportSection", fontName="Report-Bold", fontSize=16, leading=20,
                              textColor=NAVY, spaceAfter=13))
    styles.add(ParagraphStyle("ReportSub", fontName="Report-Bold", fontSize=11, leading=14,
                              textColor=TEAL, spaceBefore=7, spaceAfter=6))
    styles.add(ParagraphStyle("ReportSmall", parent=styles["ReportBody"], fontSize=8.1,
                              leading=11, spaceAfter=7))
    styles.add(ParagraphStyle("ReportCode", fontName="Mono", fontSize=8.1, leading=11,
                              textColor=NAVY, spaceAfter=8, backColor=PALE,
                              borderPadding=7))
    styles.add(ParagraphStyle("ReportCell", fontName="Report", fontSize=8, leading=10,
                              textColor=NAVY))
    styles.add(ParagraphStyle("ReportHead", parent=styles["ReportCell"],
                              fontName="Report-Bold", textColor=colors.white))
    story, markdown, used_inputs = [], [], set()

    def p(text, style="ReportBody"):
        story.append(Paragraph(escape(text), styles[style]))
        markdown.append(text + "\n")

    def sub(text):
        p(text, "ReportSub")
        markdown[-1] = "### " + text + "\n"

    def page(number, title):
        if number > 1:
            story.append(PageBreak())
        p(f"{number:02d} / RESEARCH REPORT", "ReportSmall")
        p(title, "ReportTitle" if number == 1 else "ReportSection")
        markdown[-1] = ("# " if number == 1 else "## ") + title + "\n"

    def code(text):
        story.append(Paragraph(escape(text).replace("\n", "<br/>"), styles["ReportCode"]))
        markdown.append("```text\n" + text + "\n```\n")

    def table(headers, rows, widths=None, tiny=False):
        font = 7.3 if tiny else 8
        cell = ParagraphStyle("temp", parent=styles["ReportCell"], fontSize=font,
                              leading=font + 2)
        head = ParagraphStyle("temph", parent=styles["ReportHead"], fontSize=font,
                              leading=font + 2)
        data = [[Paragraph(escape(str(x)), head) for x in headers]]
        data += [[Paragraph(escape(str(x)), cell) for x in row] for row in rows]
        if widths is None:
            widths = [WIDTH / len(headers)] * len(headers)
        else:
            widths = [WIDTH * w / sum(widths) for w in widths]
        t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4 if tiny else 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4 if tiny else 5),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, TEAL),
        ]))
        story.extend([t, Spacer(1, 9)])
        markdown.append("| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |")
        markdown.extend("| " + " | ".join(str(x) for x in row) + " |" for row in rows)
        markdown.append("")

    def figure(rel, caption, max_height=255):
        path = ROOT / rel
        used_inputs.add(rel)
        with PILImage.open(path) as im:
            w, h = im.size
        scale = min(WIDTH / w, max_height / h)
        story.append(KeepTogether([Image(str(path), width=w * scale, height=h * scale),
                                    Paragraph(escape(caption), styles["ReportSmall"])]))
        relative = "../examples/" + rel.split("reports/examples/", 1)[1]
        markdown.append(f"![{caption}]({relative})\n")

    def link(title, url):
        story.append(Paragraph(f'<link href="{escape(url)}" color="#007E80">{escape(title)}</link>', styles["ReportSmall"]))
        markdown.append(f"[{title}]({url})\n")

    page(1, "Option Pricing & Delta Hedging")
    p("Monte Carlo accuracy, computational efficiency and auditable hedge risk", "ReportSection")
    p("Completed research version | 23 October 2026 | Financial Engineering + Computer Engineering", "ReportSmall")
    sub("Abstract")
    p("This project builds and verifies a European option-pricing and short-call replication engine. Its main computational study compares plain Monte Carlo, antithetic pairs and an independent-pilot stock control variate. A paired simulation then measures how hedge frequency, transaction costs and volatility assumptions affect terminal cash P&L. All results are conditional experiments under a declared model; no market return or executable trading edge is inferred.")
    sub("Observed findings")
    p(f"At 262,144 production evaluations, baseline call RMSE falls from {f(next(r for r in mc['baseline_results'] if r['kind']=='call' and r['method']=='plain')['rmse'], 5)} for plain MC to {f(next(r for r in mc['baseline_results'] if r['kind']=='call' and r['method']=='control')['rmse'], 5)} for the control estimator. Independent pilot work is counted. Empirical RMSE slopes across sample sizes are close to the expected -0.5 rate, while rare-payoff stress tests expose misleading zero sample errors.")
    p("At reference volatility 20% and 5 bps trading cost, hedging every grid step has RMSE 0.54279, versus 0.97187 every five steps. It also incurs more financed costs: 0.31736 versus 0.18155. A model-sigma change can alter the premium received; fixing that premium removes an apparent profit in the high-sigma example.")
    table(["Evidence", "Retained scope"], [
        ["Pricing research", "5,760 repeated MC estimates; 144 independent-reference scenarios"],
        ["Hedge research", "10,000 common paths; 21 cases; 210,000 path outcomes"],
        ["Verification", "390 tests passed; scalar/vector checks and source replay evidence"],
        ["Practical demonstration", "Second six-month contract; prices, Greeks and 63,000 hedge outcomes"],
    ], [1, 2.9])
    p("Research question: how do discrete trading, costs and volatility misspecification change short-call replication error, and how much computation is needed to estimate those effects reliably?")

    page(2, "Model, units and self-financing accounting")
    p("One non-dividend-paying underlying follows geometric Brownian motion (GBM). The primary study fixes S0=K=100, T=1 year, continuously compounded r=5%, assumed physical drift mu=8% and true scenario volatility sigma=20%. None is estimated from market data. A European call is sold with unit multiplier; fractional shares and unlimited borrowing/lending at r are allowed.")
    sub("Pricing measure versus scenario measure")
    code("S(t+dt) = S(t) exp((drift - sigma^2/2)dt + sigma sqrt(dt) Z)\nZ ~ N(0,1) independently across paths/increments\nPricing: drift = r;  call value = E_Q[exp(-rT) max(S_T-K,0)]\nHedge scenarios: drift = mu; mu is not a forecast from this project")
    p("Exact GBM transitions remove Euler time-discretization error in this model. They do not remove the error from trading only at discrete dates. European pricing needs only terminal samples; hedge accounting requires prices throughout the path.")
    sub("Analytic and tree pricing references")
    code("d1 = (log(S/K) + (r + sigma^2/2)*T) / (sigma*sqrt(T))\nd2 = d1 - sigma*sqrt(T); Phi = standard-normal CDF\nCall = S*Phi(d1) - K*exp(-r*T)*Phi(d2)\nPut = K*exp(-r*T)*Phi(-d2) - S*Phi(-d1)\nCRR: u=exp(sigma*sqrt(dt)); d=1/u\np=(exp(r*dt)-d)/(u-d); discount one-step expected payoffs")
    p("CRR rejects invalid transition probabilities rather than clipping them. Expiry and zero-volatility cases are handled separately; analytic Greeks at derivative kinks are explicitly undefined. The formulas here apply to positive maturity/volatility.", "ReportSmall")
    sub("Cash ledger and event order")
    code("Opening: receive C0; buy delta0 shares\nB0 = C0 - delta0*S0 - opening_cost\nEach date: B_pre = B_previous * exp(r*dt)\nRebalance before expiry:\nB_new = B_pre - (delta_new-delta_old)*S - trade_cost\nExpiry: P&L = B_pre + delta_old*S_T - close_cost - call_payoff")
    p("Delta uses only the current spot and time remaining. At expiry the held shares are liquidated and the payoff is paid; there is no new delta trade. One-way cost equals bps/10,000 times absolute traded shares times spot. Opening, rebalancing and liquidation costs all enter cash; financed costs must not be deducted a second time.")
    table(["Output", "Interpretation"], [
        ["Price / terminal P&L", "Currency units per one option unit, not portfolio return percentages"],
        ["Delta / gamma", "First / second local sensitivity to spot"],
        ["Vega", "Per 1.0 absolute volatility; divide by 100 for one percentage point"],
        ["RMSE", "sqrt(mean(P&L^2)); measures error around zero, including bias"],
        ["Cash borrowing", "Simulated cash deficit; not broker margin or investable capital"],
    ], [1, 3])

    page(3, "Monte Carlo: estimator and uncertainty design")
    p("The estimator never calls the analytic option price. Black-Scholes supplies the experiment's numerical reference. Independent streams are derived with SeedSequence identifiers and PCG64; raw run keys and estimates are saved. The lab spans five production sample sizes (1,024 to 262,144), three strikes (80, 100, 120), both payoff types, three methods and 64 independent repeats per cell.")
    table(["Method", "Estimator", "Independent observations / extra work"], [
        ["Plain", "Mean of discounted payoffs Y", "N independent terminal evaluations"],
        ["Antithetic", "Mean of (Y(Z)+Y(-Z))/2", "N/2 independent pairs; N payoff evaluations"],
        ["Control", "Mean of Y-beta*(X-S0), X=exp(-rT)*S_T", "N production observations + 2,048 independent pilot observations"],
    ], [1, 2.2, 2.6])
    p("The control expectation E_Q[X]=S0 is known under the model. Beta is fitted on the pilot and frozen before production sampling. The estimator does not use the true option premium to tune its answer. Pilot draws are disjoint from production draws and their cost is included in work and timing comparisons.")
    code("SE = sample_std(independent observations, ddof=1) / sqrt(n_independent)\nApproximate 95% interval = estimate +/- 1.95996398454 * SE\nEmpirical RMSE = sqrt(mean((estimate - reference)^2))")
    sub("What the repeated experiment measures")
    p("Across independent repeats, the lab records signed bias, empirical standard deviation, RMSE and approximate-CI coverage. RMSE intervals use 2,000 bootstrap resamples of repeats; coverage proportions have Wilson intervals. These distinguish uncertainty in an individual price estimate from uncertainty in the measured performance of an estimator.")
    p("The asymptotic sampling reference is RMSE proportional to N^(-1/2): roughly four times the work is needed to halve sampling error without a better estimator. A better algorithm can improve accuracy per evaluation, but the benefit depends on payoff shape. Every strike/payoff result is retained, rather than selecting the best case.")
    sub("Numerical decisions")
    p("Batch-centered moments avoid subtracting nearly equal raw second moments. Sample values are normalized to spot units; underflow/overflow and unrepresentable moments produce explicit errors. Adjusted control prices and confidence intervals are not clipped to theoretical bounds. A zero observed variance is recorded, never treated as proof of an exact price.")

    page(4, "Monte Carlo: measured accuracy and calibration")
    p("Baseline S=K=100, T=1, r=5%, sigma=20%; N=262,144 production evaluations and 64 independent repeats per row. Analytic call/put references are 10.4505835722 and 5.5735260223. The intervals below describe finite-repeat uncertainty in measured RMSE.")
    table(["Payoff / method", "RMSE", "95% RMSE interval", "CI coverage", "Work gain"], [
        [r["kind"] + " / " + r["method"], f(r["rmse"]),
         f"[{f(r['rmse_ci_low'])}, {f(r['rmse_ci_high'])}]", f"{r['coverage']:.1%}",
         f(r["work_normalized_gain"], 2)]
        for r in sorted(mc["baseline_results"], key=lambda r: (r["kind"], {"plain":0,"antithetic":1,"control":2}[r["method"]]))
    ], [1.5, .85, 1.8, .9, .8])
    figure("reports/examples/milestone-2b/accuracy.png", "Figure 1. Repeated-seed RMSE and baseline estimator accuracy; full underlying records are retained.", 265)
    p("Work gain is plain MSE divided by adjusted-method MSE, multiplied by plain work / adjusted work. Control pilot evaluations are included. For the baseline call its measured work-normalized gain is 9.87, not a guaranteed future speedup or an equal-wall-clock result.")
    p("Call log-log RMSE slopes are -0.477 (plain), -0.489 (antithetic) and -0.507 (control); put slopes are -0.513, -0.502 and -0.510. Coverage of 100% in 64 control-call repeats has a Wilson interval of about [94.3%, 100%], so it does not establish perfect calibration.")

    page(5, "Computer Engineering: speed, memory and boundaries")
    p("The engineering question is accuracy per computational resource. Terminal sampling and bounded batches avoid storing unnecessary full paths for European pricing. The implementation uses O(N + pilot) work and O(batch size) numerical workspace, with reproducible streams and explicit input/numerical validation.")
    figure("reports/examples/milestone-2b/engineering.png", "Figure 2. Kernel timings and complete-estimator batching measurements on the recorded local machine.", 270)
    table(["Batch size", "Complete price median (ms)", "Peak traced MiB"], [
        [f"{r['batch_size']:,}", f(r["median_seconds"] * 1000, 3), f(r["traced_peak_bytes"] / 2**20, 3)]
        for r in mc["batch_benchmark"]
    ], [1, 2, 1.4])
    p(f"The identical-pre-generated-normal scalar/vector kernel benchmark has a median ratio of {mc['kernel_speedup']:.2f}x over nine timed repeats after warm-up. RNG and standard-error calculation are excluded from both kernels; array allocation and validation are included. The scalar baseline is educational Python, not an optimized compiled competitor. This ratio is not end-to-end MC speedup.")
    p("Complete-estimator batching includes RNG, payoff and uncertainty calculation, while Generator construction is excluded for every call. Allocation is measured separately with tracemalloc, not process RSS. Timing and allocation ratios are local observations; scheduling, cache behavior, threading and library builds can change them. No GPU, multicore or cross-platform performance claim is made.")
    p("Hedge accounting instead keeps O(N*M) input paths, loops over dates and vectorizes over paths. Its date-loop workspace is O(N), but current input validation also creates O(N*M) temporary booleans. The whole hedge pipeline therefore has no claimed O(N) peak-memory bound.")

    page(6, "Validation: accurate arithmetic is not market accuracy")
    p(f"An independent discounted-payoff integral checks 144 scenarios across strike, tenor, volatility and rate, including both payoff types and negative rates. It does not call project pricing or GBM routines. Maximum analytic/integral absolute difference is {stress['max_analytic_quadrature_difference']:.3e}, below the declared 1e-7 tolerance. Quadrature error is estimated, with a separate normal-tail bound; relative accuracy for arbitrarily tiny premiums is not established.")
    figure("reports/examples/research-validation/calibration.png", "Figure 3. Stress calibration exposes regimes where normal intervals or observed zero variance are misleading.", 250)
    table(["Method", "Zero-SE repeats", "Zero-SE with positive reference", "Misses above floor"], [
        [name, data["zero_se_repeats"], data["zero_se_nonzero_reference_repeats"],
         data["uncovered_above_precision_floor"]]
        for name, data in stress["methods"].items()
    ], [1, 1.2, 1.8, 1.3])
    p("The stress experiment retains 13,824 estimates (144 scenarios x 3 methods x 32 repeats, 8,192 production evaluations each). The display/interpretation floor is 1e-10; it does not repair or remove raw outcomes. A positive but rare payoff may never be sampled, giving price=0 and SE=0 even though the true premium is positive. These failures are part of the research finding.")
    p("Additional checks cover put-call parity, bounds, deterministic limits, finite-difference Greeks, invalid inputs and numerical range errors. CRR has absolute error 0.00175112 at 1,001 steps in the baseline; odd/even errors can oscillate. Physical/risk-neutral path diagnostics test model moments across independent repeats. None validates GBM against actual asset returns.")

    page(7, "Paired hedge study: design and reference results")
    p("The predeclared grid uses 10,000 independent physical GBM paths, 252 intervals, hedge frequencies of every 1/5 steps, costs of 0/5/10 bps, and model volatilities of 15/20/25%. There are 18 hedge cases plus three same-model-premium unhedged baselines. The same path IDs are used throughout; 1,000 shared whole-path bootstrap resamples preserve covariance in comparisons.")
    table(["Reference sigma=20%", "Mean P&L", "RMSE", "95% RMSE interval", "Financed cost"], [
        [label, f(metric[i, "model"]["mean_pnl"]), f(metric[i, "model"]["rmse"]),
         ci(metric[i, "model"]), f(metric[i, "model"]["mean_financed_costs"])]
        for i, label in ((19,"Unhedged"),(6,"Every 1 / 0 bps"),(9,"Every 5 / 0 bps"),
                         (7,"Every 1 / 5 bps"),(10,"Every 5 / 5 bps"),
                         (8,"Every 1 / 10 bps"),(11,"Every 5 / 10 bps"))
    ], [1.5, .85, .85, 1.9, 1])
    figure("reports/examples/milestone-5/risk_and_cost.png", "Figure 4. Replication-error and cost trade-offs; amounts are per short-option unit, not portfolio percentages.", 245)
    p("At 5 bps, every-one minus every-five RMSE is -0.42908, with paired 95% interval [-0.44634, -0.41135]. This is evidence of lower replication RMSE under this model, alongside higher trading cost and a more negative mean. The finer policy also remains lower-RMSE at 10 bps for reference sigma; the grid does not establish the break-even cost.")
    p("Intervals are approximate, pointwise bootstrap intervals, not simultaneous superiority claims or uncertainty about the model parameters. Daily/weekly are shorthand for the default every-1/5 grid policies, not holiday-aware exchange schedules.")

    page(8, "Volatility misspecification: separate premium from policy")
    p("Model volatility sets both the initial premium and the delta policy. A larger premium can make a strategy look profitable without improving the hedge. To isolate this effect, each path also has a common-premium P&L based on the 20% reference premium. The deterministic funded premium shift changes terminal P&L, not the delta policy.")
    code("P&L_common = P&L_model + (C_reference - C_model) * exp(r*T)")
    table(["Model sigma / steps", "Initial premium", "Own mean", "Common mean", "Common RMSE"], [
        [f"{float(metric[i,'model']['hedge_volatility']):.0%} / {metric[i,'model']['rebalance_every_steps']}",
         f(metric[i,"model"]["initial_premium"],4), f(metric[i,"model"]["mean_pnl"],4),
         f(metric[i,"common_reference"]["mean_pnl"],4), f(metric[i,"common_reference"]["rmse"],4)]
        for i in (1,4,7,10,13,16)
    ], [1.6, 1.2, 1, 1.1, 1.2])
    p("All table rows have 5 bps cost. At 25% model volatility and every-one-step hedging, own-premium mean +1.68117 becomes -0.30092 on the common premium. The model supplied the higher receipt; there is no observed executable quote showing that a market participant would pay it.")
    figure("reports/examples/milestone-5/volatility_and_premium.png", "Figure 5. Volatility-policy comparisons with original and fixed-premium interpretations.", 255)
    p("A lower loss probability alone is also insufficient: it omits loss magnitude and capital needs. For reference sigma, every-one-step hedging at 10 bps has about 93.8% negative outcomes despite much smaller error magnitude than the unhedged short call. Mean simulated peak borrowing at 5 bps is 88.38674; this is not margin, collateral or an adequate capital requirement.")

    page(9, "Complete primary grid and paired frequency effects")
    p("All 21 cases are shown on the model-premium basis. Sigma sets both premium and hedge delta. U means an unhedged short call; costs are bps and all cash amounts are per one option unit. The complete common-premium grid, quantiles, funding diagnostics and intervals remain in the CSV artifacts.", "ReportSmall")
    table(["ID", "Sigma", "Steps", "bps", "Mean P&L", "SD", "RMSE", "Fin. cost"], [
        [i, f"{float(r['hedge_volatility']):.0%}", "U" if r["strategy"]=="unhedged" else r["rebalance_every_steps"],
         f(r["one_way_cost_bps"],0), f(r["mean_pnl"],4), f(r["standard_deviation"],4),
         f(r["rmse"],4), f(r["mean_financed_costs"],4)]
        for i in range(21) for r in [metric[i,"model"]]
    ], [.4,.7,.6,.5,1.2,1,1,1], tiny=True)
    sub("Every-one minus every-five RMSE: paired 95% intervals")
    table(["Sigma", "Cost bps", "RMSE difference", "Paired 95% interval"], [
        [f"{float(metric[int(r['left_scenario_id']), 'model']['hedge_volatility']):.0%}",
         f(metric[int(r["left_scenario_id"]),"model"]["one_way_cost_bps"],0),
         f(r["rmse_difference"],5), ci(r,"rmse_difference",5)]
        for r in pairs if r["comparison_kind"]=="frequency" and r["premium_basis"]=="model"
    ], [1,1,1.8,2.6], tiny=True)
    p("At sigma=15%, 5 bps the interval crosses zero; at 10 bps the finer policy has higher RMSE. Frequency preference is conditional on costs, model sigma and the selected error objective. The report does not declare a universal optimal policy.", "ReportSmall")

    page(10, "A usable contract-review workflow")
    p("A second predeclared hypothetical contract demonstrates that the interfaces accept inputs beyond the original benchmark: S0=120, K=125, T=0.5 years, r=4%, pricing sigma=25%, no dividends. These are chosen test inputs, not a live ticker, a market quote or the user's actual position. Existing APIs produce the following analytic outputs.")
    table(["Payoff", "Price", "Delta", "Gamma", "Vega / 1 pp"], [
        [r["kind"], f(r["price"],6), f(r["delta"],6), f(r["gamma"],6),
         f(r["vega_per_percentage_point"],6)] for r in example
    ])
    p("Delta 0.48827 means a local call-value sensitivity of about 0.48827 currency units for a one-unit spot increase; gamma means this linear approximation changes with spot. Vega 0.33837 per volatility percentage point is a local model sensitivity, not a guarantee for a large joint move or a market price.")
    p("The same contract is also priced in a new 1,728-estimate MC experiment. For calls at N=65,536 and 32 independent repeats, RMSE is 0.05977 (plain), 0.03726 (antithetic) and 0.02725 (control). Control's measured work-normalized gain is 4.74 including 1,024 pilot evaluations; its benefit differs from the original case.", "ReportSmall")
    sub("Stress the hedge while keeping the opening receipt fixed")
    p("The scenario assumes true sigma=30% and mu=6%, with 3,000 common paths over 126 intervals, 21 cases and 500 joint bootstrap resamples. All rows below receive the same 25%-sigma reference premium; trading cost is 2 bps. Correct scenario sigma is known only because the scenario was constructed.")
    table(["Hedge sigma / steps", "Mean P&L", "RMSE", "95% RMSE interval", "Fin. cost"], [
        [f"{float(emetric[i,'common_reference']['hedge_volatility']):.0%} / {emetric[i,'common_reference']['rebalance_every_steps']}",
         f(emetric[i,"common_reference"]["mean_pnl"],4), f(emetric[i,"common_reference"]["rmse"],4),
         ci(emetric[i,"common_reference"],digits=4), f(emetric[i,"common_reference"]["mean_financed_costs"],4)]
        for i in (1,4,7,10,13,16)
    ], [1.6,1,1,2,1])
    p("For every-one-step hedging, moving the hedge sigma from 25% to the scenario's 30% reduces observed RMSE from 2.21339 to 2.03738, but the common-premium mean remains -1.85348. A better delta policy cannot create an adequate initial premium. The matching unhedged baseline has RMSE 16.94108; these are short-call error comparisons, not returns on invested capital.")
    sub("What a user can do now")
    p("Enter supported contract/model assumptions; inspect prices and local sensitivities; vary volatility, costs and trading frequency; compare error magnitude and uncertainty; inspect every cash/trade event; retain and replay the outputs. The workflow supports numerical and scenario decisions. Market execution requires additional contract and data capabilities described on page 12.")

    page(11, "Verification and reproducibility contract")
    p("Fresh acceptance on 23 October 2026: 390 tests passed in 23.37 seconds with warnings treated as errors. For the primary paired study, 336 scalar/vector comparisons on the fixed first 16 paths per case have maximum money difference 7.95808e-13, below the declared 1e-8 tolerance. The new use case adds 252 such comparisons, maximum money difference 6.82121e-13. These checks validate implementations and accounting within the model.")
    p("Read-only report QA independently recomputes point statistics from every retained path, all saved metric CI endpoints, every paired point estimate/CI, premium shifts and financed-cost identities for both hedge studies. Initial premiums and the new call/put prices are checked against the independent payoff integral. This checks report evidence; it does not independently regenerate every bootstrap draw.")
    p("The earlier primary-study source replay actually imported recovered archived code and reproduced 11 numerical artifacts byte-for-byte in the recorded environment. Its proof is reports/verification/milestone-5-replay.json. Report QA does not repeat that replay. The original milestone-2B record is hash-only: its exact historical source cannot be recovered from that record alone.")
    p("The new contract's pricing and hedge source archives were separately recovered and executed through their CLIs; all 14 selected numerical artifacts matched bytes. Proof: reports/verification/contract-review-replay.json. This replay covers pricing and hedging, not the new MC timing experiment, and is limited to the current recorded environment.", "ReportSmall")
    table(["Record", "Meaning and limit"], [
        ["Input + artifact hashes", "Consistency against the supplied manifest; not authenticity or correctness"],
        ["Source snapshot", "Source/config bytes can be recovered for later runs; code execution is separate"],
        ["RNG + environment", "PCG64, call shape, seeds, versions and platform matter; no universal stream identity"],
        ["Recorded versions", "; ".join(f"{k}={v}" for k,v in manifest["versions"].items())],
    ], [1,3])
    sub("Reproduce with a new output folder")
    code("PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.runner \\\n  --config configs/hedge_study.toml \\\n  --output-dir reports/runs/my-study\nPYTHONPATH=src .venv/bin/python -m option_hedging.experiments.verify_run \\\n  reports/runs/my-study")
    p("Existing destinations are refused. For contract review, use configs/contract_review_pricing.toml with pricing_demo, and configs/contract_review_hedging.toml with runner. Saved inputs remain the authority for exact cases. Timing, figure, timestamp and archive bytes are not cross-environment replay targets.", "ReportSmall")
    p("Build this report with reports/final/build_report.py using a Python runtime containing ReportLab and Pillow. First run reports/final/verify_evidence.py with the project environment. The Markdown and PDF share the same source; report inputs and output digests are recorded separately from experiment manifests.", "ReportSmall")

    page(12, "Practical limits, next scope and references")
    p("The completed result is a reusable numerical pricing and hedge-scenario research engine, with an executed report and demonstration. It can support research prototyping, model implementation checks and engineering experiments. It has not been certified for corporate production or validated as a live trading strategy. Completing this version does not make a market risk model correct.")
    table(["Current model boundary", "Needed before the corresponding market use"], [
        ["European, q=0, unit cash payoff", "Verified exercise, dividends, multiplier and settlement conventions"],
        ["Assumed constant volatility / smooth GBM", "Observed quotes and calibration; volatility/jump stress and empirical validation"],
        ["Fixed proportional costs / same-rate funding", "Executable spread, liquidity, funding, margin and position constraints"],
        ["No quote feed or order lifecycle", "Timestamped input checks, monitoring and forward paper evaluation"],
    ], [1.2,2.7])
    p("OCC describes standard US equity options as American exercise with stock delivery and usually 100 shares, subject to adjustments [3]. Those contracts are not fully represented by multiplying this European cash model by 100. The user's ETF/stock allocation problem remains a separate Portfolio Quantitative Research project.")
    sub("Next useful extension, without duplicating portfolio research")
    p("Prioritize a narrowly specified option-quote audit and implied-volatility layer: accept timestamped quotes for explicitly supported contracts, check price bounds and bid/ask consistency, solve implied volatility with a verified bracket, and show Greeks and model sensitivity with quality flags. Reject unsupported contract styles rather than silently treating them as European. This is a proposed next scope, not implemented capability; real American/dividend support is a separate extension.")
    p("The distinct profile contribution is the connection between financial mathematics, variance reduction, correct uncertainty units, bounded computation, accountable cash flows and reproducible experiments. The evidence supports model-based comparison and extension; it does not support claims of profitable option selection or reduced drawdown in a real long-only portfolio.")
    sub("References and primary evidence")
    p("Derivations and conventions: docs/RESEARCH_SPEC.md. Numerical evidence: reports/examples/milestone-2b/, research-validation/, milestone-5/ and contract-review/. Independent report checks: reports/verification/final-report-evidence.json. Full results, manifests, configs and source recovery limits are retained in the project.", "ReportSmall")
    link("[1] NumPy: random-stream compatibility policy (accessed 23 Oct 2026)", "https://numpy.org/doc/stable/reference/random/compatibility.html")
    link("[2] SciPy: quad / QUADPACK integration and error estimates (accessed 23 Oct 2026)", "https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad.html")
    link("[3] OCC: Equity Options product specifications (accessed 23 Oct 2026)", "https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications")

    def decorate(canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(TEAL)
        canvas.rect(0, h-9, w, 9, stroke=0, fill=1)
        canvas.setFont("Report-Bold", 7.3)
        canvas.setFillColor(NAVY)
        canvas.drawString(56, h-35, "OPTION PRICING & DELTA HEDGING LAB")
        canvas.setStrokeColor(colors.HexColor("#D8E3E8"))
        canvas.line(56, 42, w-56, 42)
        canvas.setFont("Report", 7)
        canvas.drawString(56, 28, "Conditional model research | 23 October 2026")
        canvas.drawRightString(w-56, 28, f"{doc.page} / 12")
        canvas.restoreState()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=56, leftMargin=56,
                            topMargin=53, bottomMargin=54, title="Option Pricing and Delta Hedging: Research Report",
                            author="Option Pricing & Delta Hedging Lab", pageCompression=1)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    (HERE / "research_report.md").write_text("\n".join(markdown), encoding="utf-8")
    used_inputs.update(evidence["input_sha256"])
    used_inputs.update(["reports/examples/milestone-5/scenarios.csv", "reports/examples/milestone-5/summary.json",
                       "reports/examples/milestone-5/manifest.json", "reports/examples/contract-review/hedging/summary.json",
                       "reports/examples/milestone-5/paired_comparisons.csv", "reports/examples/contract-review/hedging/metrics.csv",
                       "reports/verification/final-report-evidence.json", "reports/verification/milestone-5-replay.json",
                       "reports/verification/contract-review-replay.json"])
    provenance = {"kind":"report_build", "scope":"Document provenance; experiment manifests remain authoritative",
                  "inputs":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(used_inputs)},
                  "generator_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "outputs":{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in (OUTPUT, HERE/"research_report.md")}}
    (HERE / "report_manifest.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
