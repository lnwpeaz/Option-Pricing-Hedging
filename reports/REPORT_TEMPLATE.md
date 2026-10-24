# Option Pricing and Delta Hedging: Research Report

Status: retained outline for future reports. The completed milestone-6 report is
in reports/final/research_report.md and output/pdf/option_pricing_hedging_research_report.pdf.
Pricing, Monte Carlo, paths, ledger and paired hedge experiments are implemented.
Fill new reports only with their corresponding validated implementation and observed results.

## Abstract
State the question, model assumptions, experiment design and observed conclusions.

## 1. Research question and economic motivation
Explain why discrete rebalancing, costs and volatility uncertainty matter to an option seller.

## 2. Financial model and conventions
Define payoff, no-arbitrage assumptions, physical versus risk-neutral measures and units.

## 3. Numerical pricing and verification
Present analytic/tree/MC methods, convergence and uncertainty against fixed benchmarks.

## 4. Self-financing hedge methodology
Explain opening premium, stock/cash trades, interest, all costs and terminal settlement.

## 5. Experimental design
List predeclared scenarios, shared path generation, seeds and reproducibility artifacts.

## 6. Results and uncertainty
Compare replication-error distributions, RMSE, costs, turnover and paired differences.
Include all scenarios and the unhedged baseline; avoid selecting favorable examples alone.

## 7. Limitations
Discuss GBM assumptions, volatility misspecification, absent market quotes and execution limits.

## 8. Conclusions and next questions
Connect findings to the research question and distinguish evidence from speculation.

## References and reproduction appendix
List sources actually read, mathematical derivations, exact versions and reproduction commands.
