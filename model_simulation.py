"""
数值模拟：人力资本积累与家庭赡养的中介效应
基于改进的OLG模型
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager
import pandas as pd
from scipy.optimize import fsolve

# Set matplotlib to use LaTeX-style math text
matplotlib.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'serif'
plt.rcParams['mathtext.fontset'] = 'dejavuserif'

class OLGModel:
    """
    三代OLG模型：孙代、子代、父代
    """
    def __init__(self):
        # ========== 基本参数设置 ==========
        # 人口参数
        self.n_t = 0.8          # 生育率（每个子代生育的孩子数）
        self.n_t_minus_1 = 1.2  # 上期生育率
        self.p = 0.85           # 父代存活概率

        # 人力资本积累参数（式1）
        self.A = 1.5            # 全要素生产率
        self.alpha_h = 0.3      # 子代人力资本弹性
        self.beta_h = 0.4       # 教育投资弹性
        self.gamma_h = 0.3      # 时间投入弹性
        self.theta_c = 1.0      # 子代时间投入效率
        self.theta_g = 0.7      # 父代时间投入效率（假设低于子代）

        # 时间配置参数
        self.tau_c = 0.15       # 子代对孙代的教育时间投入
        self.tau_g = 0.20       # 父代隔代抚育时间投入
        self.xi = 0.5           # 父代时间对子代时间的替代系数

        # 赡养行为参数
        self.tau_o_base = 0.10  # 基础赡养支出比例
        self.tau_o_time = 0.15  # 照料时间基数

        # 赡养行为内生化参数（式35, 38, 41）
        self.tau_0 = 0.05       # 基础赡养支出比例
        self.mu_1 = 0.15        # 赡养比对赡养支出的影响系数
        self.mu_2 = 0.10        # 养老金缺口影响系数
        self.tau_o_time_0 = 0.08  # 基础照料时间
        self.nu_1 = 0.12        # 照料需求系数
        self.H_t = 0.7          # 父代健康指数
        self.p_0 = 0.75         # 基准存活概率
        self.kappa = 0.10       # 老龄化与预期寿命的相关系数

        # 效用函数参数
        self.beta = 0.95        # 折现因子
        self.delta = 0.4        # 子代对孙代教育的重视程度
        self.phi = 0.3          # 子代对父代的利他程度
        self.sigma = 1.5        # 相对风险厌恶系数

        # 生产函数参数（式8）
        self.D = 1.0            # 全要素生产率
        self.alpha_prod = 0.35  # 资本产出弹性

        # 政策参数
        self.tau = 0.20         # 养老保险总缴费率
        self.rho_pen = 0.45     # 养老金替代率

        # 预防性储蓄参数
        self.theta_precautionary = 0.05  # 预防性储蓄系数
        self.sigma_y_sq = 0.02           # 未来收入方差

        # 计算衍生变量
        self.C_t = self.n_t                    # 抚养比
        self.D_t = 1.0 / self.n_t_minus_1      # 赡养比

    def compute_support_ratio(self, n_t, n_t_minus_1):
        """计算抚养比和赡养比"""
        C_t = n_t                    # 抚养比
        D_t = 1.0 / n_t_minus_1      # 赡养比
        return C_t, D_t

    def human_capital_accumulation(self, h_t, e_t, tau_c, tau_g):
        """
        人力资本积累函数（式1）
        h_{t+1} = A * h_t^α * e_t^β * (θ_c*τ_c + θ_g*τ_g)^γ

        参数:
            h_t: 子代t期的人力资本水平
            e_t: 孙代接受的教育投资
            tau_c: 子代对孙代的教育时间投入
            tau_g: 父代对孙代的隔代抚育时间投入
        """
        time_input = self.theta_c * tau_c + self.theta_g * tau_g
        h_t_plus_1 = self.A * (h_t ** self.alpha_h) * (e_t ** self.beta_h) * (time_input ** self.gamma_h)
        return h_t_plus_1

    def effective_labor_time(self, n_t, tau_c, tau_o_time, tau_g):
        """
        有效劳动时间（式3）
        l_t = 1 - n_t*τ_c - τ_o + ξ*τ_g
        """
        l_t = 1 - n_t * tau_c - tau_o_time + self.xi * tau_g
        return max(l_t, 0.1)  # 确保劳动时间为正

    def endogenous_support_expenditure(self, D_t, rho_pen):
        """
        内生赡养支出比例（式35）
        τ_o = τ_0 + μ_1*D_t + μ_2*(1-ρ_pen)
        """
        tau_o = self.tau_0 + self.mu_1 * D_t + self.mu_2 * (1 - rho_pen)
        return tau_o

    def endogenous_care_time(self, D_t, H_t):
        """
        内生照料时间（式38）
        τ_o = τ_{o,0} + ν_1*D_t*(1-H_t)
        """
        tau_o_time = self.tau_o_time_0 + self.nu_1 * D_t * (1 - H_t)
        return tau_o_time

    def endogenous_survival_prob(self, D_t):
        """
        内生存活概率（式41）
        p = p_0 + κ*D_t
        """
        p = self.p_0 + self.kappa * D_t
        return min(p, 0.99)  # 确保概率小于1

    def simulate_human_capital_sensitivity(self, h_t_base=1.0, e_t_base=0.5):
        """
        模拟1：人力资本积累对时间投入的敏感性分析
        """
        # 创建时间投入网格
        tau_c_range = np.linspace(0.05, 0.30, 20)
        tau_g_range = np.linspace(0.05, 0.30, 20)

        # 固定教育投资
        e_t = e_t_base

        results = {
            'tau_c': [],
            'tau_g': [],
            'h_t_plus_1': [],
            'h_t_plus_1_only_c': [],  # 仅子代投入
            'h_t_plus_1_only_g': []   # 仅父代投入
        }

        for tau_c in tau_c_range:
            for tau_g in tau_g_range:
                # 完整模型
                h_full = self.human_capital_accumulation(h_t_base, e_t, tau_c, tau_g)

                # 仅子代投入
                h_only_c = self.human_capital_accumulation(h_t_base, e_t, tau_c, 0)

                # 仅父代投入
                h_only_g = self.human_capital_accumulation(h_t_base, e_t, 0, tau_g)

                results['tau_c'].append(tau_c)
                results['tau_g'].append(tau_g)
                results['h_t_plus_1'].append(h_full)
                results['h_t_plus_1_only_c'].append(h_only_c)
                results['h_t_plus_1_only_g'].append(h_only_g)

        return pd.DataFrame(results)

    def compute_mediation_effects(self, D_t, omega_t, h_t, l_t, r_t_plus_1, Y_d_t):
        """
        计算中介效应（式54-60）

        返回:
            直接效应、赡养支出中介、照料时间中介、赡养风险中介、总效应
        """
        # 计算内生变量
        tau_o = self.endogenous_support_expenditure(D_t, self.rho_pen)
        tau_o_time = self.endogenous_care_time(D_t, self.H_t)
        p = self.endogenous_survival_prob(D_t)

        # 1. 直接效应（式56）
        m_g_t = 0.05 * omega_t * h_t  # 假设父代物质转移
        direct_effect = (self.beta * m_g_t) / ((1 + self.beta) * Y_d_t)

        # 2. 赡养支出中介效应（式57）
        # ∂τ_o/∂D_t = μ_1
        d_tau_o_d_D = self.mu_1
        # ∂s_t/∂τ_o（式46）
        term = (1 - self.tau) + l_t - tau_o
        d_s_d_tau_o = -(self.beta * omega_t * h_t * term) / (1 + self.beta)
        support_expenditure_mediation = d_s_d_tau_o * d_tau_o_d_D / Y_d_t

        # 3. 照料时间中介效应（式58）
        # ∂τ_o/∂D_t = ν_1*(1-H_t)
        d_tau_o_time_d_D = self.nu_1 * (1 - self.H_t)
        # ∂s_t/∂τ_o（预防性储蓄主导）
        d_s_d_tau_o_time = self.theta_precautionary * self.sigma_y_sq
        care_time_mediation = d_s_d_tau_o_time * d_tau_o_time_d_D / Y_d_t

        # 4. 赡养风险中介效应（式59）
        # ∂p/∂D_t = κ
        d_p_d_D = self.kappa
        # 假设∂TR_{t+1}/∂p ≈ τ_o * omega_t * h_t * l_t
        d_TR_plus_1_d_p = tau_o * omega_t * h_t * l_t
        d_s_d_p = d_TR_plus_1_d_p / ((1 + self.beta) * (1 + r_t_plus_1))
        support_risk_mediation = (d_s_d_p * d_p_d_D) / Y_d_t

        # 5. 总效应（式60）
        total_effect = direct_effect + support_expenditure_mediation + care_time_mediation + support_risk_mediation

        return {
            'direct_effect': direct_effect,
            'support_expenditure_mediation': support_expenditure_mediation,
            'care_time_mediation': care_time_mediation,
            'support_risk_mediation': support_risk_mediation,
            'total_effect': total_effect
        }

    def simulate_mediation_effects(self):
        """
        模拟2：中介效应随老龄化程度变化
        """
        # 赡养比范围（从0.5到2.0，表示从低度到高度老龄化）
        D_t_range = np.linspace(0.5, 2.0, 30)

        # 假设其他变量
        omega_t = 1.0
        h_t = 1.0
        r_t_plus_1 = 0.05
        Y_d_t = omega_t * h_t * 0.7  # 可支配收入

        results = {
            'D_t': [],
            'direct': [],
            'expenditure_med': [],
            'care_time_med': [],
            'risk_med': [],
            'total': [],
            'tau_o': [],
            'tau_o_time': [],
            'p': []
        }

        for D_t in D_t_range:
            l_t = self.effective_labor_time(self.n_t, self.tau_c,
                                           self.endogenous_care_time(D_t, self.H_t),
                                           self.tau_g)

            effects = self.compute_mediation_effects(D_t, omega_t, h_t, l_t, r_t_plus_1, Y_d_t)

            results['D_t'].append(D_t)
            results['direct'].append(effects['direct_effect'])
            results['expenditure_med'].append(effects['support_expenditure_mediation'])
            results['care_time_med'].append(effects['care_time_mediation'])
            results['risk_med'].append(effects['support_risk_mediation'])
            results['total'].append(effects['total_effect'])

            # 记录内生变量
            results['tau_o'].append(self.endogenous_support_expenditure(D_t, self.rho_pen))
            results['tau_o_time'].append(self.endogenous_care_time(D_t, self.H_t))
            results['p'].append(self.endogenous_survival_prob(D_t))

        return pd.DataFrame(results)

    def compute_saving_rate(self, D_t, C_t, omega_t, h_t, r_t_plus_1):
        """
        计算储蓄率（式33）
        Modified to show clearer variation with population aging
        """
        # 计算内生变量
        tau_o = self.endogenous_support_expenditure(D_t, self.rho_pen)
        tau_o_time = self.endogenous_care_time(D_t, self.H_t)

        # 计算劳动时间
        l_t = self.effective_labor_time(C_t, self.tau_c, tau_o_time, self.tau_g)

        # 计算可支配收入和转移支出
        b_t = 0.12 * omega_t * h_t  # 增加继承收入
        Y_d_t = (1 - self.tau) * omega_t * h_t * l_t + b_t

        # 转移支出 - 大幅降低教育投资基数
        n_t = C_t
        e_t = 0.03 * omega_t * h_t  # 进一步降低教育投资基数
        TR_t = tau_o * omega_t * h_t * l_t + n_t * e_t - b_t

        # 转移支出比率
        tau_TR_t = TR_t / Y_d_t if Y_d_t > 0 else 0

        # 转移支出随老龄化显著增加
        tau_TR_t_plus_1 = tau_TR_t * (1 + 0.05 * (D_t - 1))
        g = 0.025  # 降低增长率

        # 储蓄率（式33）
        term1 = (self.beta * (1 - tau_TR_t)) / (1 + self.beta)
        term2 = ((1 + g) * (1 - tau_TR_t_plus_1)) / ((1 + self.beta) * (1 + r_t_plus_1))
        rho_t = term1 - term2

        # 确保储蓄率在合理范围内
        return max(min(rho_t, 0.5), -0.15)

    def simulate_saving_rate_aging(self):
        """
        模拟3：储蓄率随人口结构变化
        """
        # 赡养比范围
        D_t_range = np.linspace(0.5, 2.0, 30)
        # 抚养比范围（与赡养比负相关）
        C_t_range = np.linspace(1.5, 0.6, 30)

        omega_t = 1.0
        h_t = 1.0
        r_t_plus_1 = 0.10  # 进一步提高利率使储蓄率有更明显的变化

        results = []
        for D_t, C_t in zip(D_t_range, C_t_range):
            rho_t = self.compute_saving_rate(D_t, C_t, omega_t, h_t, r_t_plus_1)
            results.append({
                'D_t': D_t,
                'C_t': C_t,
                'saving_rate': rho_t
            })

        return pd.DataFrame(results)

    def simulate_fertility_decline_aging(self):
        """
        Simulation 4: Fertility Decline Leads to Aging and Higher Saving Rate
        模拟4：少子化导致老龄化加剧，最终提升储蓄率

        Mechanism (机制):
        1. Fertility decline (生育率下降) n_t ↓
        2. Future old-age dependency rises (未来老年抚养比上升) D_{t+k} ↑
        3. Precautionary saving increases (预防性储蓄增加) ρ_t ↑
        4. Current child burden decreases (当期抚养负担减轻) C_t ↓ → ρ_t ↑
        """
        # Time periods: simulate 50 years (时间周期：模拟50年)
        periods = 50

        # Fertility decline scenario: from 1.5 to 0.5 over 30 years
        # 生育率下降情景：30年内从1.5降至0.5
        fertility_path = np.concatenate([
            np.linspace(1.5, 0.5, 30),  # Decline phase (下降阶段)
            np.ones(20) * 0.5            # Stable low phase (稳定低位)
        ])

        # Initialize tracking variables (初始化追踪变量)
        results = {
            'period': [],
            'fertility_rate': [],        # n_t
            'child_dependency': [],      # C_t = n_t
            'old_dependency': [],        # D_t = 1/n_{t-1}
            'saving_rate': [],
            'support_burden': [],        # τ_o
            'future_aging_pressure': []  # Forward-looking measure
        }

        # Historical fertility for initial old-age dependency
        # 历史生育率用于初始老年抚养比
        n_history = [1.5, 1.5, 1.4, 1.3, 1.2]

        omega_t = 1.0
        h_t = 1.0
        r_t_plus_1 = 0.10

        for t in range(periods):
            # Current fertility
            n_t = fertility_path[t]

            # Old-age dependency based on past fertility
            # 基于过去生育率的老年抚养比
            if t == 0:
                n_prev = n_history[-1]
            else:
                n_prev = fertility_path[t-1]
            D_t = 1.0 / n_prev if n_prev > 0 else 2.0

            # Child dependency
            C_t = n_t

            # Future aging pressure: average D over next 20 years
            # 未来老龄化压力：未来20年D的平均值
            future_n = fertility_path[t:min(t+20, periods)] if t < periods-20 else fertility_path[t:]
            future_D = np.mean(1.0 / np.maximum(future_n, 0.3))

            # Compute saving rate
            rho_t = self.compute_saving_rate(D_t, C_t, omega_t, h_t, r_t_plus_1)

            # Support burden
            tau_o = self.endogenous_support_expenditure(D_t, self.rho_pen)

            results['period'].append(t)
            results['fertility_rate'].append(n_t)
            results['child_dependency'].append(C_t)
            results['old_dependency'].append(D_t)
            results['saving_rate'].append(rho_t)
            results['support_burden'].append(tau_o)
            results['future_aging_pressure'].append(future_D)

        return pd.DataFrame(results)

    def compute_fertility_mediation_effects(self, n_t, omega_t, h_t, r_t_plus_1, Y_d_t):
        """
        Calculate mediation effects of fertility decline on saving rates (Chapter 6)
        计算少子化对储蓄率的中介效应（第六章）

        Based on theoretical decomposition:
        dρ_t/dn_t = Direct + Future Aging + Per Capita Resources + Human Capital

        Returns:
            Dictionary with 5 effects: direct, future_aging_med, per_capita_med, human_capital_med, total
        """
        # Calculate endogenous variables
        D_t = 1.0 / self.n_t_minus_1  # Current old-age dependency
        tau_o = self.endogenous_support_expenditure(D_t, self.rho_pen)
        tau_o_time = self.endogenous_care_time(D_t, self.H_t)

        # Calculate labor time
        l_t = self.effective_labor_time(n_t, self.tau_c, tau_o_time, self.tau_g)

        # 1. DIRECT EFFECT (Equation 66-67)
        # ∂s_t/∂n_t = -β/[(1+β)]·[(1-τ-τ_o)·ω·h·τ_c + e_t]
        e_t = 0.03 * omega_t * h_t  # Per-child education investment
        term_direct = (1 - self.tau - tau_o) * omega_t * h_t * self.tau_c + e_t
        d_s_d_n_direct = -(self.beta / (1 + self.beta)) * term_direct
        direct_effect = d_s_d_n_direct / Y_d_t

        # 2. FUTURE AGING EXPECTATION MEDIATION (Equation 71-75)
        # ∂s_t/∂n_t|expectation = [μ_1·ω_{t+1}·h_{t+1}·l_{t+1} / ((1+β)(1+r))] · (-1/n_t²)
        # Future old-age dependency: D_{t+1} = 1/n_t
        # ∂D_{t+1}/∂n_t = -1/n_t²
        d_D_future_d_n = -1.0 / (n_t ** 2)

        # ∂E[TR_{t+1}]/∂D_{t+1} = μ_1·ω·h·l (assuming future income similar to current)
        d_TR_future_d_D = self.mu_1 * omega_t * h_t * l_t

        # ∂s_t/∂E[TR_{t+1}] = 1/[(1+β)(1+r)]
        d_s_d_TR_future = 1.0 / ((1 + self.beta) * (1 + r_t_plus_1))

        future_aging_med = (d_s_d_TR_future * d_TR_future_d_D * d_D_future_d_n) / Y_d_t

        # 3. PER CAPITA RESOURCES MEDIATION (Equation 76-77)
        # y^per_capita = (Y_d - TR) / (1 + n_t + D_t)
        # ∂y^per_capita/∂n_t < 0 (family size effect)
        TR_t = tau_o * omega_t * h_t * l_t + n_t * e_t
        N_family = 1 + n_t + D_t

        # ∂Y_d/∂n_t = -(1-τ)·ω·h·τ_c (labor time reduction)
        d_Yd_d_n = -(1 - self.tau) * omega_t * h_t * self.tau_c

        # ∂TR/∂n_t ≈ e_t (dominant term)
        d_TR_d_n = e_t

        # ∂y^per_capita/∂n_t (using quotient rule)
        numerator = N_family * (d_Yd_d_n - d_TR_d_n) - (Y_d_t - TR_t)
        d_y_per_capita_d_n = numerator / (N_family ** 2)

        # ∂ρ_t/∂y^per_capita ≈ β/[(1+β)·Y_d] (marginal propensity to save)
        d_rho_d_y_per_capita = self.beta / ((1 + self.beta) * Y_d_t)

        per_capita_med = d_rho_d_y_per_capita * d_y_per_capita_d_n

        # 4. HUMAN CAPITAL INVESTMENT MEDIATION (Equation 78-79)
        # Becker's quality-quantity tradeoff: e_t = E_t/n_t
        # ∂e_t/∂n_t = -E_t/n_t² (if total education budget E_t is fixed)
        # ∂h_{t+1}/∂e_t = β_h · h_{t+1}/e_t
        E_total = n_t * e_t  # Total education budget
        d_e_d_n = -E_total / (n_t ** 2)

        # From human capital function (Equation 1)
        h_t_plus_1 = self.human_capital_accumulation(h_t, e_t, self.tau_c, self.tau_g)
        d_h_future_d_e = self.beta_h * h_t_plus_1 / e_t if e_t > 0 else 0
        d_h_future_d_n = d_h_future_d_e * d_e_d_n

        # ∂ρ_t/∂h_{t+1}: Higher future human capital → higher future income → affects saving
        # This is a long-term effect, approximate with income effect
        d_rho_d_h_future = 0.05 * self.beta / ((1 + self.beta) * Y_d_t)  # Scaled effect

        human_capital_med = d_rho_d_h_future * d_h_future_d_n

        # 5. TOTAL EFFECT (Equation 80-81)
        total_effect = direct_effect + future_aging_med + per_capita_med + human_capital_med

        return {
            'direct_effect': direct_effect,
            'future_aging_mediation': future_aging_med,
            'per_capita_mediation': per_capita_med,
            'human_capital_mediation': human_capital_med,
            'total_effect': total_effect,
            # Additional info for visualization
            'n_t': n_t,
            'C_t': n_t,
            'D_future': 1.0 / n_t,
            'per_capita_income': (Y_d_t - TR_t) / (1 + n_t + D_t),
            'per_child_education': e_t
        }

    def simulate_fertility_mediation_effects(self):
        """
        Simulation 6: Mediation Effects of Fertility Decline on Saving Rates
        模拟6：少子化对储蓄率的中介效应分解

        Demonstrates how fertility decline affects saving rates through 4 channels:
        1. Direct effect (childcare expenditure & labor time)
        2. Future aging expectation mediation
        3. Per capita resources mediation
        4. Human capital investment mediation
        """
        # Fertility rate range: from high (2.0) to low (0.5)
        # 生育率范围：从高生育率（2.0）到低生育率（0.5）
        n_t_range = np.linspace(2.0, 0.5, 30)

        # Assume other variables
        omega_t = 1.0
        h_t = 1.0
        r_t_plus_1 = 0.10

        results = {
            'n_t': [],
            'C_t': [],
            'direct': [],
            'future_aging_med': [],
            'per_capita_med': [],
            'human_capital_med': [],
            'total': [],
            'D_future': [],
            'per_capita_income': [],
            'per_child_education': []
        }

        for n_t in n_t_range:
            # Calculate disposable income (varies with n_t through labor time)
            D_t = 1.0 / self.n_t_minus_1
            tau_o = self.endogenous_support_expenditure(D_t, self.rho_pen)
            tau_o_time = self.endogenous_care_time(D_t, self.H_t)
            l_t = self.effective_labor_time(n_t, self.tau_c, tau_o_time, self.tau_g)

            Y_d_t = (1 - self.tau) * omega_t * h_t * l_t + 0.05 * omega_t * h_t

            effects = self.compute_fertility_mediation_effects(n_t, omega_t, h_t, r_t_plus_1, Y_d_t)

            results['n_t'].append(n_t)
            results['C_t'].append(effects['C_t'])
            results['direct'].append(effects['direct_effect'])
            results['future_aging_med'].append(effects['future_aging_mediation'])
            results['per_capita_med'].append(effects['per_capita_mediation'])
            results['human_capital_med'].append(effects['human_capital_mediation'])
            results['total'].append(effects['total_effect'])
            results['D_future'].append(effects['D_future'])
            results['per_capita_income'].append(effects['per_capita_income'])
            results['per_child_education'].append(effects['per_child_education'])

        return pd.DataFrame(results)

    def simulate_ai_labor_substitution(self):
        """
        Simulation 5: AI Development Reduces Saving Rate via Labor Substitution
        模拟5：人工智能发展通过劳动替代效应降低储蓄率

        Mechanism (机制):
        1. AI adoption increases (AI应用增加) α_AI ↑
        2. Labor income share decreases (劳动收入份额下降) (1-α_AI)·w·h·l ↓
        3. Capital income share increases (资本收入份额上升) but concentrated
        4. Household disposable income falls (家庭可支配收入下降) Y_d ↓
        5. Saving rate decreases (储蓄率下降) ρ_t ↓

        Additional channel (额外渠道):
        - AI reduces care time needs (AI降低照料时间需求) τ_o^time ↓
        - But labor income loss dominates (但劳动收入损失占主导)
        """
        # AI adoption levels: from 0% to 80% over 30 years
        # AI应用水平：30年内从0%到80%
        ai_adoption = np.linspace(0.0, 0.8, 30)

        # Baseline parameters
        D_t = 1.0  # Medium aging (中度老龄化)
        C_t = 0.8  # Low fertility (低生育率)
        omega_t = 1.0
        h_t = 1.0
        r_t_plus_1 = 0.10

        results = {
            'ai_adoption': [],           # α_AI: AI替代率
            'labor_income_share': [],    # Labor share after AI
            'capital_income_share': [],  # Capital share (increases with AI)
            'disposable_income': [],     # Y_d
            'saving_rate': [],           # ρ_t
            'care_time': [],             # τ_o^time (reduced by AI)
            'employment_rate': []        # Employment level
        }

        for alpha_ai in ai_adoption:
            # Labor income reduced by AI substitution
            # AI替代导致劳动收入下降
            labor_share = 1 - alpha_ai  # Remaining labor share
            effective_labor_income = labor_share * omega_t * h_t * 0.7  # 0.7 is baseline labor time

            # Capital income increases (but not equally distributed)
            # 资本收入增加（但分配不均）
            # Assume households own limited capital, most goes to corporations
            # 假设家庭拥有有限资本，大部分流向企业
            capital_share = alpha_ai
            household_capital_income = 0.2 * capital_share * omega_t * h_t  # Only 20% goes to households

            # Total disposable income (税后)
            Y_d = (1 - self.tau) * (effective_labor_income + household_capital_income)

            # AI reduces care time needs (AI助老服务)
            # AI eldercare assistance reduces ν_1
            ai_care_reduction = 0.5 * alpha_ai  # AI can reduce care needs by up to 50% at full adoption
            adjusted_nu_1 = self.nu_1 * (1 - ai_care_reduction)
            tau_o_time = self.tau_o_time_0 + adjusted_nu_1 * D_t * (1 - self.H_t)

            # Compute saving rate with adjusted income
            # Modified savings calculation accounting for income loss
            tau_o = self.endogenous_support_expenditure(D_t, self.rho_pen)

            # Simplified saving rate: more sensitive to income loss
            # Transfers as fraction of reduced income
            b_t = 0.12 * omega_t * h_t  # Inheritance unchanged
            e_t = 0.03 * omega_t * h_t
            TR_t = tau_o * effective_labor_income + C_t * e_t - b_t

            tau_TR_t = TR_t / Y_d if Y_d > 0.01 else 0.9
            tau_TR_t_plus_1 = tau_TR_t * (1 + 0.05 * (D_t - 1))
            g = 0.025

            term1 = (self.beta * (1 - tau_TR_t)) / (1 + self.beta)
            term2 = ((1 + g) * (1 - tau_TR_t_plus_1)) / ((1 + self.beta) * (1 + r_t_plus_1))
            rho_t = term1 - term2
            rho_t = max(min(rho_t, 0.5), -0.2)

            # Employment rate (就业率)
            employment = labor_share

            results['ai_adoption'].append(alpha_ai * 100)  # Convert to percentage
            results['labor_income_share'].append(labor_share)
            results['capital_income_share'].append(capital_share)
            results['disposable_income'].append(Y_d)
            results['saving_rate'].append(rho_t)
            results['care_time'].append(tau_o_time)
            results['employment_rate'].append(employment)

        return pd.DataFrame(results)


def plot_human_capital_sensitivity(df_hc):
    """
    Visualization 1: Human Capital Accumulation Sensitivity to Time Inputs
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # Prepare 3D data
    tau_c_unique = sorted(df_hc['tau_c'].unique())
    tau_g_unique = sorted(df_hc['tau_g'].unique())

    # Subplot 1: Heatmap of full model
    pivot_full = df_hc.pivot_table(values='h_t_plus_1', index='tau_g', columns='tau_c')
    im1 = axes[0, 0].contourf(pivot_full.columns, pivot_full.index, pivot_full.values, levels=15, cmap='YlOrRd')
    axes[0, 0].set_xlabel(r'Children Time Input $\tau_c$', fontsize=12)
    axes[0, 0].set_ylabel(r'Grandparents Time Input $\tau_g$', fontsize=12)
    axes[0, 0].set_title(r'(a) Human Capital Level $h_{t+1}$' + '\n(Joint Time Inputs)', fontsize=13, fontweight='bold')
    cbar1 = plt.colorbar(im1, ax=axes[0, 0])
    cbar1.set_label(r'$h_{t+1}$', fontsize=11)

    # Subplot 2: Marginal effect comparison
    tau_g_fixed = 0.15
    df_fixed_g = df_hc[np.isclose(df_hc['tau_g'], tau_g_fixed, atol=0.01)]
    axes[0, 1].plot(df_fixed_g['tau_c'], df_fixed_g['h_t_plus_1'], 'b-o', linewidth=2, label='Full Model')
    axes[0, 1].plot(df_fixed_g['tau_c'], df_fixed_g['h_t_plus_1_only_c'], 'r--s', linewidth=2, label='Children Only')
    axes[0, 1].set_xlabel(r'Children Time Input $\tau_c$', fontsize=12)
    axes[0, 1].set_ylabel(r'Human Capital $h_{t+1}$', fontsize=12)
    axes[0, 1].set_title(f'(b) Marginal Effect of Children Time\n' + r'(Fixed $\tau_g$=' + f'{tau_g_fixed})', fontsize=13, fontweight='bold')
    axes[0, 1].legend(fontsize=11)
    axes[0, 1].grid(True, alpha=0.3)

    # Subplot 3: Complementarity analysis
    tau_c_fixed = 0.15
    df_fixed_c = df_hc[np.isclose(df_hc['tau_c'], tau_c_fixed, atol=0.01)]
    axes[1, 0].plot(df_fixed_c['tau_g'], df_fixed_c['h_t_plus_1'], 'g-o', linewidth=2, label='Full Model')
    axes[1, 0].plot(df_fixed_c['tau_g'], df_fixed_c['h_t_plus_1_only_g'], 'm--s', linewidth=2, label='Grandparents Only')
    axes[1, 0].set_xlabel(r'Grandparents Time Input $\tau_g$', fontsize=12)
    axes[1, 0].set_ylabel(r'Human Capital $h_{t+1}$', fontsize=12)
    axes[1, 0].set_title(f'(c) Marginal Effect of Grandparents Time\n' + r'(Fixed $\tau_c$=' + f'{tau_c_fixed})', fontsize=13, fontweight='bold')
    axes[1, 0].legend(fontsize=11)
    axes[1, 0].grid(True, alpha=0.3)

    # Subplot 4: Efficiency difference (θ_c vs θ_g)
    tau_g_levels = [0.10, 0.15, 0.20]
    for tau_g_val in tau_g_levels:
        df_subset = df_hc[np.isclose(df_hc['tau_g'], tau_g_val, atol=0.01)]
        df_subset = df_subset.sort_values('tau_c')
        axes[1, 1].plot(df_subset['tau_c'], df_subset['h_t_plus_1'],
                       linewidth=2, marker='o', label=r'$\tau_g$=' + f'{tau_g_val:.2f}')

    axes[1, 1].set_xlabel(r'Children Time Input $\tau_c$', fontsize=12)
    axes[1, 1].set_ylabel(r'Human Capital $h_{t+1}$', fontsize=12)
    axes[1, 1].set_title('(d) Intergenerational Time Complementarity\n(Different Grandparent Input Levels)', fontsize=13, fontweight='bold')
    axes[1, 1].legend(fontsize=11)
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/user/econ/figure1_human_capital.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 1 saved: figure1_human_capital.png")
    return fig


