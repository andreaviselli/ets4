# Deep Dive Report - 2025-11-23

Analyzing 2 papers.

## 1. Diffolio: A Diffusion Model for Multivariate Probabilistic Financial Time-Series Forecasting and Portfolio Construction
**Source:** https://arxiv.org/pdf/2511.07014

### 1. The Core Innovation
The core innovation of the paper "Diffolio" is the introduction of a diffusion model specifically designed for multivariate probabilistic financial time-series forecasting and portfolio construction. The model employs a hierarchical attention architecture that includes both asset-level and market-level layers. The key equations and algorithms include:

- **Denoising Diffusion Probabilistic Models (DDPM)**: The forward process corrupts data into Gaussian noise, while the reverse process aims to recover the original data. The training objective is simplified to minimize the mean squared error between predicted noise and actual noise:
  \[
  L_{DDPM}(\theta) = E_{\tau, x_0, \epsilon} \left[ \|\epsilon - \epsilon_\theta(x_\tau, \tau)\|^2 \right]
  \]

- **Correlation-Guided Regularizer**: This regularizer aligns the attention probabilities with a stable estimate of the correlation matrix among assets:
  \[
  L_{corr} = -\frac{1}{N} \sum_{i=1}^{N} \frac{A_i \cdot \hat{target}_{i,t}}{\|A_i\|_2 \|\hat{target}_{i,t}\|_2}
  \]
  The overall training objective combines the denoising loss and the correlation-guided regularizer:
  \[
  L_{Diffolio} = L_{DDPM-cond} + \lambda_{corr} L_{corr}
  \]

### 2. Methodology
The methodology of Diffolio consists of several key components:

- **Model Architecture**: The hierarchical attention network is structured in two stages:
  - **Asset-Level Attention**: Each asset's historical returns and asset-specific covariates are processed to create an asset-specific latent vector using cross-attention.
  - **Market-Level Attention**: The asset-specific latent vectors are aggregated, and self-attention is applied to model cross-sectional dependencies and systematic covariates.

- **Feature Engineering**: The model incorporates both asset-specific characteristics (e.g., momentum, volatility) and systematic macroeconomic variables (e.g., interest rates, earnings-to-price ratios) to enhance predictive accuracy.

- **Estimation Methods**: The model uses a diffusion process for probabilistic forecasting, leveraging the DDIM (Denoising Diffusion Implicit Models) for efficient sampling during inference.

### 3. Empirical Evidence
The empirical evidence presented in the paper includes:

- **Dataset**: The model is evaluated on the daily excess returns of 12 industry portfolios from 1958 to 2023, totaling 16,613 trading days. The data is partitioned into training (1958-1999), validation (2000-2004), and test sets (2005-2023).

- **Performance Metrics**: The model's performance is assessed using:
  - **Statistical Accuracy**: Continuous Ranked Probability Score (CRPS) and Energy Score (ES) for probabilistic forecasting accuracy.
  - **Portfolio Performance**: Sharpe Ratio (SR) for the mean-variance tangency portfolio (MVP) and Certainty Equivalent (CE) for the growth-optimal portfolio (GOP).

- **Comparison to Baselines**: Diffolio outperforms various probabilistic forecasting baselines across all metrics, achieving a Sharpe ratio of 0.7206 and a certainty equivalent of 0.1611, significantly higher than the benchmarks.

### 4. Critical Takeaway
For practitioners, Diffolio represents a significant advancement in financial time-series forecasting, providing a robust framework that not only enhances predictive accuracy but also enables the construction of efficient portfolios that consistently outperform traditional models and benchmarks.

---

## 2. AIA Forecaster: Technical Report
**Source:** https://www.arxiv.org/abs/2511.07678

### 1. The Core Innovation
The AIA Forecaster introduces a novel multi-agent architecture for judgmental forecasting that leverages Large Language Models (LLMs) to perform adaptive searches over high-quality unstructured data sources. The core innovation lies in its three main components:
- **Agentic Search**: Each forecasting agent independently queries a search provider, allowing for adaptive information retrieval based on prior results.
- **Supervisor Agent**: A supervisory agent reconciles the forecasts from multiple agents, addressing discrepancies and enhancing the final output through additional queries.
- **Statistical Calibration Techniques**: The model employs statistical corrections, such as Platt scaling, to mitigate behavioral biases inherent in LLMs, particularly the tendency to hedge predictions towards 0.5.

Mathematically, the forecasting process can be represented as:
\[
\pi : (q, E) \rightarrow p
\]
where \(q\) is the binary question, \(E\) is the evidence gathered, and \(p\) is the predicted probability of the outcome.

### 2. Methodology
The AIA Forecaster's architecture consists of:
- **Multi-Agent System**: M independent agents perform searches and generate initial forecasts. Each agent's search is adaptive, allowing it to refine queries based on previous results.
- **Reconciliation Process**: The supervisor agent evaluates the forecasts from the M agents, identifies disagreements, and issues clarifying queries to enhance the quality of the final forecast.
- **Statistical Calibration**: The final probability is adjusted using techniques like Platt scaling, which applies a sigmoid transformation to the forecasts to correct for over-cautious predictions.

The overall pipeline can be expressed as:
\[
\pi_i : q \rightarrow E_1 \rightarrow E_2 \rightarrow \ldots \rightarrow (R_i, p_i)
\]
\[
\text{Supervisor} : (R_1, R_2, \ldots, R_M) \rightarrow E_{\text{supervisor}} \rightarrow p_{\text{final}}
\]

### 3. Empirical Evidence
The AIA Forecaster was evaluated on several benchmarks:
- **ForecastBench**: Includes FB-7-21, FB-8-14, and FB-Market, with a total of 1,176 questions across various domains.
- **MarketLiquid**: A more challenging benchmark with 1,610 questions sourced from liquid prediction markets.

Performance metrics include:
- **Brier Score**: A measure of the accuracy of probabilistic predictions, where lower scores indicate better performance.
- **Results**: The AIA Forecaster achieved a Brier score of 0.0753 on FB-Market, outperforming median forecasts from public surveys and expert superforecasters. However, it slightly underperformed against market consensus on the MarketLiquid benchmark, indicating that while it provides valuable information, it does not always surpass market predictions.

### 4. Critical Takeaway
The AIA Forecaster demonstrates that combining adaptive search, multi-agent collaboration, and statistical calibration can yield expert-level forecasting performance, providing practitioners with a powerful tool for judgmental forecasting that leverages unstructured data effectively.

---
