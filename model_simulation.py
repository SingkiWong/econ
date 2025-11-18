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

# 设置中文字体支持
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

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
        """
        # 计算内生变量
        tau_o = self.endogenous_support_expenditure(D_t, self.rho_pen)
        tau_o_time = self.endogenous_care_time(D_t, self.H_t)

        # 计算劳动时间
        l_t = self.effective_labor_time(C_t, self.tau_c, tau_o_time, self.tau_g)

        # 计算可支配收入和转移支出
        b_t = 0.05 * omega_t * h_t  # 简化的继承收入
        Y_d_t = (1 - self.tau) * omega_t * h_t * l_t + b_t

        # 转移支出
        n_t = C_t
        e_t = 0.1 * omega_t * h_t  # 简化的教育投资
        TR_t = tau_o * omega_t * h_t * l_t + n_t * e_t - b_t

        # 转移支出比率
        tau_TR_t = TR_t / Y_d_t

        # 假设稳态下转移支出比率不变
        tau_TR_t_plus_1 = tau_TR_t
        g = 0.02  # 假设2%的增长率

        # 储蓄率（式33）
        term1 = (self.beta * (1 - tau_TR_t)) / (1 + self.beta)
        term2 = ((1 + g) * (1 - tau_TR_t_plus_1)) / ((1 + self.beta) * (1 + r_t_plus_1))
        rho_t = term1 - term2

        return max(rho_t, 0)  # 确保储蓄率非负

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
        r_t_plus_1 = 0.05

        results = []
        for D_t, C_t in zip(D_t_range, C_t_range):
            rho_t = self.compute_saving_rate(D_t, C_t, omega_t, h_t, r_t_plus_1)
            results.append({
                'D_t': D_t,
                'C_t': C_t,
                'saving_rate': rho_t
            })

        return pd.DataFrame(results)


def plot_human_capital_sensitivity(df_hc):
    """
    可视化1：人力资本积累的时间投入敏感性
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # 准备3D数据
    tau_c_unique = sorted(df_hc['tau_c'].unique())
    tau_g_unique = sorted(df_hc['tau_g'].unique())

    # 子图1：完整模型的热力图
    pivot_full = df_hc.pivot_table(values='h_t_plus_1', index='tau_g', columns='tau_c')
    im1 = axes[0, 0].contourf(pivot_full.columns, pivot_full.index, pivot_full.values, levels=15, cmap='YlOrRd')
    axes[0, 0].set_xlabel('子代时间投入 τ_c', fontsize=12)
    axes[0, 0].set_ylabel('父代时间投入 τ_g', fontsize=12)
    axes[0, 0].set_title('(a) 人力资本积累水平 h_{t+1}\n（子代与父代共同投入）', fontsize=13, fontweight='bold')
    plt.colorbar(im1, ax=axes[0, 0])

    # 子图2：边际效应对比
    # 固定一个维度，观察另一个维度的影响
    tau_g_fixed = 0.15
    df_fixed_g = df_hc[np.isclose(df_hc['tau_g'], tau_g_fixed, atol=0.01)]
    axes[0, 1].plot(df_fixed_g['tau_c'], df_fixed_g['h_t_plus_1'], 'b-o', linewidth=2, label='完整模型')
    axes[0, 1].plot(df_fixed_g['tau_c'], df_fixed_g['h_t_plus_1_only_c'], 'r--s', linewidth=2, label='仅子代投入')
    axes[0, 1].set_xlabel('子代时间投入 τ_c', fontsize=12)
    axes[0, 1].set_ylabel('人力资本水平 h_{t+1}', fontsize=12)
    axes[0, 1].set_title(f'(b) 子代时间投入的边际效应\n（固定父代投入 τ_g={tau_g_fixed}）', fontsize=13, fontweight='bold')
    axes[0, 1].legend(fontsize=11)
    axes[0, 1].grid(True, alpha=0.3)

    # 子图3：互补性分析
    tau_c_fixed = 0.15
    df_fixed_c = df_hc[np.isclose(df_hc['tau_c'], tau_c_fixed, atol=0.01)]
    axes[1, 0].plot(df_fixed_c['tau_g'], df_fixed_c['h_t_plus_1'], 'g-o', linewidth=2, label='完整模型')
    axes[1, 0].plot(df_fixed_c['tau_g'], df_fixed_c['h_t_plus_1_only_g'], 'm--s', linewidth=2, label='仅父代投入')
    axes[1, 0].set_xlabel('父代时间投入 τ_g', fontsize=12)
    axes[1, 0].set_ylabel('人力资本水平 h_{t+1}', fontsize=12)
    axes[1, 0].set_title(f'(c) 父代时间投入的边际效应\n（固定子代投入 τ_c={tau_c_fixed}）', fontsize=13, fontweight='bold')
    axes[1, 0].legend(fontsize=11)
    axes[1, 0].grid(True, alpha=0.3)

    # 子图4：效率差异展示（θ_c vs θ_g）
    # 计算边际产出
    df_sorted = df_hc.sort_values('tau_c')
    tau_g_levels = [0.10, 0.15, 0.20]
    for tau_g_val in tau_g_levels:
        df_subset = df_hc[np.isclose(df_hc['tau_g'], tau_g_val, atol=0.01)]
        df_subset = df_subset.sort_values('tau_c')
        axes[1, 1].plot(df_subset['tau_c'], df_subset['h_t_plus_1'],
                       linewidth=2, marker='o', label=f'τ_g={tau_g_val:.2f}')

    axes[1, 1].set_xlabel('子代时间投入 τ_c', fontsize=12)
    axes[1, 1].set_ylabel('人力资本水平 h_{t+1}', fontsize=12)
    axes[1, 1].set_title('(d) 代际时间投入的互补性\n（不同父代投入水平）', fontsize=13, fontweight='bold')
    axes[1, 1].legend(fontsize=11)
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/user/econ/figure1_human_capital.png', dpi=300, bbox_inches='tight')
    print("✓ 图1已保存: figure1_human_capital.png")
    return fig


