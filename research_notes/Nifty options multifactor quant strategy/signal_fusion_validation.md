# Signal fusion, calibration and small-sample validation for a Nifty/Sensex intraday options alert system

Scope: how to combine technical, options-implied, macro and sentiment signals into one calibrated trade decision, and how to validate it honestly when you have at most ~2,000 historical setups and 10–20 live trades a month. Project assumptions (from `reports/RESEARCH_REPORT.md` and the brief): personal alert-only system, ₹5,000 capital, 1 lot, buy Nifty (Tuesday weekly) and Sensex (Thursday weekly) options intraday, risk ₹200–500 and target ₹800–1,000 per trade, rule-based setups give the side, a meta-label model gives P(target before stop within the time limit), and an alert fires only if expected value after costs is positive.

Evidence grades: **A** = peer-reviewed with strong empirical support; **B** = peer-reviewed or theoretical, limited empirical support (incl. simulation-only or non-finance-domain transfer); **C** = practitioner, book, software docs or preprint; **D** = opinion. "[calc]" marks my own arithmetic or simulation (scratch scripts `calc.py` and `calc2.py`, seeds fixed). Every [calc] uses formulas from the cited sources. Where a source is clinical or another non-finance domain, the finding itself gets its own grade, and applying it to trading is listed under Inferences.

---

## 1. Meta-labeling: documented gains, failure modes, sample needs

### Takeaway
Meta-labeling is a sound *design pattern*: a rule sets the side and a secondary classifier decides take/skip (and size). The published evidence for *how much* it helps is thin. It comes mostly from controlled or synthetic experiments by one vendor-affiliated group, plus one real-data case study where out-of-sample precision rose only from 0.17 to 0.20. No paper gives a minimum sample size. Small-sample prediction theory implies that with ≤2,000 setups the meta-model must have only a handful of parameters.

