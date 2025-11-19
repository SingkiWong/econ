# Numerical Simulation: Human Capital Accumulation and Mediation Effects

This repository contains numerical simulations for a three-generation OLG model focusing on:
1. **Human capital accumulation with intergenerational time inputs**
2. **Mediation effects of family support on saving rates**

## Key Features

### 1. Human Capital Accumulation Function

**Equation (1):**
```
h_{t+1} = A · h_t^α · e_t^β · (θ_c·τ_c + θ_g·τ_g)^γ
```

Where:
- **τ_c**: Children's time input for grandchildren education
- **τ_g**: Grandparents' time input for intergenerational care
- **θ_c = 1.0**: Children's time efficiency parameter
- **θ_g = 0.7**: Grandparents' time efficiency parameter
- **Efficiency ratio θ_c/θ_g = 1.43**: Children are 43% more efficient than grandparents

### 2. Mediation Effects Decomposition

**Total Effect Equation (54):**
```
dρ_t/dD_t = Direct Effect + Support Expenditure + Care Time + Support Risk
```

Three mediation channels:
1. **Support Expenditure Mediation** (negative): D_t↑ → τ_o↑ → ρ_t↓
2. **Care Time Mediation** (positive): D_t↑ → τ_o(time)↑ → precautionary saving↑
3. **Support Risk Mediation** (positive): D_t↑ → p↑ → precautionary saving↑

## Generated Files

### Figures
- **figure1_human_capital.png**: Human capital sensitivity to time inputs (4 subplots)
  - (a) Heatmap of h_{t+1} vs τ_c and τ_g
  - (b) Marginal effect of children's time (fixed τ_g=0.15)
  - (c) Marginal effect of grandparents' time (fixed τ_c=0.15)
  - (d) Intergenerational time complementarity

- **figure2_mediation_effects.png**: Mediation effects decomposition (4 subplots)
  - (a) Individual mediation effects over aging
  - (b) Total effect on saving rate
  - (c) Evolution of endogenous support variables
  - (d) Cumulative contribution of mediation effects

- **figure3_saving_rate.png**: Saving rate and population structure (2 subplots)
  - (a) Saving rate vs old-age dependency ratio D_t
  - (b) Saving rate vs child dependency ratio C_t

### Data Files
- **data_human_capital.csv**: 400 data points for time input sensitivity
- **data_mediation_effects.csv**: 30 data points for mediation decomposition
- **data_saving_rate.csv**: 30 data points for saving rate analysis

### Code
- **model_simulation.py**: Complete OLG model simulation program (600+ lines)
- **simulation_report.md**: Detailed Chinese analysis report

## Simulation Results

### Human Capital Accumulation
- Parameter range: h_{t+1} ∈ [0.543, 0.929]
- Children's time input shows 20% higher marginal effect than grandparents'
- Intergenerational time inputs exhibit imperfect substitutability

### Mediation Effects (at D_t = 1.0)
| Effect Type | Value | Sign | Share |
|------------|-------|------|-------|
| Direct Effect | 0.03480 | + | -39.0% |
| Support Expenditure | -0.14174 | - | 158.8% |
| Care Time | 0.00005 | + | -0.1% |
| Support Risk | 0.01766 | + | -19.8% |
| **Total Effect** | **-0.08923** | **-** | **100%** |

**Key Finding:** Support expenditure mediation dominates the total effect under baseline parameters.

### Endogenous Variables Evolution (D_t: 0.5 → 2.0)
- Support ratio τ_o: 12.5% → 35.0% (+180%)
- Care time τ_o(time): 0.098 → 0.152 (+55%)
- Survival probability p: 0.80 → 0.95 (+19%)

## Model Parameters

| Category | Parameter | Value | Description |
|----------|-----------|-------|-------------|
| **Population** | n_t | 0.8 | Current fertility rate |
| | n_{t-1} | 1.2 | Previous fertility rate |
| | p | 0.85 | Survival probability |
| **Human Capital** | A | 1.5 | TFP |
| | α | 0.3 | Human capital elasticity |
| | β | 0.4 | Education investment elasticity |
| | γ | 0.3 | Time input elasticity |
| | θ_c | 1.0 | Children efficiency |
| | θ_g | 0.7 | Grandparents efficiency |
| **Time Allocation** | τ_c | 0.15 | Children education time |
| | τ_g | 0.20 | Grandparent care time |
| | ξ | 0.5 | Time substitution coefficient |
| **Endogenization** | μ_1 | 0.15 | Dependency effect on support |
| | μ_2 | 0.10 | Pension gap coefficient |
| | ν_1 | 0.12 | Care demand coefficient |
| | κ | 0.10 | Longevity-aging coefficient |
| **Utility** | β | 0.95 | Discount factor |
| | σ | 1.5 | Risk aversion |
| **Policy** | τ | 0.20 | Pension contribution rate |
| | ρ_pen | 0.45 | Pension replacement rate |

## Usage

Run the simulation:
```bash
python model_simulation.py
```

Expected runtime: ~10-15 seconds

## Requirements
- Python 3.11+
- numpy 2.3.5
- matplotlib 3.10.7
- pandas 2.3.3
- scipy 1.16.3

## Policy Implications

1. **Pension System**: Raising pension replacement rate from 0.45 to 0.60 could reduce support burden by ~1.5 percentage points

2. **Long-term Care Insurance**: Developing care services can reduce care time burden and excessive precautionary saving

3. **Intergenerational Support**: Encouraging three-generation households can:
   - Release children's labor time through substitution effect (ξ·τ_g)
   - Contribute positively to grandchildren's human capital
   - Optimize family resource allocation

## References

Based on theoretical model in: `新建文本文档.md` (Chinese theoretical framework)

## Author

Generated: 2025-11-19
Branch: claude/add-capital-support-model-01HwXbz948LnkQApyJm8fZnC