def plot_mediation_effects(df_med):
    """
    可视化2：中介效应分解
    """
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # 子图1：各中介效应的演变
    axes[0, 0].plot(df_med['D_t'], df_med['direct'], 'b-o', linewidth=2.5, markersize=6, label='直接效应')
    axes[0, 0].plot(df_med['D_t'], df_med['expenditure_med'], 'r--s', linewidth=2.5, markersize=6, label='赡养支出中介（负）')
    axes[0, 0].plot(df_med['D_t'], df_med['care_time_med'], 'g-.^', linewidth=2.5, markersize=6, label='照料时间中介（正）')
    axes[0, 0].plot(df_med['D_t'], df_med['risk_med'], 'm:d', linewidth=2.5, markersize=6, label='赡养风险中介（正）')
    axes[0, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)
    axes[0, 0].set_xlabel('赡养比 D_t', fontsize=12)
    axes[0, 0].set_ylabel('对储蓄率的影响', fontsize=12)
    axes[0, 0].set_title('(a) 老龄化的中介效应分解', fontsize=13, fontweight='bold')
    axes[0, 0].legend(fontsize=10, loc='best')
    axes[0, 0].grid(True, alpha=0.3)

    # 子图2：总效应及其分解
    axes[0, 1].plot(df_med['D_t'], df_med['total'], 'k-o', linewidth=3, markersize=7, label='总效应')
    axes[0, 1].fill_between(df_med['D_t'], 0, df_med['total'], alpha=0.2, color='gray')
    axes[0, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    axes[0, 1].set_xlabel('赡养比 D_t', fontsize=12)
    axes[0, 1].set_ylabel('对储蓄率的总效应', fontsize=12)
    axes[0, 1].set_title('(b) 老龄化对储蓄率的总效应', fontsize=13, fontweight='bold')
    axes[0, 1].legend(fontsize=11)
    axes[0, 1].grid(True, alpha=0.3)

    # 子图3：内生变量的演变
    ax3_1 = axes[1, 0]
    ax3_2 = ax3_1.twinx()

    line1 = ax3_1.plot(df_med['D_t'], df_med['tau_o'], 'b-o', linewidth=2.5, markersize=6, label='赡养支出比例 τ_o')
    line2 = ax3_1.plot(df_med['D_t'], df_med['tau_o_time'], 'r--s', linewidth=2.5, markersize=6, label='照料时间 τ_o')
    line3 = ax3_2.plot(df_med['D_t'], df_med['p'], 'g-.^', linewidth=2.5, markersize=6, label='存活概率 p')

    ax3_1.set_xlabel('赡养比 D_t', fontsize=12)
    ax3_1.set_ylabel('赡养支出与照料时间', fontsize=12, color='black')
    ax3_2.set_ylabel('存活概率', fontsize=12, color='g')
    ax3_1.set_title('(c) 内生赡养行为变量的演变', fontsize=13, fontweight='bold')

    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax3_1.legend(lines, labels, fontsize=10, loc='upper left')
    ax3_1.grid(True, alpha=0.3)

    # 子图4：堆叠面积图展示中介效应贡献
    # 为了堆叠，需要将负值和正值分开
    positive_effects = np.maximum(df_med['direct'], 0) + np.maximum(df_med['care_time_med'], 0) + np.maximum(df_med['risk_med'], 0)
    negative_effects = np.minimum(df_med['expenditure_med'], 0)

    axes[1, 1].fill_between(df_med['D_t'], 0, df_med['direct'], alpha=0.6, label='直接效应', color='#1f77b4')
    axes[1, 1].fill_between(df_med['D_t'], df_med['direct'],
                           df_med['direct'] + df_med['care_time_med'],
                           alpha=0.6, label='照料时间中介', color='#2ca02c')
    axes[1, 1].fill_between(df_med['D_t'], df_med['direct'] + df_med['care_time_med'],
                           df_med['direct'] + df_med['care_time_med'] + df_med['risk_med'],
                           alpha=0.6, label='赡养风险中介', color='#9467bd')
    axes[1, 1].fill_between(df_med['D_t'], 0, df_med['expenditure_med'],
                           alpha=0.6, label='赡养支出中介', color='#d62728')
    axes[1, 1].plot(df_med['D_t'], df_med['total'], 'k-', linewidth=2.5, label='总效应')

    axes[1, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    axes[1, 1].set_xlabel('赡养比 D_t', fontsize=12)
    axes[1, 1].set_ylabel('对储蓄率的影响', fontsize=12)
    axes[1, 1].set_title('(d) 中介效应的累积贡献', fontsize=13, fontweight='bold')
    axes[1, 1].legend(fontsize=10, loc='best')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/user/econ/figure2_mediation_effects.png', dpi=300, bbox_inches='tight')
    print("✓ 图2已保存: figure2_mediation_effects.png")
    return fig


def plot_saving_rate_aging(df_saving):
    """
    可视化3：储蓄率与人口结构
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 子图1：储蓄率与赡养比
    axes[0].plot(df_saving['D_t'], df_saving['saving_rate'], 'b-o', linewidth=2.5, markersize=7)
    axes[0].fill_between(df_saving['D_t'], 0, df_saving['saving_rate'], alpha=0.2, color='blue')
    axes[0].set_xlabel('赡养比 D_t', fontsize=12)
    axes[0].set_ylabel('家庭储蓄率 ρ_t', fontsize=12)
    axes[0].set_title('(a) 储蓄率与老龄化程度', fontsize=13, fontweight='bold')
    axes[0].grid(True, alpha=0.3)

    # 子图2：储蓄率与抚养比（反向关系）
    axes[1].plot(df_saving['C_t'], df_saving['saving_rate'], 'r-s', linewidth=2.5, markersize=7)
    axes[1].fill_between(df_saving['C_t'], 0, df_saving['saving_rate'], alpha=0.2, color='red')
    axes[1].set_xlabel('抚养比 C_t', fontsize=12)
    axes[1].set_ylabel('家庭储蓄率 ρ_t', fontsize=12)
    axes[1].set_title('(b) 储蓄率与少子化程度', fontsize=13, fontweight='bold')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/user/econ/figure3_saving_rate.png', dpi=300, bbox_inches='tight')
    print("✓ 图3已保存: figure3_saving_rate.png")
    return fig


def main():
    """
    主函数：运行所有数值模拟
    """
    print("="*60)
    print("数值模拟：人力资本积累与家庭赡养的中介效应")
    print("="*60)

    # 初始化模型
    model = OLGModel()

    print("\n[1] 模拟人力资本积累对时间投入的敏感性...")
    df_hc = model.simulate_human_capital_sensitivity()
    print(f"    完成！生成{len(df_hc)}个数据点")

    print("\n[2] 模拟中介效应随老龄化程度的变化...")
    df_med = model.simulate_mediation_effects()
    print(f"    完成！生成{len(df_med)}个数据点")

    print("\n[3] 模拟储蓄率随人口结构的变化...")
    df_saving = model.simulate_saving_rate_aging()
    print(f"    完成！生成{len(df_saving)}个数据点")

    print("\n" + "="*60)
    print("生成可视化图表...")
    print("="*60)

    # 生成图表
    fig1 = plot_human_capital_sensitivity(df_hc)
    fig2 = plot_mediation_effects(df_med)
    fig3 = plot_saving_rate_aging(df_saving)

    # 保存数据
    print("\n保存模拟数据...")
    df_hc.to_csv('/home/user/econ/data_human_capital.csv', index=False)
    print("✓ 数据已保存: data_human_capital.csv")

    df_med.to_csv('/home/user/econ/data_mediation_effects.csv', index=False)
    print("✓ 数据已保存: data_mediation_effects.csv")

    df_saving.to_csv('/home/user/econ/data_saving_rate.csv', index=False)
    print("✓ 数据已保存: data_saving_rate.csv")

    print("\n" + "="*60)
    print("模拟结果总结")
    print("="*60)

    # 输出关键结果
    print("\n【1. 人力资本积累】")
    print(f"  • 子代效率参数 θ_c = {model.theta_c:.2f}")
    print(f"  • 父代效率参数 θ_g = {model.theta_g:.2f}")
    print(f"  • 效率比 θ_c/θ_g = {model.theta_c/model.theta_g:.2f}")
    print(f"  • 人力资本范围: [{df_hc['h_t_plus_1'].min():.3f}, {df_hc['h_t_plus_1'].max():.3f}]")

    print("\n【2. 中介效应分解】（在赡养比D_t=1.0时）")
    idx_mid = len(df_med) // 2
    print(f"  • 直接效应: {df_med.loc[idx_mid, 'direct']:.5f}")
    print(f"  • 赡养支出中介: {df_med.loc[idx_mid, 'expenditure_med']:.5f} (负向)")
    print(f"  • 照料时间中介: {df_med.loc[idx_mid, 'care_time_med']:.5f} (正向)")
    print(f"  • 赡养风险中介: {df_med.loc[idx_mid, 'risk_med']:.5f} (正向)")
    print(f"  • 总效应: {df_med.loc[idx_mid, 'total']:.5f}")

    print("\n【3. 储蓄率】")
    print(f"  • 最低储蓄率: {df_saving['saving_rate'].min():.4f} (低度老龄化)")
    print(f"  • 最高储蓄率: {df_saving['saving_rate'].max():.4f} (高度老龄化)")
    print(f"  • 平均储蓄率: {df_saving['saving_rate'].mean():.4f}")

    print("\n" + "="*60)
    print("所有模拟完成！")
    print("="*60)

    return df_hc, df_med, df_saving


if __name__ == "__main__":
    df_hc, df_med, df_saving = main()