### Cited Findings
- **[C]** López de Prado (2018, *Advances in Financial Machine Learning*, Wiley) introduced meta-labeling and the triple-barrier labels it uses. The primary model decides the side, and a secondary ML model learns whether to act on it. The secondary model's probability can then size the bet, so the primary can be tuned for recall and the secondary for precision. Graded C because the book gives no peer-reviewed out-of-sample test. — [Wiley book page](https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086)
- **[B]** Joubert (2022), "Meta-Labeling: Theory and Framework", *J. Financial Data Science* 4(3):31–44, DOI 10.3905/jfds.2022.1.098. Meta-labeling is "a machine learning layer that sits on top of a base primary strategy to help size positions, filter out false-positive signals", improving Sharpe ratio and maximum drawdown. The paper splits it into three components, uses a *controlled experiment* to show how each helps, and discusses which features to use. The author is CEO of Hudson & Thames, which sells the mlfinlab library, so there is a conflict of interest. — [pm-research](https://www.pm-research.com/content/iijjfds/4/3/31); [SSRN 4032018](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4032018)
- **[B]** Meyer, Joubert & Alfeus (2022), "Meta-Labeling Architecture", *JFDS* 4(4). The paper describes "several heterogeneous architectures", built either from the features ("feature-driven") or from the strategy's own characteristics ("strategy-driven"). It also introduces *inverse meta-labeling* to improve the quantity and quality of side forecasts. A secondary search summary says it also covers *conditional* meta-labeling, which partitions data by regime and fits a specialised secondary model per regime. I could not verify that against the full text. — [JFDS](https://jfds.pm-research.com/content/4/4/10); [code repo](https://github.com/hudson-and-thames/meta-labeling)
- **[B]** Meyer, Barziy & Joubert (2023), "Meta-Labeling: Calibration and Position Sizing", *JFDS*. Tested six position-sizing algorithms on calibrated and uncalibrated probabilities. Calibration "significantly improved" *fixed* sizing methods. Methods that estimate their sizing function from training data gained nothing significant from calibration. The paper also proposes "sigmoid optimal position sizing". — [pm-research](https://www.pm-research.com/content/iijjfds/early/2023/03/08/jfds20231119)
- **[B]** Thumm, Barucca & Joubert (2023), "Ensemble Meta-Labeling", *JFDS*. Ensembles are "especially beneficial when the underlying data consist of multiple regimes and are nonlinear in nature". This comes from a controlled setting. — [JFDS](https://jfds.pm-research.com/content/early/2022/12/14/jfds.2022.1.114); [UCL Discovery](https://discovery.ucl.ac.uk/id/eprint/10169066/)
- **[C]** Singh & Joubert, "Does Meta-Labeling Add to Signal Efficacy?" (capstone report, mlfinlab). S&P 500 e-mini futures, with a random-forest meta-model on Bollinger mean-reversion and SMA-crossover primaries.
  - Mean-reversion, **out-of-sample** (2018-01 to 2019-01): precision 0.17 → 0.20, "accuracy" 17% → 63%. Validation: precision 0.21 → 0.39, accuracy 20% → 77%.
  - Trend-following, validation: accuracy 37% → 56%, precision 0.37 → 0.42.
  - The authors hand-tuned the CUSUM event threshold "to get sufficiently large data set" and *up-sampled* the minority class before training. — [PDF](https://hudsonthames.org/wp-content/uploads/2022/04/Does-Meta-Labeling-Add-to-Signal-Efficacy.pdf)
- **[C]** Related evidence from this project's notes: Chen (2026, arXiv 2608.26106) found daily-direction accuracy of 58% overall but 73% when the predicted move was >1%, and only 154 of 799 days qualified. Confidence gating works, but the sample shrinks fast. — [alphaXiv](https://www.alphaxiv.org/abs/2608.26106) (via `research_notes/02_strategy_evidence_part1.md`)

### Inferences
- The big "accuracy" jumps in meta-labeling write-ups (17% → 63%) mostly count *correctly skipped* trades. For an EV-gated alert system the metrics that matter are **precision of taken trades, log-loss/Brier of p̂, and net expectancy per taken trade**. In the one real-data out-of-sample example, precision improved by about 3 percentage points. That is useful, but it is no transformation.
- **When meta-labeling fails** (inferred from the mechanics plus the sources above):
  1. The primary rule has no edge in any subset the features can identify. The meta-model then filters noise and overfits.
  2. The features carry no information beyond the trigger condition itself (e.g., re-using the breakout distance that defined the setup).
  3. There are too few positive labels per parameter (see §3).
  4. The classes are rebalanced or up-sampled, as Singh & Joubert did. Rebalancing shifts the base rate, so p̂ is no longer calibrated and EV gating breaks unless you recalibrate afterwards.
  5. Regime drift between training and deployment (see §8).
- **No published minimum sample size exists.** Treat the meta-model as a clinical-style binary risk model and apply Riley's criteria (§3). At a realistic AUC of about 0.58 and a positive rate of about 38%, keeping overfitting acceptable needs roughly 1,550 setups for 3 parameters and 2,600 for 5 [calc]. With ≤2,000 setups, the meta-model should be **one pooled model** across all four setups, with the setup as a categorical feature. Four separate models (about 500 samples each) would be badly overfit. Conditional or ensemble architectures (Meyer 2022; Thumm 2023) need more data than this project has.
- Meta-labeling also gives a hidden data bonus. The label (did the underlying hit target or stop first?) can be computed from market data for **every setup, taken or not**. Labelled data therefore accrues at the setup rate (about 1.1 per day, ~23 a month on ~2,000 setups over ~1,800 days), not at the trade rate.

### Gaps
- I could not access full texts of the four JFDS papers. The size of the gains in their controlled experiments (Sharpe or drawdown deltas, synthetic sample sizes) is not in these notes.
- I found no independent, non-vendor replication of meta-labeling gains on real futures or options data, and no live-trading evidence.
- I found no study of meta-labeling on Indian index options.

---

## 2. Forecast combination: equal weights, optimized weights, stacking, regime weights

### Takeaway
With few, noisy signals and small samples, **equal-weight or heavily shrunk combinations beat estimated "optimal" weights**. This is the forecast-combination puzzle, and the reason is estimation error in the weights. Regime-conditional or state-dependent weights sometimes rank higher, but their gains are usually statistically indistinguishable from equal weights. Mixture-of-experts has no small-sample finance evidence that I could find.

### Cited Findings
- **[A]** Timmermann (2006), "Forecast Combinations", *Handbook of Economic Forecasting* ch. 4, DOI 10.1016/S1574-0706(05)01004-9. Simple combinations often beat sophisticated weighting schemes. Shrinkage helps because it adds a little bias to the weights while "dramatically" reducing estimation error, and equal weights are the natural target to shrink towards (as summarised by Liu, Hao & Wang 2023). — [DOI](https://doi.org/10.1016/S1574-0706(05)01004-9); [Liu et al. 2023](https://doi.org/10.1111/obes.12590)
- **[A]** Smith & Wallis (2009), "A Simple Explanation of the Forecast Combination Puzzle", *Oxford Bull. Econ. Stat.* 71(3). The puzzle comes from estimation error in the weights. When forecast-error variances are similar, there is nothing to gain from estimating weights. — [DOI](https://doi.org/10.1111/j.1468-0084.2008.00541.x) (summarised in [Clements & Doolan 2020](https://doi.org/10.1002/for.2647))
- **[B]** Claeskens, Magnus, Vasnev & Wang (2016), "The forecast combination puzzle: A simple theoretical explanation", *Int. J. Forecasting* 32(3). This is the theoretical treatment of why estimated weights underperform. — [DOI](https://doi.org/10.1016/j.ijforecast.2015.12.005)
- **[A]** Rapach, Strauss & Zhou (2010), *Review of Financial Studies* 23(2):821–862.
  - Individual predictive regressions fail out of sample.
  - Combining the individual forecasts gives "statistically and economically significant out-of-sample gains" over the historical average, consistently over time.
  - Two reasons: combination substantially reduces forecast volatility, and combination forecasts are linked to the real economy. — [DOI](https://doi.org/10.1093/rfs/hhp063)
- **[A]** Neely, Rapach, Tu & Zhou (2014), *Management Science* 60(7). Technical indicators carry equity-premium information that complements macro variables, and combining both information sets improves forecasts. This is direct support for fusing technical and macro families. — [DOI](https://doi.org/10.1287/mnsc.2013.1838)
- **[A]** Zhang, He, Jacobsen & Jiang (2020), *J. Applied Econometrics* 35(5). "When estimated traditionally... the simple combination of individual predictors is superior". Sophisticated models only help once they are combined with the historical average and averaged across estimation windows. That version reached a monthly R²_OS of 1.10%. — [DOI](https://doi.org/10.1002/jae.2747)
- **[B]** Liu, Hao & Wang (2023), "Solving the Forecast Combination Puzzle Using Double Shrinkages", *Oxford Bull. Econ. Stat.* Shrinking weights both towards equal weights (WLS) and towards zero (LASSO, ridge or elastic net) gave R²_OS > 0.95% for S&P 500 excess returns from 1947 to 2017 with 12 predictors. — [DOI](https://doi.org/10.1111/obes.12590)
- **[B]** Costantini, Gunter & Kunst (2016), *J. Forecasting*. In DSGE-VAR simulations Bates–Granger weights beat uniform weights, but "in a corresponding application to real-world data, simple averaging performs best". They conclude uniform averages "may be the weighting scheme that is most robust to empirically observed irregularities". — [DOI](https://doi.org/10.1002/for.2427)
- **[B]** Clements & Doolan (2020), *J. Forecasting*. Time-dependent and *state-dependent* combinations (with more weight on past losses from similar states) "consistently rank higher" than equal weighting. Their performance is "statistically indistinguishable given the relatively low power of these loss functions". — [DOI](https://doi.org/10.1002/for.2647)
- **[A]** Aiolfi & Timmermann (2006), *J. Econometrics*. It is hard to pick the single best model, but clusters of good and bad models persist, so conditional combination can average the best cluster (as described by Meligkotsidou et al. 2014). — [DOI](https://doi.org/10.1016/j.jeconom.2005.07.015); [Meligkotsidou et al.](https://doi.org/10.1002/for.2312)
- **[B]** Elliott & Timmermann (2005), "Optimal forecast combination under regime switching", *Int. Economic Review* 46(4). Proposes combination weights that switch with a latent Markov regime. I did not verify the size of its empirical gains. — [DOI](https://doi.org/10.1111/j.1468-2354.2005.00361.x)
- **[B]** Stacking: Wolpert (1992), "Stacked generalization", *Neural Networks*, and Breiman (1996), "Stacked regressions", *Machine Learning*. Breiman found that constraining the stacking coefficients to be non-negative mattered. — [Wolpert DOI](https://doi.org/10.1016/S0893-6080(05)80023-1); [Breiman DOI](https://doi.org/10.1007/BF00117832)
- **[B]** Mixture of experts originates in Jacobs, Jordan, Nowlan & Hinton (1991), *Neural Computation*. — [DOI](https://doi.org/10.1162/neco.1991.3.1.79)
- **[C]** From this project's notes:
  - Mesfin (2026, arXiv 2605.04004): of 14 retail intraday signal families on MNQ, only regime-classifier signals with a 60–75 min hold survived walk-forward, with OOS t of 3.1–4.3.
  - Index news sentiment adds only marginal value (Dasgupta et al. 2024). — [Mesfin](https://www.alphaxiv.org/abs/2605.04004); [Dasgupta](https://www.alphaxiv.org/abs/2412.06794)

### Inferences
- **Practical fusion rule.** Turn each signal *family* into one sign-aligned, standardized score: positive means it agrees with the proposed side, winsorized at ±3, with z-scores computed from the training window only. Then:
  1. **Baseline:** the equal-weight average of the family scores (a "consensus score").
  2. **Learned:** a ridge-penalized logistic model that estimates *one* weight per family (≤4–5 weights), not one weight per raw indicator.
  
  This is the Rapach/Timmermann recipe: few weights, shrunk hard, with equal weights as the benchmark.
- **Stacking** with out-of-fold base predictions is acceptable only if the meta-learner is tiny: non-negative or ridge-penalized logistic regression on ≤5 inputs. With ~2,000 samples, a stacked GBM on top of GBMs has no evidential support.
- **Regime conditioning.** The evidence (Clements & Doolan; Elliott & Timmermann; Thumm et al.) says regime weights can help but are hard to verify with low power. Enter the regime as *one feature* (e.g., VIX − realized vol, or a trend/chop classifier output) plus at most one interaction (regime × breakout score). Do not fit separate models per regime: splitting 2,000 samples three ways leaves each regime model below Riley's minimum.
- **Pre-registered acceptance rule.** A learned or regime weighting replaces equal weights only if (a) it improves purged-CV log-loss by ≥1% relative, and (b) it improves in at least 4 of 6 calendar years (2019–2024). [D: default threshold, my opinion]
- Sentiment should enter as a *veto or shock flag*, not as a weighted score, given its grade-C evidence for index prediction.

### Gaps
- I found no peer-reviewed study of forecast combination for *intraday binary trade outcomes* specifically. All the evidence is from monthly or quarterly return forecasting and volatility.
- I found no small-sample finance evidence for mixture-of-experts gating.
- I could not obtain the exact R²_OS figures from Rapach et al. (2010); the PDF link was dead.

---

## 3. Model choice for small tabular financial datasets

### Takeaway
At ≤2,000 samples with a weak signal (AUC about 0.55–0.60), **penalized logistic regression with 3–6 effective parameters** is the evidence-based default. Gradient boosting and random forests need roughly 10× more data per variable to stabilize, and they do not beat logistic regression in unbiased comparisons on small data. The binding constraint is the Riley sample-size criterion, which for weak signals is far stricter than the old "10–20 events per variable" rule.

### Cited Findings
- **[A]** Christodoulou et al. (2019), *J. Clin. Epidemiol.* 110:12–22, systematic review.
  - In 145 comparisons at low risk of bias, the difference in logit(AUC) between ML and logistic regression was **0.00 (95% CI −0.18 to 0.18)**.
  - In 137 comparisons at *high* risk of bias, ML looked 0.34 better.
  - Calibration was rarely assessed. — [DOI](https://doi.org/10.1016/j.jclinepi.2019.02.004)
- **[A]** van der Ploeg, Austin & Steyerberg (2014), *BMC Med. Res. Methodol.* 14:137. Logistic regression reached stable AUC at about **20–50 events per variable (EPV)**. SVM, neural nets and random forests "may need over 10 times as many events per variable" to reach stable AUC and small optimism. — [article](https://bmcmedresmethodol.biomedcentral.com/articles/10.1186/1471-2288-14-137)
- **[A]** Riley et al. (2019), "Minimum sample size for developing a multivariable prediction model: Part II – binary and time-to-event outcomes", *Statistics in Medicine*. Sample size should target a global shrinkage factor S ≥ 0.9, i.e. ≤10% overfitting. Criterion (i): **n = p / [(S − 1)·ln(1 − R²_CS / S)]**, where p is the number of candidate parameters and R²_CS is the anticipated Cox-Snell R². — [DOI](https://doi.org/10.1002/sim.7992)
- **[A]** Gu, Kelly & Xiu (2020), "Empirical Asset Pricing via Machine Learning", *RFS* 33(5). Trees and neural nets beat linear models, but on a very large stock panel. That scale does not apply to 2,000 samples. — [DOI](https://doi.org/10.1093/rfs/hhaa009)
- **[B]** Grinsztajn, Oyallon & Varoquaux (2022), NeurIPS Datasets & Benchmarks. Tree-based models still beat deep learning on medium-sized tabular data, so neural nets are unjustified here. — [arXiv 2207.08815](https://arxiv.org/abs/2207.08815)
- **[A]** Niculescu-Mizil & Caruana (2005), ICML. Boosted trees and SVMs push probabilities away from 0 and 1, a sigmoid-shaped distortion. Logistic regression, bagged trees and neural nets give well-calibrated probabilities without correction. — [DOI](https://doi.org/10.1145/1102351.1102430); [PDF](https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf)
- **[C]** scikit-learn documentation: LogisticRegression "is more likely to return well calibrated predictions by itself" because its loss has a canonical (logit) link, provided the model is well specified and C is tuned. — [sklearn calibration guide](https://scikit-learn.org/stable/modules/calibration.html)
- **[C]** Monotonic constraints (forcing a feature's effect to be non-decreasing or non-increasing) are supported natively in XGBoost and LightGBM. — [XGBoost monotonic tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html)

### Inferences
- **[calc] Riley criterion (i) applied to this problem** (event rate 0.38, S = 0.9). R²_CS was obtained for each AUC by simulating a logistic model with a normal linear predictor.

| True out-of-sample AUC | Cox-Snell R² | n for 3 params | 5 params | 8 params | 12 params | 20 params |
|---|---|---|---|---|---|---|
| 0.55 | 0.0073 | 3,668 | 6,114 | 9,782 | 14,672 | 24,453 |
| 0.58 | 0.0173 | 1,546 | 2,576 | 4,122 | 6,182 | 10,304 |
| 0.60 | 0.0274 | 971 | 1,618 | 2,588 | 3,881 | 6,469 |
| 0.65 | 0.0619 | 422 | 702 | 1,124 | 1,685 | 2,808 |

  So with ≤2,000 setups and a realistic AUC of 0.56–0.60, an *unpenalized* model supports **about 3–6 parameters**. The old EPV ≥ 20 rule (760 events → 38 variables) would be badly misleading here, because it ignores how weak the signal is.
- Penalization (ridge or elastic net) lets you *screen* about 8–12 pre-specified candidates. The effective degrees of freedom should still end up at ≈4–6; check this via the size of the optimal C and coefficient stability across CV folds.
- Effective n is **smaller than 2,000**: setups on the same day share regime and news, and regimes are autocorrelated. Group CV by day and treat 2,000 as an upper bound.
- **Gradient boosting** belongs only as a *challenger*, constrained as follows:
  - max_depth 2, 100–300 trees, learning rate 0.03–0.05, min_child_samples ≥ 50
  - monotone constraints on features with a known sign (e.g., consensus score ↑ ⇒ P ↑)
  - followed by Platt or beta calibration
  
  Pre-register that it must beat penalized logistic regression by ≥1% relative log-loss in purged CV, *and* its calibration slope must be no worse. Random forests and neural nets: skip.
- Monotone constraints are a cheap way to inject prior knowledge into trees and should reduce variance. Evidence for their benefit in small finance datasets is practitioner-level (C/D).

### Gaps
- The Riley, Christodoulou and van der Ploeg results come from clinical prediction. Transferring them to finance is an inference, though the statistics (binary outcome, weak signal, small n) are the same.
- I found no head-to-head peer-reviewed comparison of logistic regression, GBM and random forest on ~2,000 intraday trade setups.

---

## 4. Probability calibration and why it matters for EV gating and sizing

### Takeaway
An EV gate is only as good as the calibration of p̂. At a 1:2 payoff, a 5-percentage-point overconfidence moves EV by 0.15R, which is about the entire expected edge of a 42%-win system. Use logistic regression (calibrated by construction). Recalibrate only with **Platt scaling (or beta calibration)** fitted on purged out-of-fold predictions. **Isotonic regression needs more than ~1,000 calibration points**, and live calibration cannot be checked bin-by-bin for years.

### Cited Findings
- **[A]** Niculescu-Mizil & Caruana (2005). Both Platt scaling and isotonic regression greatly improve squared error and log-loss of distorted models. **Platt scaling works better when calibration data are small, and isotonic regression better when there is enough data to avoid overfitting.** — [PDF](https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf)
- **[C]** scikit-learn guide:
  - "'isotonic' will perform as well as or better than 'sigmoid' when there is enough data (greater than ~ 1000 samples)". Isotonic "is more prone to overfitting, especially on small datasets".
  - The calibrator must be fitted on data independent of the classifier's training data. Otherwise the calibrated probabilities are pushed "closer to 0 and 1 than it should".
  - "A lower Brier loss... does not necessarily mean a better calibrated model". — [sklearn](https://scikit-learn.org/stable/modules/calibration.html)
- **[B]** Kull, Silva Filho & Flach (2017), AISTATS, "Beta calibration: a well-founded and easily implemented improvement on logistic calibration for binary classifiers". It is a 3-parameter calibration map (logistic regression on ln s and ln(1 − s)) that can represent the identity and non-sigmoid shapes that Platt scaling cannot. — [Bristol research page](https://research-information.bris.ac.uk/en/publications/beta-calibration-a-well-founded-and-easily-implemented-improvemen/)
- **[B]** Guo, Pleiss, Sun & Weinberger (2017), ICML, "On Calibration of Modern Neural Networks". Defines expected calibration error, ECE = Σ_b (n_b/N)·|acc_b − conf_b|, and reliability diagrams. — [arXiv 1706.04599](https://arxiv.org/abs/1706.04599)
- **[A]** Murphy (1973), *J. Applied Meteorology*. The Brier score decomposes as reliability − resolution + uncertainty. — [DOI](https://doi.org/10.1175/1520-0450(1973)012%3C0595:ANVPOT%3E2.0.CO;2)
- **[B]** Meyer, Barziy & Joubert (2023): calibration significantly improves fixed position-sizing rules applied to meta-label probabilities. — [pm-research](https://www.pm-research.com/content/iijjfds/early/2023/03/08/jfds20231119)

### Inferences
- **[calc] Sensitivity of EV to calibration error.** EV per trade in R units = p·W − (1 − p)·L − c, so ∂EV/∂p = W + L. With W = 2R and L = 1R, each 1 pp of miscalibration is 0.03R. A model that says 0.45 when the truth is 0.40 overstates EV by 0.15R. At a true p of 0.42 the whole edge is only ≈0.16R (net W = 1.9R, L = 1.1R).
- **[calc] How precisely can calibration be checked?** The standard error of the observed hit rate in a reliability bin with n points (p ≈ 0.4):

| Points per bin | SE | 95% half-width |
|---|---|---|
| 20 | 0.110 | ±0.215 |
| 50 | 0.069 | ±0.136 |
| 100 | 0.049 | ±0.096 |
| 200 | 0.035 | ±0.068 |
| 400 | 0.024 | ±0.048 |

  With 2,000 out-of-fold setups, use **5 quantile bins (~400 each)**, which gives about ±5 pp. With 10–20 live trades a month, per-bin live calibration is untestable for years. Monitor **calibration-in-the-large** (mean p̂ vs observed rate) and the **calibration slope** (logistic regression of y on logit p̂) instead. Use *all* labelled setups, including skipped ones, since labels come from market data.
- **Default procedure:**
  1. Fit L2 logistic regression.
  2. On purged out-of-fold predictions, estimate the calibration intercept and slope.
  3. If the slope is within [0.8, 1.2] and |intercept| < 0.1 logit, do nothing.
  4. Otherwise apply Platt scaling, fitted on the out-of-fold predictions (sklearn `CalibratedClassifierCV(method="sigmoid", ensemble=False)` with a purged splitter).
  5. Use beta calibration only for a GBM challenger.
  6. Isotonic regression is not allowed below 1,000 out-of-fold calibration points.
- **Never rebalance classes** (up-sampling, class weights) for a model whose p̂ feeds an EV gate. If you must, recalibrate afterwards.
- **Report:** log-loss; Brier skill score vs the base rate; calibration intercept and slope; ECE on quantile bins; AUC as secondary only.
- Add a **calibration safety margin** to the gate. Require p̂ ≥ p_breakeven + 0.04, because ±4–5 pp is the best calibration precision achievable with ~2,000 points.

### Gaps
- I found no finance-specific study comparing Platt, isotonic and beta calibration for trade-outcome probabilities at n ≈ 2,000.
- I could not read the full results of Meyer et al. (2023) (effect sizes per sizing method).

---

## 5. Labeling and leakage control: triple barrier, purging, embargo, CPCV, feature importance

### Takeaway
Triple-barrier labels are the right target. For **same-day intraday trades**, label overlap is small, so purging is simple: **group folds by trading day** and add a **≥5-trading-day embargo** for features with multi-day lookbacks. Use **CPCV** for model selection and overfitting statistics, then a single walk-forward pass and an untouched holdout. The biggest leakage risks here are not CV mechanics. They are decision-time leakage and **synthetic option prices** (Black-76 from India VIX).

### Cited Findings
- **[C]** López de Prado (2018), the main methods:
  - ch. 3: triple-barrier labels, i.e. upper (profit), lower (stop) and vertical (time) barriers. The label is whichever is touched first.
  - ch. 4: sample uniqueness weights for overlapping labels.
  - ch. 7: *purged* k-fold (drop training samples whose label windows overlap the test fold) and *embargo* (also drop training samples just after the test fold).
  - ch. 8: feature importance via MDI (in-sample and biased), MDA (permutation importance on out-of-sample folds) and SFI (single-feature importance, which avoids substitution effects).
  - ch. 12: combinatorial purged CV. With N groups and k test groups there are C(N, k) splits and φ = (k/N)·C(N, k) full backtest paths. — [Wiley](https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086)
- **[B]** Arian, Norouzi & Seco (2024), *Knowledge-Based Systems*, DOI 10.1016/j.knosys.2024.112477.
  - In a synthetic controlled environment, CPCV "demonstrated marked superiority in mitigating overfitting risks", with lower probability of backtest overfitting (PBO) and a better deflated Sharpe ratio (DSR) test statistic than walk-forward.
  - Walk-forward showed "notable shortcomings in false discovery prevention".
  - The paper also proposes bagged and adaptive CPCV variants. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110)
- **[B]** Kumar, Venkatasubramanian, Scheidegger & Friedler (2020), ICML, "Problems with Shapley-value-based explanations as feature importance measures". SHAP has mathematical problems as a feature-importance measure, and its values depend on modelling choices for correlated features. — [arXiv 2002.11097](https://arxiv.org/abs/2002.11097)
- **[C]** Chen (2026, arXiv 2608.26106) is a leakage example from this project's notes. Its "71%" logistic accuracy came from predicting close vs previous close *after* the open was known. — [alphaXiv](https://www.alphaxiv.org/abs/2608.26106)
- **[C]** Leakage-safe, search-aware evaluation and decision-time leakage papers (2026), from this project's notes. — [arXiv 2608.27734](https://www.alphaxiv.org/abs/2608.27734); [arXiv 2605.23959](https://www.alphaxiv.org/abs/2605.23959)

### Inferences
- **[calc] CPCV configurations:**

| Groups N | Test groups k | Splits C(N, k) | Backtest paths φ | Test fraction |
|---|---|---|---|---|
| 6 | 2 | 15 | 5 | 0.33 |
| 8 | 2 | 28 | 7 | 0.25 |
| 10 | 2 | 45 | 9 | 0.20 |
| 10 | 3 | 120 | 36 | 0.30 |

  Default: on 2019–2023, use **N = 10 groups of roughly half a year each, k = 2**. That gives 45 splits and 9 paths, with about 200 test setups per group.
- **Purging for this design.** Each label closes the same day (time barrier at 15:00, or 13:30 on expiry days), so label windows never cross days. Therefore:
  - Group folds by trading day, so same-day setups never sit on both sides.
  - Purge = drop the train days adjacent to each test group.
  - Embargo = 5 trading days after each test group. This covers 5-day ATR and noise-band lookbacks and short-term regime autocorrelation. If any feature uses a 14- or 20-day lookback, extend the embargo to match it.
- **Barriers on the underlying, not on synthetic premiums.** Define the target and stop on Nifty/Sensex spot or futures in units of the VIX-implied expected move for the rest of the session. Translate to premium only for the alert.
  - Black-76 prices built from India VIX (a 30-day ATM index) ignore weekly term structure, skew, intraday IV moves and bid-ask spreads. Option-level P&L in the backtest is therefore a model output, not data.
  - Use the live-recorded chain to measure that pricing error before trusting premium-based expectancy.
- **Record the realized R of time-barrier exits.** A binary "target first" label drops the P&L of trades that time out. Either:
  - model three outcomes (target / stop / time), with EV = p_T·W − p_S·L + p_X·E[R | time] − c; or
  - model the binary label and add an empirical E[R | time-out] by setup type.
- **Decision-time checklist:**
  - Features use only bars closed before the signal bar.
  - Entry is at the *next* bar, at ask plus slippage.
  - FII/DII and participant OI are usable only the next day.
  - Use days-to-expiry, not weekday. Expiry moved from Thursday to Tuesday in September 2025, and lot sizes and STT changed.
  - Live-only features (option-chain OI and flow) **cannot** enter the historical model. Log them in "shadow" mode until enough live setups exist (§8).
- **Feature importance at this scale:**
  - For logistic regression, use standardized coefficients plus a bootstrap or CV-fold sign-stability count. Keep a feature only if its sign is stable in ≥80% of folds.
  - Use MDA on purged out-of-fold predictions for the GBM challenger.
  - Treat SHAP as a description of the model, not evidence about the market.

### Gaps
- Arian et al. (2024) is synthetic. I found no real-data study showing CPCV-selected strategies outperform walk-forward-selected ones *live*.
- I found no study quantifying Black-76-from-VIX pricing error for Nifty or Sensex *weekly* options intraday. This needs measuring from the live-recorded chain.

---

## 6. Multiple testing and overfitting: DSR, PBO, t > 3, MinBTL, false strategy theorem, experiment registry

### Takeaway
Every configuration you try raises the bar. For a realistic edge (per-trade Sharpe about 0.13, i.e. p ≈ 0.43 at 1.9R/−1.1R) and ~600 out-of-sample trades, the deflated Sharpe stays above 0.95 only if you have tried **about 10 or fewer effectively independent configurations** [calc]. A t-statistic ≥ 3 needs **about 550 trades**. Keep a registry of every trial from day 1.

### Cited Findings
- **[B]** Bailey & López de Prado (2014), "The Deflated Sharpe Ratio", *J. Portfolio Management* 40(5), DOI 10.3905/jpm.2014.40.5.094.
  - **Expected maximum Sharpe across N independent trials:** E[max SR] ≈ √V[SR]·[(1 − γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e))], where γ ≈ 0.5772 is the Euler–Mascheroni constant.
  - **DSR** = Φ( (SR̂ − SR₀)·√(T − 1) / √(1 − γ̂₃·SR̂ + ((γ̂₄ − 1)/4)·SR̂²) ), with SR₀ = E[max SR], γ̂₃ = skewness and γ̂₄ = kurtosis.
  - Worked example: an annualized SR of 2.5 on 5 years of daily data (T = 1,250) with skew −3 and kurtosis 10, after N = 100 trials, gives DSR ≈ 0.90 ("only a 90% chance that the true SR... is greater than zero"). With N = 46 trials the DSR would have been 0.9505. With normal returns the strategy would have failed only after N = 88 trials.
  - "Multiple testing exercises should be carefully planned in advance... Investment theory, not computational power, should motivate what experiments are worth conducting." — [PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf); [DOI](https://doi.org/10.3905/jpm.2014.40.5.094)
- **[B]** Bailey, Borwein, López de Prado & Zhu (2017), "The probability of backtest overfitting", *J. Computational Finance* 20(4), DOI 10.21314/JCF.2016.322. PBO is the probability that the configuration chosen as best in-sample underperforms the median of all N configurations out of sample. It is estimated by combinatorially symmetric cross-validation (CSCV), in which every training split is reused as a test split. — [DOI](https://doi.org/10.21314/JCF.2016.322); [CRAN pbo](https://cran.r-project.org/web/packages/pbo/readme/README.html)
- **[B]** Bailey, Borwein, López de Prado & Zhu (2014), "Pseudo-Mathematics and Financial Charlatanism", *Notices of the AMS* 61(5).
  - Minimum backtest length rises with the number of trials, roughly MinBTL < 2·ln(N) / E[max SR]².
  - "If only five years of data are available, no more than forty-five independent model configurations should be tried". At that point the expected maximum in-sample SR is 1 while the expected out-of-sample SR is 0. — [AMS PDF](https://www.ams.org/notices/201405/rnoti-p458.pdf); [DOI](https://doi.org/10.1090/noti1105)
- **[B]** López de Prado & Bailey, "The False Strategy Theorem". The expected maximum Sharpe of N zero-skill strategies grows with N and with the variance across trials. With enough unreported trials, no Sharpe ratio is high enough to reject the hypothesis that a strategy is false. — [SSRN 3221798](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3221798)
- **[A]** Harvey, Liu & Zhu (2016), "…and the Cross-Section of Expected Returns", *RFS* 29(1). After adjusting for multiple testing (Bonferroni, Holm, BHY), a newly discovered factor needs a **t-ratio above 3.0**, not 2.0. — [DOI](https://doi.org/10.1093/rfs/hhv059)
- **[B]** Arian et al. (2024): CPCV gives lower PBO and better DSR than walk-forward in synthetic tests. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110)

### Inferences
- **[calc] DSR worked for this system.** Per-trade outcomes are +1.9R or −1.1R with p = 0.43, giving per-trade SR = 0.128, skew 0.28 and kurtosis 1.08. I assumed the standard deviation of per-trade SR across trials is 0.04.

| Effective trials N | SR₀ = E[max] | DSR at T=300 trades | T=600 | T=1,000 |
|---|---|---|---|---|
| 1 | 0 | 0.988 | 0.999 | 1.000 |
| 10 | 0.063 | 0.874 | 0.947 | 0.982 |
| 30 | 0.083 | 0.786 | 0.869 | 0.926 |
| 100 | 0.101 | 0.681 | 0.747 | 0.805 |

  **Trial budget:** if the meta-filter leaves about 600–1,000 backtest trades, keep the effectively independent configurations at **≤10–15** for the whole research programme. Count every setup variant, feature-set change, barrier choice and model class.
- **[calc] t-stat requirement:** t = SR_trade·√T. At SR_trade = 0.128, t ≥ 2 needs T ≥ 245 trades and t ≥ 3 needs T ≥ 550.
- **Experiment registry** (a CSV or SQLite table, append-only). One row per run:
  - run_id, timestamp, git commit hash, data snapshot hash
  - hypothesis in one sentence, and which family or setup changed
  - parameter dict, CV scheme, number of setups and trades
  - out-of-sample log-loss, Brier, calibration slope, net expectancy in R, t-stat
  - cumulative trial count, and the cluster ID (runs differing only in nuisance parameters share a cluster)
  - a "holdout touched?" flag
  
  The DSR's N = number of clusters (effectively independent trials). The 2026 holdout may be evaluated **once**; any later change to the model starts a new registry era and needs fresh prospective data.
- **PBO acceptance:** PBO ≤ 0.2 on the CSCV of the shortlisted configurations [D: default threshold].

### Gaps
- No source gives a principled way to set the cross-trial SR variance V[SR] for a programme with few trials. I assumed 0.04 per trade. Estimate it from the registry's actual dispersion.
- I could not verify the numeric example in the False Strategy Theorem paper itself.

---

## 7. Statistical power with few trades, and sequential go/no-go testing

### Takeaway
Telling a 42% win rate from 36% at a 1:2 payoff needs **about 400 trades** (one-sided α = 0.05, power 0.8). That is **about 2–2.5 years at 15–20 trades a month.** A 40-trade paper phase therefore cannot validate the edge. It can only catch implementation errors, cost or slippage overruns, and gross failure. Use a **Wald SPRT or a Bayesian beta-binomial rule** with deliberately wide hypotheses (breakeven vs breakeven + 8 pp). This decides in about 70–110 trades on average.

### Cited Findings
- **[B]** Wald (1945), "Sequential Tests of Statistical Hypotheses", *Annals of Mathematical Statistics* 16(2). The SPRT accumulates the log-likelihood ratio Λ_n. It accepts H1 when Λ_n ≥ A = ln((1 − β)/α) and accepts H0 when Λ_n ≤ B = ln(β/(1 − α)). Among tests with the same error rates, it minimizes the expected sample size. — [DOI](https://doi.org/10.1214/aoms/1177731118)
- **[B]** Chu, Wu & Swartz (2018), "Modified Kelly criteria", *J. Quantitative Analysis in Sports*. They put a Beta prior on the unknown win probability p and update it with the observed record. This is the beta-binomial framework applied to a betting edge. — [DOI](https://doi.org/10.1515/jqas-2017-0122); [PDF](https://www.sfu.ca/~tswartz/papers/kelly.pdf)
- **[C]** This project's report sets the break-even formula as (1 + c)/(W/L + 1), and puts round-trip costs per Nifty lot at ≈₹70 in fees plus 1–2 points of slippage per side (65 units per lot). — `reports/RESEARCH_REPORT.md` §4

### Inferences
- **[calc] Break-even win rate depends heavily on rupee costs:** p_be = (L + C)/(T + L), where L is the stop loss in ₹, T the target in ₹, and C the all-in round-trip cost in ₹ including slippage.

| Target T | Stop L | C = ₹0 | C = ₹70 | C = ₹100 | C = ₹150 | C = ₹200 |
|---|---|---|---|---|---|---|
| ₹800 | ₹200 | 20.0% | 27.0% | 30.0% | 35.0% | 40.0% |
| ₹800 | ₹350 | 30.4% | 36.5% | 39.1% | 43.5% | 47.8% |
| ₹800 | ₹400 (1:2) | 33.3% | 39.2% | 41.7% | 45.8% | 50.0% |
| ₹800 | ₹500 | 38.5% | 43.8% | 46.2% | 50.0% | 53.8% |
| ₹1,000 | ₹350 | 25.9% | 31.1% | 33.3% | 37.0% | 40.7% |
| ₹1,000 | ₹500 (1:2) | 33.3% | 38.0% | 40.0% | 43.3% | 46.7% |

  The brief's "35–38% breakeven at 1:2" holds only if all-in costs are ≤ ~₹70 per round trip. That is roughly fees alone, with almost no slippage. With 0.5 point of slippage per side (₹65 for a 65-unit lot), costs are ~₹135 and breakeven at 1:2 is ~42–44%. **Measure real fills during paper trading before fixing p_be.**
- **[calc] Fixed-n sample sizes.** One-sided test of H0: p = p0 vs H1: p = p1, α = 0.05: n = [z_α·√(p0(1 − p0)) + z_β·√(p1(1 − p1))]² / (p1 − p0)². The exact binomial n is in brackets.

| p0 (no edge) | p1 (edge) | n, power 0.8 | n, power 0.9 | Months at 15 trades/mo (power 0.8) |
|---|---|---|---|---|
| 0.36 | 0.42 | 404 [412] | 562 | ~27 |
| 0.37 | 0.42 | 586 [592] | 815 | ~39 |
| 0.36 | 0.45 | 181 [185] | 252 | ~12 |
| 0.37 | 0.45 | 230 [238] | 321 | ~16 |
| 0.33 | 0.42 | 175 [184] | 245 | ~12 |
| 0.37 | 0.50 | 88 [89] | 122 | ~6 |

  Testing net expectancy > 0 directly (t-test on R-multiples, +1.9R / −1.1R) gives similar or larger numbers: at p = 0.42 (mean 0.16R, SD 1.48R) n = 529 for power 0.8; at p = 0.45 n = 220; at p = 0.40 n = 1,335.
- **[calc] What a given number of trades tells you** (observed win rate 42%):

| Trades | 95% Clopper-Pearson CI | P(observed ≤ 37% \| true 42%) | P(observed ≥ 42% \| true 36%) |
|---|---|---|---|
| 30 | 25.5%–62.6% | 0.35 | 0.26 |
| 40 | 27.0%–59.1% | 0.23 | 0.24 |
| 60 | 29.1%–55.1% | 0.24 | 0.15 |
| 100 | 32.2%–52.3% | 0.18 | 0.13 |
| 150 | 34.0%–50.3% | 0.11 | 0.08 |
| 200 | 35.1%–49.2% | 0.09 | 0.05 |
| 300 | 36.4%–47.8% | 0.04 | 0.02 |
| 400 | 37.1%–47.0% | 0.02 | 0.01 |

  After 40 paper trades, a genuinely good system (42%) looks like a loser (≤37%) 23% of the time, and a no-edge system (36%) looks good (≥42%) 24% of the time.
- **[calc] Wald SPRT, simulated** (5,000 runs each). Per-trade log-LR increments are ln(p1/p0) for a win and ln((1 − p1)/(1 − p0)) for a loss.

| H0 | H1 | α | β | True p | Mean trades to decide | Median | 90th percentile | P(accept H1) |
|---|---|---|---|---|---|---|---|---|
| 0.36 | 0.42 | 0.05 | 0.20 | 0.36 | 185 | 130 | 396 | 0.05 |
| 0.36 | 0.42 | 0.05 | 0.20 | 0.42 | 262 | 213 | 505 | 0.81 |
| 0.36 | 0.45 | 0.05 | 0.20 | 0.36 | 85 | 60 | 184 | 0.04 |
| 0.36 | 0.45 | 0.05 | 0.20 | 0.45 | 118 | 97 | 226 | 0.81 |
| **0.37** | **0.45** | **0.10** | **0.20** | 0.37 | 95 | 70 | 195 | 0.09 |
| **0.37** | **0.45** | **0.10** | **0.20** | 0.45 | 109 | 87 | 211 | 0.80 |

  **Default SPRT** (bold): H0 p = p_be (0.37 shown; re-set p_be from measured costs) vs H1 p = p_be + 0.08, α = 0.10, β = 0.20. Increments are +0.1957 per win and −0.1358 per loss. Thresholds are A = 2.079 and B = −1.504. As win-count lines after n trades:
  - **GO (accept H1)** if wins ≥ 6.27 + 0.4097·n. For example, n = 40 needs ≥23 wins (57%) and n = 100 needs ≥48.
  - **STOP (accept H0)** if wins ≤ −4.54 + 0.4097·n. For example, n = 40 stops at ≤11 wins (28%) and n = 100 at ≤36.
- **[calc] Bayesian beta-binomial alternative.** Posterior Beta(a₀ + wins, b₀ + losses). Two priors: flat Beta(1, 1), and a sceptical Beta(11, 19) (mean 0.367, worth 30 pseudo-trades centred on breakeven). The table shows P(p > 0.37):

| Trades | Wins (rate) | Flat prior | Sceptical prior | Sceptical 90% credible interval |
|---|---|---|---|---|
| 20 | 9 (45%) | 0.78 | 0.66 | 0.289–0.515 |
| 40 | 17 (42%) | 0.78 | 0.69 | 0.306–0.497 |
| 40 | 14 (35%) | 0.42 | 0.40 | 0.266–0.453 |
| 60 | 26 (43%) | 0.85 | 0.78 | 0.327–0.497 |
| 100 | 42 (42%) | 0.85 | 0.81 | 0.338–0.479 |
| 100 | 38 (38%) | 0.60 | 0.56 | 0.308–0.448 |
| 150 | 63 (42%) | 0.90 | 0.87 | 0.351–0.472 |
| 200 | 84 (42%) | 0.93 | 0.91 | 0.360–0.467 |

  A Bayesian rule with "go at P(p > p_be) ≥ 0.9" reaches a decision for a true-42% system only after about 150–200 trades. The SPRT with wide hypotheses is faster, because it gives up power against small edges.
- **Speed-up that is legitimate:** score calibration and hit rate on **all labelled setups** (~23 a month), not only the alerts you act on, because barrier outcomes come from market data. Cost and slippage checks still need real or paper fills.

### Gaps
- Trades are not exactly binary: time-barrier exits give intermediate R. Power for a mixed outcome distribution should be simulated from the backtest's empirical R distribution. The binary numbers above are approximations.
- Serial correlation of outcomes (regime clustering) would inflate the required n. I did not quantify this.

---

## 8. Concept drift and regime change: detecting edge decay, retraining cadence

### Takeaway
Edge decay is slow to detect at 15 trades a month. A Bernoulli CUSUM tuned to false-alarm only every ~600 trades needs about **100 trades (~7 months)** to flag a drop from 42% to 33%. So pair a statistical monitor with a hard capital stop. Refit on a schedule tied to new *labelled setups* (not trades), and average expanding-window and rolling-window models rather than chasing the latest window.

### Cited Findings
- **[B]** Page (1954), "Continuous Inspection Schemes", *Biometrika* 41. The CUSUM statistic S_n = max(0, S_{n−1} + x_n) signals when S_n ≥ h. It is equivalent to a repeated SPRT. — [DOI](https://doi.org/10.1093/biomet/41.1-2.100)
- **[B]** Reynolds & Stoumbos (1999), "A CUSUM Chart for Monitoring a Proportion When Inspecting Continuously", *J. Quality Technology* 31(1). This is the Bernoulli CUSUM for binary outcomes. — [DOI](https://doi.org/10.1080/00224065.1999.11979900)
- **[B]** Gama, Žliobaitė, Bifet, Pechenizkiy & Bouchachia (2014), "A survey on concept drift adaptation", *ACM Computing Surveys* 46(4). It surveys drift detectors (e.g., Page-Hinkley and window-based detectors) and adaptation strategies (retrain, forget, ensemble). — [DOI](https://doi.org/10.1145/2523813)
- **[A]** Pesaran & Timmermann (2007), "Selection of estimation window in the presence of breaks", *J. Econometrics* 137(1). The choice between rolling and expanding windows under structural breaks trades bias against variance, and no single window dominates. — [DOI](https://doi.org/10.1016/j.jeconom.2006.03.010)
- **[A]** Zhang et al. (2020), *JAE*. Averaging forecasts across *estimation windows* (the Pesaran–Timmermann "AveW" method) handles parameter instability. Combined with the historical average, it gave a monthly R²_OS of 1.10% and 2.34% annual utility gains. — [DOI](https://doi.org/10.1002/jae.2747)
- **[C]** Structural changes in this market, from this project's report:
  - Weekly expiries moved to Tuesday (Nifty) and Thursday (Sensex).
  - Bank Nifty weeklies were removed in Nov 2024.
  - STT rose to 0.15% in April 2026.
  - Expiry settlement has used a closing auction since August 2026. — `reports/RESEARCH_REPORT.md` §1

### Inferences
- **[calc] Bernoulli CUSUM for edge loss.** In control p0 = 0.42, out of control p1 = 0.33. Increments are +ln(0.67/0.58) = +0.144 per loss and ln(0.33/0.42) = −0.241 per win, floored at 0. Simulated average run lengths (ARL):

| Threshold h | False alarm ARL0 (true 0.42) | Detection ARL1 (true 0.33) | Detection (true 0.30) |
|---|---|---|---|
| 2.0 | 312 trades (median 219) | 76 (median 62) | 55 |
| **2.5** | **603 (median 418)** | **102 (median 84)** | **72** |
| 3.0 | 1,089 (median 770) | 130 (median 107) | 90 |
| 3.5 | 1,814 (median 1,388) | 158 (median 135) | 107 |

  Default h = 2.5: about one false alarm every ~3 years at 15–20 trades a month, and detection of a collapse to 33% in ~5–7 months. A Page-Hinkley or CUSUM test on R-multiples is the analogue if exits are not binary. Set p0 to the *validated* win rate, not the backtest's best case.
- **Capital stop.** Drawdowns of 10–20R occur even with a real edge (§9 simulation), so a tight drawdown stop cannot tell bad luck from no edge. Use the CUSUM/SPRT for the statistical decision, and a separate **hard pause at −40% of starting capital** to protect capital [D].
- **Retraining cadence** [D, informed by Pesaran & Timmermann and Zhang et al.]:
  - Refit every 6 months, *or* after ≥250 new labelled setups, whichever comes later.
  - Each refit fits (a) an expanding-window model and (b) a 3-year rolling model, and averages their probabilities.
  - Re-check calibration intercept and slope on the new out-of-fold data. Change only the intercept if the slope is fine.
  - Do not refit after every losing streak.
  - Each refit is a registry entry. Changes to features or model class count as new trials.
- **Online updating:** a full online learner is not justified at ~23 labelled setups a month. The beta-binomial posterior on the *live* win rate (§7) is the online component.
- **Shadow features.** Live-only option-chain features (OI change, PCR-OI, first-10-minute option order imbalance) are logged from day 1 but not used. Test them after ≥300 live labelled setups (~12–14 months), as a pre-registered single trial: the model with the feature vs the frozen model on prospective log-loss.

### Gaps
- I found no peer-reviewed evidence on the *optimal* retraining frequency for intraday trade-filter models, nor any study of how fast intraday edges decay in Indian index options.
- I found no study of CUSUM or Page-Hinkley applied to monitoring retail trading strategies. The ARL numbers here are my simulations, not published values.

---

## 9. Position sizing from calibrated probabilities: Kelly, fractional Kelly, 1-lot granularity

### Takeaway
At these payoffs, full Kelly *net of costs* is only about 2–8% of capital per trade for win rates of 38–42%. Estimation error argues for roughly half that. The brief's ₹200–500 risk on ₹5,000 is **4–10% per trade, at or above full Kelly** for plausible edges. With 1-lot granularity, "sizing" collapses into three choices: trade or skip, stop distance, and strike. Calibrated p̂ should drive the **gate**, not a size multiplier, until the edge is validated live.

### Cited Findings
- **[B]** MacLean, Thorp & Ziemba (2010), "Long-term capital growth: the good and bad properties of the Kelly and fractional Kelly capital growth criteria", *Quantitative Finance* 10(7). Kelly maximizes long-run growth but is very risky in the short run. Fractional Kelly gives up growth for security. — [DOI](https://doi.org/10.1080/14697688.2010.506108)
- **[B]** Baker & McHale (2013), "Optimal Betting Under Parameter Uncertainty: Improving the Kelly Criterion", *Decision Analysis* 10(3). When p is estimated, the out-of-sample-optimal bet is a **shrunk** Kelly fraction k·f*(p̂) with 0 < k < 1. They give an approximate "back of envelope" shrinkage factor and show shrunk Kelly beats raw Kelly in simulations and tennis-betting data. — [DOI](https://doi.org/10.1287/deca.2013.0271); [ResearchGate](https://www.researchgate.net/publication/262425087_Optimal_Betting_Under_Parameter_Uncertainty_Improving_the_Kelly_Criterion)
- **[B]** Chu, Wu & Swartz (2018). With a Beta prior on p, the Bayes-optimal fractions are smaller than Kelly. In their main example the preferred estimator gave **0.048 vs raw Kelly 0.089**, i.e. "nearly corresponds to half-Kelly". They call this "a theoretical rationale for the use of half-Kelly". — [PDF](https://www.sfu.ca/~tswartz/papers/kelly.pdf)
- **[B]** Meyer, Barziy & Joubert (2023): calibrated meta-label probabilities improve fixed-function sizing rules. — [pm-research](https://www.pm-research.com/content/iijjfds/early/2023/03/08/jfds20231119)
- **[C]** Project facts: the Nifty lot is 65. The report's own risk rule was "at most 1% of trading capital at the stop", which the ₹5,000 / ₹200–500 brief now exceeds 4–10×. — `reports/RESEARCH_REPORT.md` §1, §6

### Inferences
- **[calc] Kelly for a two-outcome trade.** Net win W·R with probability p, net loss L·R otherwise: f* = (p·W − (1 − p)·L)/(W·L), as a fraction of capital at risk at the stop.

| p | f* with W = 2.0, L = 1.0 (no costs) | f* with W = 1.9, L = 1.1 (0.1R costs) | Half Kelly (with costs) |
|---|---|---|---|
| 0.37 | 5.5% | 0.5% | 0.2% |
| 0.38 | 7.0% | 1.9% | 1.0% |
| 0.40 | 10.0% | 4.8% | 2.4% |
| 0.42 | 13.0% | 7.7% | 3.8% |
| 0.45 | 17.5% | 12.0% | 6.0% |
| 0.50 | 25.0% | 19.1% | 9.6% |

- **[calc] Monte Carlo of ruin and drawdown.** ₹5,000 start, fixed rupee risk R per trade, net +1.9R/−1.1R, 120 trades (~8 months), 20,000 paths, no stopping. *Hit −50%* = equity ever falls below ₹2,500. *Ruin* = equity ever falls below the next stop. Max drawdowns above ₹5,000 are hypothetical, because ruin would end trading first.

| True p | Risk R | P(hit −50%) | P(ruin) | Median max drawdown | P(below ₹5,000 at end) | Median longest losing streak (90th pct) |
|---|---|---|---|---|---|---|
| 0.36 | ₹200 | 0.46 | 0.15 | ₹3,580 | 0.58 | 9 (13) |
| 0.40 | ₹200 | 0.20 | 0.03 | ₹2,660 | 0.24 | 8 (11) |
| 0.40 | ₹500 | 0.53 | 0.32 | ₹6,600 | 0.20 | 8 (11) |
| 0.42 | ₹200 | 0.12 | 0.01 | ₹2,320 | 0.13 | 7 (11) |
| 0.42 | ₹350 | 0.29 | 0.10 | ₹4,060 | 0.13 | 7 (11) |
| 0.42 | ₹500 | 0.42 | 0.22 | ₹5,850 | 0.10 | 7 (11) |
| 0.45 | ₹200 | 0.04 | 0.002 | ₹1,980 | 0.04 | 7 (10) |
| 0.45 | ₹500 | 0.28 | 0.11 | ₹4,950 | 0.03 | 7 (10) |

  With a *genuine* 42% edge, risking ₹500 a trade gives a 42% chance of halving the account within ~8 months, and a 22% chance of being unable to place the next trade.
- **The capital constraint is binding on both sides.** Larger R breaches Kelly and drives ruin risk. Smaller R makes the fixed ~₹70+ round-trip cost a bigger fraction of R, which raises p_be (e.g., L = ₹250, T = ₹500, C = ₹100 gives p_be = 46.7%). The report writer should state this plainly: **₹5,000 with 1-lot index options sits at the edge of viability.**
- **Premium affordability [calc, to verify on the live chain].** ₹5,000 / 65 = ₹76.9 maximum premium per unit for one Nifty lot, before costs. By the Black-76 ATM approximation (0.4·F·σ·√t), ATM Nifty weeklies at VIX ≈ 14.7 cost about ₹120 with 3 days left and about ₹70 with 1 day left. So outside the last ~1–1.5 days, ₹5,000 may force out-of-the-money strikes. That changes delta and theta, and therefore the p̂ to payoff mapping. The model must be trained on the strikes you can actually afford.
- **Default sizing policy:**
  - 1 lot only.
  - Stop risk capped at ₹250 (5% of capital, about half Kelly at p ≈ 0.42 net of costs) until the SPRT accepts H1.
  - Skip any alert whose premium × lot + costs exceeds available capital, or whose stop risk exceeds the cap.
  - No probability-scaled sizing until ≥150 live trades and posterior P(p > p_be) ≥ 0.9. After that, at most half Kelly using the posterior *lower* 10% quantile of p.
  
  [D: defaults; consistent with Baker & McHale, Chu et al. and MacLean et al.]

### Gaps
- I could not extract Baker & McHale's exact shrinkage formula; the paper was paywalled and the PDF unreadable.
- I found no study of Kelly sizing with the integer constraints and fixed-cost structure of retail index options.

---

## 10. Recommended pipeline and validation protocol (defaults)

### Takeaway
Build a small, conservative stack:
1. Frozen rule-based setups.
2. Four sign-aligned family scores.
3. One pooled L2-logistic meta-model with ≤9 columns (effective df ≈ 4–6).
4. Platt recalibration only if needed.
5. An EV gate with a calibration margin.
6. 1-lot sizing.

Validate with CPCV on 2019–2023, walk-forward on 2024–2025 and a one-shot 2026 holdout, under a trial budget of ≤10–15 effective configurations and DSR ≥ 0.95. Paper-trade to verify costs and mechanics, then go live with 1 lot under an SPRT (p_be vs p_be + 8 pp), a CUSUM kill-switch and a −40% capital pause. Expect a statistically convincing verdict only after ~100–250 trades.

### Cited Findings
- **[A]** Equal or shrunk weights beat estimated weights in small samples (Timmermann 2006; Smith & Wallis 2009; Rapach et al. 2010). — [Timmermann](https://doi.org/10.1016/S1574-0706(05)01004-9); [Smith & Wallis](https://doi.org/10.1111/j.1468-0084.2008.00541.x); [Rapach et al.](https://doi.org/10.1093/rfs/hhp063)
- **[A]** Logistic regression matches ML when comparisons are unbiased, and ML needs about 10× more events per variable (Christodoulou 2019; van der Ploeg 2014). Sample size is set by shrinkage targets (Riley 2019). — [Christodoulou](https://doi.org/10.1016/j.jclinepi.2019.02.004); [van der Ploeg](https://bmcmedresmethodol.biomedcentral.com/articles/10.1186/1471-2288-14-137); [Riley](https://doi.org/10.1002/sim.7992)
- **[A]/[C]** Platt scaling for small calibration sets; isotonic only above ~1,000 samples (Niculescu-Mizil & Caruana 2005; sklearn). — [N-M & C](https://doi.org/10.1145/1102351.1102430); [sklearn](https://scikit-learn.org/stable/modules/calibration.html)
- **[B]** DSR, PBO, MinBTL and the false strategy theorem (Bailey & López de Prado 2014; Bailey et al. 2014, 2017). t > 3 under multiple testing (Harvey, Liu & Zhu 2016, grade A). — [DSR](https://doi.org/10.3905/jpm.2014.40.5.094); [PBO](https://doi.org/10.21314/JCF.2016.322); [MinBTL](https://doi.org/10.1090/noti1105); [HLZ](https://doi.org/10.1093/rfs/hhv059)
- **[B]** CPCV beats walk-forward on false-discovery control in synthetic tests (Arian et al. 2024). — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110)
- **[B]** SPRT (Wald 1945), CUSUM (Page 1954; Reynolds & Stoumbos 1999) and shrunk Kelly (Baker & McHale 2013; Chu et al. 2018). — [Wald](https://doi.org/10.1214/aoms/1177731118); [Page](https://doi.org/10.1093/biomet/41.1-2.100); [Baker & McHale](https://doi.org/10.1287/deca.2013.0271)

### Inferences

**A. Architecture (defaults)** [D, synthesized from §1–9]

| Layer | What it does | Default |
|---|---|---|
| L0 Data | Decision-time snapshots | 1-min index data with features computed on closed bars only. Entry at the next bar at ask plus measured slippage. Days-to-expiry, not weekday. Per-date lot size, STT and expiry rules. |
| L1 Setups (side) | 4 rule families: noise-band breakout, first-hour continuation, gap recovery, late-day momentum | Parameters fixed from the literature or one coarse grid. **≤2 variants per setup** go into the registry. The output is side + setup_id. |
| L2 Family scores | One sign-aligned z-score per family, winsorized at ±3 and fitted on the training window | **Technical** (e.g., distance beyond noise band in band widths, first-30-min return). **Options-implied, historical** (VIX − 10-day realized vol, VIX 1-day change). **Macro/context** (gap vs prior US session, event-day flag as a veto). **Sentiment** = veto/shock flag only. Equal-weight consensus score = baseline. |
| L3 Meta-model | P(target before stop before time barrier) | **L2 logistic regression** with columns: 3 setup dummies + 3–4 family scores + 1 regime feature + 1 session-time or days-to-expiry feature, i.e. **≤9 columns**. C chosen by nested purged CV. Target effective df ≈ 4–6. Keep a feature only if its sign is stable in ≥80% of folds. No class rebalancing. **Challenger:** LightGBM, depth 2, 100–300 trees, learning rate 0.03–0.05, min_child_samples ≥ 50, monotone constraints, beta/Platt calibration. It must beat LR by ≥1% relative log-loss with calibration slope no worse. |
| L4 Calibration | Make p̂ trustworthy | Check intercept and slope on purged out-of-fold predictions. Slope within [0.8, 1.2] and \|intercept\| < 0.1 → none. Otherwise Platt. Isotonic only with ≥1,000 out-of-fold points *and* a log-loss win. 5 quantile bins for reliability plots. |
| L5 EV gate | Decide whether to alert | EV = p̂_T·W_net − p̂_S·L_net + p̂_X·E[R \| time] − C ≥ **+0.10R**, **and** p̂ ≥ p_be + **0.04**. p_be comes from *measured* costs (§7 table). With binary labels, use p̂ and the empirical E[R \| time-out]. |
| L6 Sizing | 1 lot | Stop risk ≤ ₹250 until SPRT accepts H1. Skip if premium × lot + costs > capital. No probability-scaled sizing until ≥150 live trades and P(p > p_be) ≥ 0.9; then ≤ half Kelly on the posterior 10th-percentile p. |
| L7 Journal | Every setup, taken or not | Log features, p̂, label (from market data), fills, costs and slippage. Shadow-log live-only option-chain features. |

**B. Historical validation protocol (defaults)**
1. **Registry first.** Append-only, one row per run (fields in §6). The trial budget for the whole programme is **≤15 effectively independent configurations**. The DSR uses the registry's cluster count.
2. **Splits.**
   - Development 2019–2023: **CPCV with N = 10 half-year groups, k = 2** (45 splits, 9 paths). Groups formed by trading day, purge adjacent days, **5-trading-day embargo** (longer if features use longer lookbacks).
   - Validation 2024–2025: **walk-forward**, expanding window, refit every 6 months, with the model frozen in between.
   - **Holdout 2026 YTD: evaluated once.**
3. **Model-quality metrics** (out-of-fold, CPCV): log-loss, Brier skill vs base rate (> 0 required), calibration slope 0.8–1.2, AUC (reported only).
4. **Trade-level pass bar** on the 2024–2025 walk-forward *and* in aggregate:
   - net expectancy > 0 after per-date costs, using **measured or pessimistic slippage**
   - t-stat ≥ 2 on walk-forward alone, and ≥ 3 if registry clusters > 20
   - **DSR ≥ 0.95** (N = registry clusters)
   - **PBO ≤ 0.2** on the shortlisted configurations
   - the same sign of expectancy in ≥4 of the 5 development years and in both validation years
   - beats two baselines: the equal-weight consensus score with a fixed threshold, and "all setups, no meta-filter"
5. **Model-risk check on option prices.** Compare Black-76-from-VIX premiums with the live-recorded chain for every recorded signal. If the median absolute error of the premium *change* over the holding period exceeds ~15%, use spot-barrier P&L translated through recorded deltas instead. [D: threshold]

**C. Paper-trading and live protocol (defaults)**
1. **Paper phase: ≥40 alerts and ≥10 weeks.** Purpose: mechanics, costs and slippage. *Not* edge proof (§7: 40 trades misclassify ~1 in 4 cases).
   - **Pass:** zero unresolved implementation defects; measured all-in cost per round trip ≤ the backtest assumption + 20% (if not, recompute p_be and re-run validation as a new registry era); calibration-in-the-large on all labelled setups, |mean p̂ − observed| ≤ 0.08; SPRT not at the STOP line.
   - **Fail-fast:** SPRT STOP line reached (≤11 wins in 40 at p_be = 0.37), or Bayesian P(p > p_be) < 0.2.
2. **Live phase, 1 lot.** The SPRT continues from the paper record: **H0 p = p_be vs H1 p = p_be + 0.08, α = 0.10, β = 0.20**. For p_be = 0.37: GO if wins ≥ 6.27 + 0.41n, STOP if wins ≤ −4.54 + 0.41n. Expected decision after ~95–110 trades (~5–7 months at 15–20 a month); 90th percentile ~200 trades.
   - Report the Bayesian posterior with the sceptical Beta(11, 19) prior alongside.
3. **Scale-up gate** (only relevant if capital grows): SPRT accepted H1, **≥150 live trades**, P(p > p_be) ≥ 0.9, and live expectancy above the 5th percentile of the walk-forward distribution.
4. **Kill-switches**, whichever triggers first:
   - Bernoulli CUSUM (p0 = validated win rate, p1 = p0 − 0.09, **h = 2.5**; ~600-trade false-alarm ARL, ~100-trade detection)
   - SPRT STOP line
   - **−40% of starting capital** (pause and review)
   - live costs > assumption + 30%
5. **Refits:** every 6 months or after ≥250 new labelled setups, whichever is later. Average expanding-window and 3-year rolling models. Each refit is a registry entry. Live-only features are tested once, after ≥300 live labelled setups, as a single pre-registered trial.

**D. Sample-size planning summary for the paper and live phases** [calc]

| Question | Trades needed | At 10 / 15 / 20 trades a month |
|---|---|---|
| Catch gross failure (true p ≤ 0.28) or cost blow-up | ~40 | 4 / 2.7 / 2 months |
| SPRT decision, p_be vs p_be + 0.08 (mean) | ~95–110 | 10 / 7 / 5 months |
| Fixed test, 0.36 vs 0.45 (power 0.8) | ~185 | 18 / 12 / 9 months |
| Fixed test, 0.36 vs 0.42 (power 0.8) | ~410 | 41 / 27 / 21 months |
| Net expectancy t ≥ 3 at a p = 0.43 edge | ~550 | 55 / 37 / 28 months |
| CUSUM detects a drop from 0.42 to 0.33 (mean) | ~100 | 10 / 7 / 5 months |

**E. Points the report writer should surface**
- The 35–38% breakeven in the brief assumes near-zero slippage. Measure it.
- ₹200–500 risk on ₹5,000 is 4–10% per trade, which exceeds the project's own 1% rule and full Kelly at realistic edges. The −50% drawdown probability is 12–42% over 8 months *even with a 42% edge*.
- ₹5,000 may not buy one ATM Nifty weekly lot except near expiry.
- No amount of paper trading at 10–20 trades a month validates a 6-pp edge within a year. The design therefore puts most of the statistical burden on an honest, trial-counted historical validation and on wide-hypothesis sequential tests.

### Gaps
- All default thresholds marked [D] (EV ≥ +0.10R, margin 0.04, PBO ≤ 0.2, −40% pause, the 6-month and 250-setup refit rule, the 15% premium-error tolerance) are my synthesis. No source validates these specific numbers.
- The power and ruin calculations assume independent binary outcomes with fixed net payoffs (+1.9R / −1.1R). Real outcomes include time-exits and regime clustering. Redo them with the backtest's empirical R-multiple distribution once it exists.
- I could not verify the actual round-trip slippage on Nifty and Sensex weekly options at ATM or OTM strikes, or the current Sensex lot size. These must come from live-chain recordings and the broker's contract notes.