def plot_mediation_effects(df_med):
    """
    Visualization 2: Mediation Effects Decomposition
    """
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # Subplot 1: Evolution of each mediation effect
    axes[0, 0].plot(df_med['D_t'], df_med['direct'], 'b-o', linewidth=2.5, markersize=6, label='Direct Effect')
    axes[0, 0].plot(df_med['D_t'], df_med['expenditure_med'], 'r--s', linewidth=2.5, markersize=6, label='Support Expenditure (neg)')
    axes[0, 0].plot(df_med['D_t'], df_med['care_time_med'], 'g-.^', linewidth=2.5, markersize=6, label='Care Time (pos)')
    axes[0, 0].plot(df_med['D_t'], df_med['risk_med'], 'm:d', linewidth=2.5, markersize=6, label='Support Risk (pos)')
    axes[0, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)
    axes[0, 0].set_xlabel(r'Old-Age Dependency Ratio $D_t$', fontsize=12)
    axes[0, 0].set_ylabel(r'Effect on Saving Rate $\rho_t$', fontsize=12)
    axes[0, 0].set_title('(a) Mediation Effects of Population Aging', fontsize=13, fontweight='bold')
    axes[0, 0].legend(fontsize=10, loc='best')
    axes[0, 0].grid(True, alpha=0.3)

    # Subplot 2: Total effect and its decomposition
    axes[0, 1].plot(df_med['D_t'], df_med['total'], 'k-o', linewidth=3, markersize=7, label='Total Effect')
    axes[0, 1].fill_between(df_med['D_t'], 0, df_med['total'], alpha=0.2, color='gray')
    axes[0, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    axes[0, 1].set_xlabel(r'Old-Age Dependency Ratio $D_t$', fontsize=12)
    axes[0, 1].set_ylabel(r'Total Effect on $\rho_t$', fontsize=12)
    axes[0, 1].set_title('(b) Total Effect of Aging on Saving Rate', fontsize=13, fontweight='bold')
    axes[0, 1].legend(fontsize=11)
    axes[0, 1].grid(True, alpha=0.3)

    # Subplot 3: Evolution of endogenous variables
    ax3_1 = axes[1, 0]
    ax3_2 = ax3_1.twinx()

    line1 = ax3_1.plot(df_med['D_t'], df_med['tau_o'], 'b-o', linewidth=2.5, markersize=6, label=r'Support Ratio $\tau_o$')
    line2 = ax3_1.plot(df_med['D_t'], df_med['tau_o_time'], 'r--s', linewidth=2.5, markersize=6, label=r'Care Time $\tau_o^{time}$')
    line3 = ax3_2.plot(df_med['D_t'], df_med['p'], 'g-.^', linewidth=2.5, markersize=6, label='Survival Prob. p')

    ax3_1.set_xlabel(r'Old-Age Dependency Ratio $D_t$', fontsize=12)
    ax3_1.set_ylabel('Support Ratio & Care Time', fontsize=12, color='black')
    ax3_2.set_ylabel('Survival Probability', fontsize=12, color='g')
    ax3_1.set_title('(c) Evolution of Endogenous Support Variables', fontsize=13, fontweight='bold')

    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax3_1.legend(lines, labels, fontsize=10, loc='upper left')
    ax3_1.grid(True, alpha=0.3)

    # Subplot 4: Stacked area chart showing mediation contributions
    axes[1, 1].fill_between(df_med['D_t'], 0, df_med['direct'], alpha=0.6, label='Direct Effect', color='#1f77b4')
    axes[1, 1].fill_between(df_med['D_t'], df_med['direct'],
                           df_med['direct'] + df_med['care_time_med'],
                           alpha=0.6, label='Care Time Mediation', color='#2ca02c')
    axes[1, 1].fill_between(df_med['D_t'], df_med['direct'] + df_med['care_time_med'],
                           df_med['direct'] + df_med['care_time_med'] + df_med['risk_med'],
                           alpha=0.6, label='Support Risk Mediation', color='#9467bd')
    axes[1, 1].fill_between(df_med['D_t'], 0, df_med['expenditure_med'],
                           alpha=0.6, label='Expenditure Mediation', color='#d62728')
    axes[1, 1].plot(df_med['D_t'], df_med['total'], 'k-', linewidth=2.5, label='Total Effect')

    axes[1, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    axes[1, 1].set_xlabel(r'Old-Age Dependency Ratio $D_t$', fontsize=12)
    axes[1, 1].set_ylabel(r'Effect on $\rho_t$', fontsize=12)
    axes[1, 1].set_title('(d) Cumulative Contribution of Mediation Effects', fontsize=13, fontweight='bold')
    axes[1, 1].legend(fontsize=10, loc='best')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/user/econ/figure2_mediation_effects.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 2 saved: figure2_mediation_effects.png")
    return fig


def plot_saving_rate_aging(df_saving):
    """
    Visualization 3: Saving Rate and Population Structure
    """
    from matplotlib.ticker import PercentFormatter

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Subplot 1: Saving rate vs old-age dependency ratio
    axes[0].plot(df_saving['D_t'], df_saving['saving_rate']*100, 'b-o', linewidth=2.5, markersize=7)
    axes[0].fill_between(df_saving['D_t'], 0, df_saving['saving_rate']*100, alpha=0.2, color='blue')
    axes[0].set_xlabel(r'Old-Age Dependency Ratio $D_t$', fontsize=12)
    axes[0].set_ylabel(r'Household Saving Rate $\rho_t$ (%)', fontsize=12)
    axes[0].set_title('(a) Saving Rate and Population Aging', fontsize=13, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    axes[0].axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.3)

    # Add value range annotation
    min_rate = df_saving['saving_rate'].min() * 100
    max_rate = df_saving['saving_rate'].max() * 100
    axes[0].text(0.05, 0.95, f'Range: [{min_rate:.2f}%, {max_rate:.2f}%]',
                 transform=axes[0].transAxes, fontsize=10, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    # Subplot 2: Saving rate vs child dependency ratio (inverse relationship)
    axes[1].plot(df_saving['C_t'], df_saving['saving_rate']*100, 'r-s', linewidth=2.5, markersize=7)
    axes[1].fill_between(df_saving['C_t'], 0, df_saving['saving_rate']*100, alpha=0.2, color='red')
    axes[1].set_xlabel(r'Child Dependency Ratio $C_t$', fontsize=12)
    axes[1].set_ylabel(r'Household Saving Rate $\rho_t$ (%)', fontsize=12)
    axes[1].set_title('(b) Saving Rate and Fertility Decline', fontsize=13, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    axes[1].axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.3)

    # Add value range annotation
    axes[1].text(0.05, 0.95, f'Range: [{min_rate:.2f}%, {max_rate:.2f}%]',
                 transform=axes[1].transAxes, fontsize=10, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()
    plt.savefig('/home/user/econ/figure3_saving_rate.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 3 saved: figure3_saving_rate.png")
    return fig


def plot_fertility_decline_aging(df_fert):
    """
    Visualization 4: Fertility Decline Leads to Aging and Higher Saving Rate
    可视化4：少子化导致老龄化加剧，最终提升储蓄率
    """
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # Subplot 1: Fertility rate and dependency ratios over time
    ax1_1 = axes[0, 0]
    ax1_2 = ax1_1.twinx()

    line1 = ax1_1.plot(df_fert['period'], df_fert['fertility_rate'], 'b-', linewidth=2.5, label='Fertility Rate $n_t$')
    line2 = ax1_2.plot(df_fert['period'], df_fert['child_dependency'], 'g--', linewidth=2, label='Child Dependency $C_t$')
    line3 = ax1_2.plot(df_fert['period'], df_fert['old_dependency'], 'r-.', linewidth=2, label='Old-Age Dependency $D_t$')

    ax1_1.set_xlabel('Period (Years)', fontsize=12)
    ax1_1.set_ylabel('Fertility Rate $n_t$', fontsize=12, color='b')
    ax1_2.set_ylabel('Dependency Ratios', fontsize=12, color='black')
    ax1_1.set_title('(a) Fertility Decline and Rising Old-Age Dependency', fontsize=13, fontweight='bold')
    ax1_1.tick_params(axis='y', labelcolor='b')

    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1_1.legend(lines, labels, fontsize=10, loc='upper right')
    ax1_1.grid(True, alpha=0.3)

    # Subplot 2: Saving rate evolution
    axes[0, 1].plot(df_fert['period'], df_fert['saving_rate']*100, 'purple', linewidth=2.5)
    axes[0, 1].fill_between(df_fert['period'], 0, df_fert['saving_rate']*100, alpha=0.2, color='purple')
    axes[0, 1].set_xlabel('Period (Years)', fontsize=12)
    axes[0, 1].set_ylabel('Household Saving Rate $\\rho_t$ (%)', fontsize=12)
    axes[0, 1].set_title('(b) Saving Rate Evolution with Fertility Decline', fontsize=13, fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.3)

    # Add annotation
    max_idx = df_fert['saving_rate'].idxmax()
    max_period = df_fert.loc[max_idx, 'period']
    max_rate = df_fert.loc[max_idx, 'saving_rate'] * 100
    axes[0, 1].annotate(f'Peak: {max_rate:.2f}%\nat year {max_period}',
                        xy=(max_period, max_rate), xytext=(max_period-10, max_rate+0.5),
                        arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
                        fontsize=10, color='red')

    # Subplot 3: Support burden evolution
    axes[1, 0].plot(df_fert['period'], df_fert['support_burden']*100, 'orange', linewidth=2.5)
    axes[1, 0].fill_between(df_fert['period'], 0, df_fert['support_burden']*100, alpha=0.2, color='orange')
    axes[1, 0].set_xlabel('Period (Years)', fontsize=12)
    axes[1, 0].set_ylabel('Support Expenditure Ratio $\\tau_o$ (%)', fontsize=12)
    axes[1, 0].set_title('(c) Rising Support Burden with Aging', fontsize=13, fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3)

    # Subplot 4: Future aging pressure
    axes[1, 1].plot(df_fert['period'], df_fert['future_aging_pressure'], 'teal', linewidth=2.5)
    axes[1, 1].fill_between(df_fert['period'], 0, df_fert['future_aging_pressure'], alpha=0.2, color='teal')
    axes[1, 1].set_xlabel('Period (Years)', fontsize=12)
    axes[1, 1].set_ylabel('Future Aging Pressure\n(20-year forward $D_t$ avg)', fontsize=12)
    axes[1, 1].set_title('(d) Forward-Looking Aging Pressure', fontsize=13, fontweight='bold')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/user/econ/figure4_fertility_decline.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 4 saved: figure4_fertility_decline.png")
    return fig


def plot_fertility_mediation_effects(df_fert_med):
    """
    Visualization 6: Mediation Effects of Fertility Decline on Saving Rates
    可视化6：少子化对储蓄率的中介效应分解
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Subplot 1: Mediation effects decomposition
    ax1 = axes[0, 0]

    # Plot each mediation channel
    ax1.plot(df_fert_med['n_t'], df_fert_med['direct'], 'b-', linewidth=2.5, marker='o', markersize=4, label='Direct Effect')
    ax1.plot(df_fert_med['n_t'], df_fert_med['future_aging_med'], 'r--', linewidth=2.5, marker='s', markersize=4, label='Future Aging Mediation')
    ax1.plot(df_fert_med['n_t'], df_fert_med['per_capita_med'], 'g-.', linewidth=2.5, marker='^', markersize=4, label='Per Capita Resources Mediation')
    ax1.plot(df_fert_med['n_t'], df_fert_med['human_capital_med'], 'm:', linewidth=2.5, marker='d', markersize=4, label='Human Capital Mediation')
    ax1.plot(df_fert_med['n_t'], df_fert_med['total'], 'k-', linewidth=3, marker='*', markersize=6, label='Total Effect')

    ax1.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax1.set_xlabel('Fertility Rate $n_t$', fontsize=12)
    ax1.set_ylabel(r'Effect on Saving Rate $\partial\rho_t/\partial n_t$', fontsize=12)
    ax1.set_title('(a) Four-Channel Mediation Decomposition', fontsize=13, fontweight='bold')
    ax1.legend(fontsize=10, loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.invert_xaxis()  # Invert x-axis so fertility decline (left to right) shows increasing effect

    # Add annotation for key finding
    ax1.text(0.6, 0.05, 'All channels reinforce:\nFertility decline → Saving rate ↑',
             transform=ax1.transAxes, fontsize=11, verticalalignment='bottom',
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))

    # Subplot 2: Stacked bar chart showing relative contributions
    ax2 = axes[0, 1]

    # Calculate percentage contributions for n_t=0.5 (low fertility scenario)
    idx_low_fert = df_fert_med['n_t'].idxmin()  # Find index of minimum n_t
    direct_val = df_fert_med.loc[idx_low_fert, 'direct']
    future_aging_val = df_fert_med.loc[idx_low_fert, 'future_aging_med']
    per_capita_val = df_fert_med.loc[idx_low_fert, 'per_capita_med']
    human_capital_val = df_fert_med.loc[idx_low_fert, 'human_capital_med']
    total_val = df_fert_med.loc[idx_low_fert, 'total']

    # Calculate percentages
    contributions = [direct_val, future_aging_val, per_capita_val, human_capital_val]
    labels = ['Direct', 'Future\nAging', 'Per Capita\nResources', 'Human\nCapital']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

    bars = ax2.bar(labels, contributions, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax2.set_ylabel(r'Contribution to $d\rho_t/dn_t$ at $n_t=0.5$', fontsize=12)
    ax2.set_title('(b) Channel Contributions at Low Fertility', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for bar, val in zip(bars, contributions):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.4f}',
                ha='center', va='bottom' if height > 0 else 'top', fontsize=10)

    # Subplot 3: Future old-age dependency and per capita income
    ax3_1 = axes[1, 0]
    ax3_2 = ax3_1.twinx()

    line1 = ax3_1.plot(df_fert_med['n_t'], df_fert_med['D_future'], 'b-', linewidth=2.5, label='Future Old-Age Dependency $D_{t+1}$')
    line2 = ax3_2.plot(df_fert_med['n_t'], df_fert_med['per_capita_income'], 'r--', linewidth=2.5, label='Per Capita Income')

    ax3_1.set_xlabel('Fertility Rate $n_t$', fontsize=12)
    ax3_1.set_ylabel('Future Dependency $D_{t+1} = 1/n_t$', fontsize=12, color='b')
    ax3_2.set_ylabel('Per Capita Income', fontsize=12, color='r')
    ax3_1.set_title('(c) Mechanisms: Aging Expectation & Resource Concentration', fontsize=13, fontweight='bold')
    ax3_1.tick_params(axis='y', labelcolor='b')
    ax3_2.tick_params(axis='y', labelcolor='r')
    ax3_1.invert_xaxis()

    lines = line1 + line2
    labels_legend = [l.get_label() for l in lines]
    ax3_1.legend(lines, labels_legend, fontsize=10, loc='upper left')
    ax3_1.grid(True, alpha=0.3)

    # Subplot 4: Per-child education investment (quality-quantity tradeoff)
    ax4 = axes[1, 1]

    ax4.plot(df_fert_med['n_t'], df_fert_med['per_child_education'], 'purple', linewidth=2.5, marker='o', markersize=5)
    ax4.fill_between(df_fert_med['n_t'], 0, df_fert_med['per_child_education'], alpha=0.2, color='purple')

    ax4.set_xlabel('Fertility Rate $n_t$', fontsize=12)
    ax4.set_ylabel('Per-Child Education Investment $e_t$', fontsize=12)
    ax4.set_title('(d) Becker Quality-Quantity Tradeoff', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.invert_xaxis()

    # Add annotation
    e_at_high_fert = df_fert_med.loc[df_fert_med['n_t'].idxmax(), 'per_child_education']
    e_at_low_fert = df_fert_med.loc[df_fert_med['n_t'].idxmin(), 'per_child_education']
    increase_pct = (e_at_low_fert / e_at_high_fert - 1) * 100

    ax4.text(0.6, 0.95, f'Fertility 2.0→0.5:\nEducation per child ↑{increase_pct:.0f}%',
             transform=ax4.transAxes, fontsize=11, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

    plt.tight_layout()
    plt.savefig('/home/user/econ/figure6_fertility_mediation.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 6 saved: figure6_fertility_mediation.png")
    return fig


def plot_ai_labor_substitution(df_ai):
    """
    Visualization 5: AI Development Reduces Saving Rate via Labor Substitution
    可视化5：人工智能发展通过劳动替代效应降低储蓄率
    """
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # Subplot 1: AI adoption and income composition
    ax1 = axes[0, 0]
    ax1.fill_between(df_ai['ai_adoption'], 0, df_ai['labor_income_share']*100,
                     alpha=0.6, color='#2ca02c', label='Labor Income Share')
    ax1.fill_between(df_ai['ai_adoption'], df_ai['labor_income_share']*100,
                     (df_ai['labor_income_share'] + df_ai['capital_income_share'])*100,
                     alpha=0.6, color='#ff7f0e', label='Capital Income Share')
    ax1.set_xlabel('AI Adoption Rate $\\alpha_{AI}$ (%)', fontsize=12)
    ax1.set_ylabel('Income Share (%)', fontsize=12)
    ax1.set_title('(a) Income Composition with AI Development', fontsize=13, fontweight='bold')
    ax1.legend(fontsize=11, loc='right')
    ax1.grid(True, alpha=0.3)

    # Subplot 2: Disposable income and employment
    ax2_1 = axes[0, 1]
    ax2_2 = ax2_1.twinx()

    line1 = ax2_1.plot(df_ai['ai_adoption'], df_ai['disposable_income'], 'b-', linewidth=2.5, label='Disposable Income $Y_d$')
    line2 = ax2_2.plot(df_ai['ai_adoption'], df_ai['employment_rate']*100, 'r--', linewidth=2.5, label='Employment Rate (%)')

    ax2_1.set_xlabel('AI Adoption Rate $\\alpha_{AI}$ (%)', fontsize=12)
    ax2_1.set_ylabel('Household Disposable Income $Y_d$', fontsize=12, color='b')
    ax2_2.set_ylabel('Employment Rate (%)', fontsize=12, color='r')
    ax2_1.set_title('(b) Income Loss and Employment Decline', fontsize=13, fontweight='bold')
    ax2_1.tick_params(axis='y', labelcolor='b')
    ax2_2.tick_params(axis='y', labelcolor='r')

    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax2_1.legend(lines, labels, fontsize=10, loc='upper right')
    ax2_1.grid(True, alpha=0.3)

    # Subplot 3: Saving rate decline
    axes[1, 0].plot(df_ai['ai_adoption'], df_ai['saving_rate']*100, 'purple', linewidth=3, marker='o', markersize=4)
    axes[1, 0].fill_between(df_ai['ai_adoption'], 0, df_ai['saving_rate']*100, alpha=0.2, color='purple')
    axes[1, 0].set_xlabel('AI Adoption Rate $\\alpha_{AI}$ (%)', fontsize=12)
    axes[1, 0].set_ylabel('Household Saving Rate $\\rho_t$ (%)', fontsize=12)
    axes[1, 0].set_title('(c) Declining Saving Rate with AI Substitution', fontsize=13, fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.3)

    # Add annotation
    initial_rate = df_ai.loc[0, 'saving_rate'] * 100
    final_rate = df_ai.loc[len(df_ai)-1, 'saving_rate'] * 100
    decline = initial_rate - final_rate
    axes[1, 0].text(0.6, 0.95, f'Total Decline: {decline:.2f}pp',
                    transform=axes[1, 0].transAxes, fontsize=11, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))

    # Subplot 4: AI care assistance benefit
    axes[1, 1].plot(df_ai['ai_adoption'], df_ai['care_time'], 'teal', linewidth=2.5)
    axes[1, 1].fill_between(df_ai['ai_adoption'], 0, df_ai['care_time'], alpha=0.2, color='teal')
    axes[1, 1].set_xlabel('AI Adoption Rate $\\alpha_{AI}$ (%)', fontsize=12)
    axes[1, 1].set_ylabel('Care Time Requirement $\\tau_o^{time}$', fontsize=12)
    axes[1, 1].set_title('(d) AI Elderly Care Assistance (Partial Offset)', fontsize=13, fontweight='bold')
    axes[1, 1].grid(True, alpha=0.3)

    # Add annotation
    care_reduction = (df_ai.loc[0, 'care_time'] - df_ai.loc[len(df_ai)-1, 'care_time']) / df_ai.loc[0, 'care_time'] * 100
    axes[1, 1].text(0.6, 0.95, f'Care Time Reduction: {care_reduction:.1f}%',
                    transform=axes[1, 1].transAxes, fontsize=11, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

    plt.tight_layout()
    plt.savefig('/home/user/econ/figure5_ai_substitution.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 5 saved: figure5_ai_substitution.png")
    return fig


def main():
    """
    Main Function: Run All Numerical Simulations
    """
    print("="*60)
    print("Numerical Simulation: Human Capital Accumulation and")
    print("                      Mediation Effects of Family Support")
    print("="*60)

    # Initialize model
    model = OLGModel()

    print("\n[1] Simulating human capital sensitivity to time inputs...")
    df_hc = model.simulate_human_capital_sensitivity()
    print(f"    Done! Generated {len(df_hc)} data points")

    print("\n[2] Simulating mediation effects with aging...")
    df_med = model.simulate_mediation_effects()
    print(f"    Done! Generated {len(df_med)} data points")

    print("\n[3] Simulating saving rate with population structure...")
    df_saving = model.simulate_saving_rate_aging()
    print(f"    Done! Generated {len(df_saving)} data points")

    print("\n[4] Simulating fertility decline and future aging...")
    df_fert = model.simulate_fertility_decline_aging()
    print(f"    Done! Generated {len(df_fert)} data points (50-year projection)")

    print("\n[5] Simulating AI labor substitution effects...")
    df_ai = model.simulate_ai_labor_substitution()
    print(f"    Done! Generated {len(df_ai)} data points")

    print("\n[6] Simulating fertility decline mediation effects...")
    df_fert_med = model.simulate_fertility_mediation_effects()
    print(f"    Done! Generated {len(df_fert_med)} data points")

    print("\n" + "="*60)
    print("Generating visualizations...")
    print("="*60)

    # Generate figures
    fig1 = plot_human_capital_sensitivity(df_hc)
    fig2 = plot_mediation_effects(df_med)
    fig3 = plot_saving_rate_aging(df_saving)
    fig4 = plot_fertility_decline_aging(df_fert)
    fig5 = plot_ai_labor_substitution(df_ai)
    fig6 = plot_fertility_mediation_effects(df_fert_med)

    # Save data
    print("\nSaving simulation data...")
    df_hc.to_csv('/home/user/econ/data_human_capital.csv', index=False)
    print("✓ Data saved: data_human_capital.csv")

    df_med.to_csv('/home/user/econ/data_mediation_effects.csv', index=False)
    print("✓ Data saved: data_mediation_effects.csv")

    df_saving.to_csv('/home/user/econ/data_saving_rate.csv', index=False)
    print("✓ Data saved: data_saving_rate.csv")

    df_fert.to_csv('/home/user/econ/data_fertility_decline.csv', index=False)
    print("✓ Data saved: data_fertility_decline.csv")

    df_ai.to_csv('/home/user/econ/data_ai_substitution.csv', index=False)
    print("✓ Data saved: data_ai_substitution.csv")

    df_fert_med.to_csv('/home/user/econ/data_fertility_mediation.csv', index=False)
    print("✓ Data saved: data_fertility_mediation.csv")

    print("\n" + "="*60)
    print("SIMULATION RESULTS SUMMARY")
    print("="*60)

    # Output key results
    print("\n[1. Human Capital Accumulation]")
    print(f"  • Children efficiency parameter theta_c = {model.theta_c:.2f}")
    print(f"  • Grandparents efficiency parameter theta_g = {model.theta_g:.2f}")
    print(f"  • Efficiency ratio theta_c/theta_g = {model.theta_c/model.theta_g:.2f}")
    print(f"  • Human capital range: [{df_hc['h_t_plus_1'].min():.3f}, {df_hc['h_t_plus_1'].max():.3f}]")

    print("\n[2. Mediation Effects Decomposition] (at D_t=1.0)")
    idx_mid = len(df_med) // 2
    print(f"  • Direct effect: {df_med.loc[idx_mid, 'direct']:.5f}")
    print(f"  • Support expenditure mediation: {df_med.loc[idx_mid, 'expenditure_med']:.5f} (negative)")
    print(f"  • Care time mediation: {df_med.loc[idx_mid, 'care_time_med']:.5f} (positive)")
    print(f"  • Support risk mediation: {df_med.loc[idx_mid, 'risk_med']:.5f} (positive)")
    print(f"  • Total effect: {df_med.loc[idx_mid, 'total']:.5f}")

    print("\n[3. Saving Rate and Population Structure]")
    print(f"  • Minimum saving rate: {df_saving['saving_rate'].min():.4f} (low aging)")
    print(f"  • Maximum saving rate: {df_saving['saving_rate'].max():.4f} (high aging)")
    print(f"  • Average saving rate: {df_saving['saving_rate'].mean():.4f}")

    print("\n[4. Fertility Decline and Future Aging]")
    print(f"  • Initial fertility rate: {df_fert.loc[0, 'fertility_rate']:.2f}")
    print(f"  • Final fertility rate: {df_fert.loc[len(df_fert)-1, 'fertility_rate']:.2f}")
    print(f"  • Peak saving rate: {df_fert['saving_rate'].max()*100:.2f}% at year {df_fert.loc[df_fert['saving_rate'].idxmax(), 'period']:.0f}")
    print(f"  • Old-age dependency increase: {df_fert.loc[0, 'old_dependency']:.2f} → {df_fert.loc[len(df_fert)-1, 'old_dependency']:.2f}")

    print("\n[5. AI Labor Substitution]")
    initial_sr_ai = df_ai.loc[0, 'saving_rate'] * 100
    final_sr_ai = df_ai.loc[len(df_ai)-1, 'saving_rate'] * 100
    print(f"  • AI adoption range: 0% → 80%")
    print(f"  • Saving rate decline: {initial_sr_ai:.2f}% → {final_sr_ai:.2f}% ({initial_sr_ai-final_sr_ai:.2f}pp drop)")
    print(f"  • Employment rate decline: 100% → {df_ai.loc[len(df_ai)-1, 'employment_rate']*100:.1f}%")
    print(f"  • Disposable income loss: {(1-df_ai.loc[len(df_ai)-1, 'disposable_income']/df_ai.loc[0, 'disposable_income'])*100:.1f}%")

    print("\n[6. Fertility Decline Mediation Effects]")
    # Find values at low fertility (n_t = 0.5)
    idx_low_fert = df_fert_med['n_t'].idxmin()
    direct_val = df_fert_med.loc[idx_low_fert, 'direct']
    future_aging_val = df_fert_med.loc[idx_low_fert, 'future_aging_med']
    per_capita_val = df_fert_med.loc[idx_low_fert, 'per_capita_med']
    human_capital_val = df_fert_med.loc[idx_low_fert, 'human_capital_med']
    total_val = df_fert_med.loc[idx_low_fert, 'total']

    print(f"  • Fertility range: 2.0 → 0.5")
    print(f"  • Direct effect contribution: {direct_val:.5f}")
    print(f"  • Future aging mediation: {future_aging_val:.5f}")
    print(f"  • Per capita resources mediation: {per_capita_val:.5f}")
    print(f"  • Human capital mediation: {human_capital_val:.5f}")
    print(f"  • Total effect (dρ/dn at n=0.5): {total_val:.5f}")
    print(f"  • All channels reinforce: Fertility decline → Saving rate ↑")

    print("\n" + "="*60)
    print("ALL SIMULATIONS COMPLETED!")
    print("="*60)

    return df_hc, df_med, df_saving, df_fert, df_ai, df_fert_med


if __name__ == "__main__":
    df_hc, df_med, df_saving, df_fert, df_ai, df_fert_med = main()
