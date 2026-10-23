#!/usr/bin/env python3
"""Build publication-oriented figures for the two-RQ paper framework.

Sources are the validated project CSV outputs. Sensitivity figures are deliberately
not fabricated here; they are to be built after the planned sensitivity runs exist.
"""
from __future__ import annotations
import csv, re
from pathlib import Path
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results'/'paper'/'figures'
UNITS=['G1','G2','G13','G22','G23','G27']
UCOL={'G1':'#1769aa','G2':'#e07a19','G13':'#2a8c55','G22':'#c43c39','G23':'#8057a5','G27':'#7a5b48'}
KCOL={'K1':'#64748b','K2':'#168aad','K3':'#2a9d8f','K4':'#e9a23b','K5':'#e76f51','K6':'#8b5cf6'}
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if Path(FONT).exists():font_manager.fontManager.addfont(FONT)
plt.rcParams.update({'font.family':'Noto Sans CJK JP','font.size':9,'axes.titlesize':11,
    'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'axes.spines.top':False,
    'axes.spines.right':False,'figure.facecolor':'white','axes.facecolor':'white',
    'savefig.facecolor':'white','svg.fonttype':'none'})

def read_csv(p):
    with open(p,newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def save(fig,name):
    OUT.mkdir(parents=True,exist_ok=True)
    fig.savefig(OUT/f'{name}.png',dpi=300,bbox_inches='tight')
    fig.savefig(OUT/f'{name}.svg',bbox_inches='tight')
    plt.close(fig)

def fig01_framework():
    fig,ax=plt.subplots(figsize=(15,7));ax.set_xlim(0,15);ax.set_ylim(0,7);ax.axis('off')
    left=FancyBboxPatch((.25,1.65),6.75,4.8,boxstyle='round,pad=.12,rounding_size=.16',
                        fc='#f0f7ff',ec='#3274a1',lw=1.5)
    right=FancyBboxPatch((8.0,1.65),6.75,4.8,boxstyle='round,pad=.12,rounding_size=.16',
                         fc='#f5f7fb',ec='#475569',lw=1.5)
    ax.add_patch(left);ax.add_patch(right)
    ax.text(.55,6.07,'RQ1  冷端运行机理（机组侧）',fontsize=13,weight='bold',color='#174c72')
    ax.text(8.3,6.07,'RQ2  冷源中断下的电网级联',fontsize=13,weight='bold',color='#29384c')
    cold=[('补水中断','M → 0'),('水池库存','V / 水位'),('泵与循环水','NPSH / qcw'),('塔—凝汽器','温度 / 排热 / 背压'),('保护与能力','P_available(t)\nt_trip / 标签')]
    xs=[.52,1.78,3.04,4.30,5.56]
    for i,((title,sub),x) in enumerate(zip(cold,xs)):
        b=FancyBboxPatch((x,3.92),1.1,1.28,boxstyle='round,pad=.05,rounding_size=.08',
                         fc='#d9ecfa' if i<4 else '#c8e1f3',ec='#3274a1',lw=1.0)
        ax.add_patch(b);ax.text(x+.55,4.77,title,ha='center',va='center',weight='bold',fontsize=8.5)
        ax.text(x+.55,4.27,sub,ha='center',va='center',fontsize=7.7)
        if i<4:ax.annotate('',xy=(x+1.24,4.56),xytext=(x+1.12,4.56),arrowprops=dict(arrowstyle='->',color='#3274a1',lw=1.3))
    ax.text(.58,3.33,'冷端状态轨迹：水位 · qcw · 冷却水温 · 排热 · 背压',fontsize=8.5,color='#244e69')
    ax.text(.58,2.78,'RQ1 终点：机组侧可用出力与冷端保护事件（不评估 H/级联）',fontsize=8.2,weight='bold',color='#174c72')
    grid=[('频率响应','SFR / UFLS'),('受限再调度','Pg / 备用'),('AC 事件级联','线路 / 孤岛'),('网侧结果','H / f_min / shed')]
    gx=[8.38,9.94,11.50,13.06]
    for i,((title,sub),x) in enumerate(zip(grid,gx)):
        b=FancyBboxPatch((x,3.92),1.34,1.28,boxstyle='round,pad=.05,rounding_size=.08',
                         fc='#e9edf4' if i<3 else '#dbe4ef',ec='#64748b',lw=1.0)
        ax.add_patch(b);ax.text(x+.67,4.77,title,ha='center',va='center',weight='bold',fontsize=8.5)
        ax.text(x+.67,4.27,sub,ha='center',va='center',fontsize=7.7)
        if i<3:ax.annotate('',xy=(x+1.49,4.56),xytext=(x+1.36,4.56),arrowprops=dict(arrowstyle='->',color='#64748b',lw=1.3))
    # Interface between cold-end and grid.
    ax.annotate('',xy=(8.28,3.35),xytext=(6.88,3.35),arrowprops=dict(arrowstyle='-|>',color='#1769aa',lw=2.0))
    ax.text(7.57,3.55,'P_available(t) + 跳闸事件',ha='center',fontsize=8.0,color='#174c72',weight='bold')
    # Grid response feedback to surviving units.
    ax.annotate('',xy=(6.45,2.4),xytext=(10.75,2.4),arrowprops=dict(arrowstyle='-|>',color='#b45309',lw=1.8))
    ax.text(8.6,2.66,'幸存机组 Pg 更新 → 冷端负荷与后续轨迹反馈',ha='center',fontsize=8.0,color='#9a4a08')
    # Sensitivity bracket across both domains.
    ax.plot([.55,14.45],[.95,.95],color='#7b8794',lw=1.0,ls=(0,(4,2)))
    ax.text(7.5,.58,'敏感性 / 鲁棒性检验：冷端参数扰动 + 电网参数扰动；不作概率解释',ha='center',fontsize=9,weight='bold',color='#374151')
    ax.set_title('论文逻辑框架：先建立冷端机理，再评估电网级联',loc='left',pad=10,weight='bold',fontsize=14)
    save(fig,'paper_fig01_framework')

def fig02_coldend():
    series={u:read_csv(ROOT/f'results/reference/coldend_p5/unit_series/{u}.csv') for u in UNITS}
    anchors={r['unit']:r for r in read_csv(ROOT/'data/coldend/unit_anchors.csv')}
    fig,axs=plt.subplots(2,2,figsize=(12.8,8.0),sharex=False);axs=axs.ravel()
    # (a) normalized inventory margin
    for u in UNITS:
        rr=series[u];a=anchors[u];norm=float(a['level_normal_m']);thr=float(a['level_trip_m'])
        x=np.array([float(r['t_h']) for r in rr]);lev=np.array([float(r['basin_level_m']) for r in rr])
        axs[0].plot(x,(lev-thr)/(norm-thr),color=UCOL[u],lw=1.7,label=u)
        axs[0].scatter([x[-1]],[(lev[-1]-thr)/(norm-thr)],color=UCOL[u],s=16,zorder=4)
    axs[0].axhline(0,color='#b42318',ls='--',lw=1)
    axs[0].set_ylabel('归一化水位裕度');axs[0].set_xlabel('断水后时间 (h)');axs[0].set_title('(a) 水池库存与保护阈值',loc='left',weight='bold');axs[0].grid(alpha=.18)
    # (b) flow fraction and relative available power
    for u in UNITS:
        rr=series[u];x=np.array([float(r['t_h']) for r in rr])
        q=np.array([float(r['qcw_frac']) for r in rr]);p=np.array([float(r['p_avail_mw']) for r in rr])
        p0=max(p[0],1e-9)
        axs[1].plot(x,q,color=UCOL[u],lw=1.6)
        axs[1].plot(x,p/p0,color=UCOL[u],lw=1.2,ls='--',alpha=.85)
    axs[1].set_ylabel('相对初始值');axs[1].set_xlabel('断水后时间 (h)');axs[1].set_title('(b) 循环流量比例与可用出力比例',loc='left',weight='bold');axs[1].grid(alpha=.18)
    # (c) backpressure + saturation temperature
    t2=axs[2].twinx()
    for u in UNITS:
        rr=series[u];x=np.array([float(r['t_h']) for r in rr])
        axs[2].plot(x,[float(r['backpressure_kpa']) for r in rr],color=UCOL[u],lw=1.65)
        t2.plot(x,[float(r['t_sat_c']) for r in rr],color=UCOL[u],lw=1.0,ls=':',alpha=.75)
    axs[2].set_ylabel('凝汽器背压 (kPa)');t2.set_ylabel('饱和温度 (°C)')
    axs[2].set_xlabel('断水后时间 (h)');axs[2].set_title('(c) 背压与饱和温度',loc='left',weight='bold');axs[2].grid(alpha=.18)
    # (d) heat rejection + evaporation
    evax=axs[3].twinx()
    for u in UNITS:
        rr=series[u];x=np.array([float(r['t_h']) for r in rr])
        axs[3].plot(x,[float(r['heat_reject_mw_th']) for r in rr],color=UCOL[u],lw=1.55)
        evax.plot(x,[float(r['evaporation_m3s'])*3600 for r in rr],color=UCOL[u],lw=1.0,ls=':',alpha=.72)
    axs[3].set_ylabel('排热量 (MWth)');evax.set_ylabel('蒸发量 (m³/h)')
    axs[3].set_xlabel('断水后时间 (h)');axs[3].set_title('(d) 排热与蒸发',loc='left',weight='bold');axs[3].grid(alpha=.18)
    unit_handles=[Line2D([0],[0],color=UCOL[u],lw=2,label=u) for u in UNITS]
    style_handles=[Line2D([0],[0],color='#475569',lw=1.6,ls='-',label='左轴主变量'),Line2D([0],[0],color='#475569',lw=1.2,ls=':',label='右轴变量')]
    fig.legend(handles=unit_handles+style_handles,ncol=8,loc='upper center',frameon=False,bbox_to_anchor=(.5,.99),fontsize=8)
    fig.suptitle('RQ1 | P5 固定出力参考中的冷端状态演化',x=.06,ha='left',weight='bold',fontsize=14,y=1.035)
    fig.text(.06,.005,'每条轨迹在本机低水位保护处结束；颜色表示机组，线型区分同一面板的双变量。P5 用于冷端机理参照，不与 K1–K6 耦合结果直接作因果比较。',fontsize=8,color='#475569')
    fig.tight_layout(rect=(0,.04,1,.94),h_pad=1.5,w_pad=1.5)
    save(fig,'paper_fig02_coldend_mechanism')

def fig03_k2_feedback():
    sid='K2-G1-G2';cool=read_csv(ROOT/f'results/K2/scenarios/{sid}/cooling_demand_response.csv')
    disp=read_csv(ROOT/f'results/K2/scenarios/{sid}/dispatch_trajectory.csv')
    summary=next(r for r in read_csv(ROOT/'results/K2/tables/pairwise_summary.csv') if r['scenario_id']==sid)
    anchors={r['unit']:r for r in read_csv(ROOT/'data/coldend/unit_anchors.csv')}
    trips=[]
    for field,pattern,scale in [('initial_trip_events',r'([^@;]+)@([0-9.]+)h',1),('other_coldend_trip_events',r'([^@;]+)@([0-9.]+)s',1/3600)]:
        for u,t in re.findall(pattern,summary.get(field,'')):trips.append((u,float(t)*scale))
    fig,axs=plt.subplots(4,1,figsize=(11.5,9.6),sharex=True,gridspec_kw={'height_ratios':[.9,1,1,1]})
    units=['G1','G2']
    for u in units:
        rr=[r for r in cool if r['unit']==u];x=[float(r['system_t_h']) for r in rr]
        a=anchors[u];n=float(a['level_normal_m']);thr=float(a['level_trip_m'])
        axs[0].plot(x,[(float(r['basin_level_m'])-thr)/(n-thr) for r in rr],color=UCOL[u],lw=1.7,label=u)
    axs[0].axhline(0,color='#b42318',ls='--',lw=1,label='低水位保护阈值')
    axs[0].set_ylabel('归一化水位\n裕度');axs[0].set_title('(a) 冷端库存',loc='left',weight='bold');axs[0].legend(frameon=False,ncol=3,fontsize=7,loc='upper right');axs[0].grid(alpha=.17)
    water_ax=axs[1].twinx()
    for u in units:
        rr=[r for r in cool if r['unit']==u];x=[float(r['system_t_h']) for r in rr]
        axs[1].plot(x,[float(r['pg_command_mw']) for r in rr],color=UCOL[u],lw=1.7,label=f'{u} Pg')
        water_ax.plot(x,[float(r['makeup_required_m3h']) for r in rr],color=UCOL[u],lw=1.2,ls='--',label=f'{u}需补水')
    axs[1].set_ylabel('Pg 命令 (MW)');water_ax.set_ylabel('需补水量 (m³/h)')
    h1,l1=axs[1].get_legend_handles_labels();h2,l2=water_ax.get_legend_handles_labels()
    axs[1].legend(h1+h2,l1+l2,frameon=False,ncol=2,fontsize=7,loc='upper left')
    axs[1].set_title('(b) 出力与需补水响应',loc='left',weight='bold');axs[1].grid(alpha=.17)
    capax=axs[2].twinx()
    for u in units:
        rr=[r for r in cool if r['unit']==u];x=[float(r['system_t_h']) for r in rr]
        axs[2].plot(x,[float(r['backpressure_kpa']) for r in rr],color=UCOL[u],lw=1.7,label=f'{u}背压')
        capax.plot(x,[float(r['thermal_cap_mw']) for r in rr],color=UCOL[u],lw=1.1,ls='--',alpha=.85,label=f'{u}热力能力')
    axs[2].set_ylabel('背压 (kPa)');capax.set_ylabel('热力能力 (MW)')
    h1,l1=axs[2].get_legend_handles_labels();h2,l2=capax.get_legend_handles_labels()
    axs[2].legend(h1+h2,l1+l2,frameon=False,ncol=2,fontsize=7,loc='upper left')
    axs[2].set_title('(c) 热力状态',loc='left',weight='bold');axs[2].grid(alpha=.17)
    x=[0.0]+[float(r['system_t_h']) for r in disp];y=[60.0]+[float(r['frequency_hz']) for r in disp]
    axs[3].plot(x,y,color='#344054',lw=1.3)
    st=[0.0]+[float(r['ufls_stage']) for r in disp]
    axs[3].scatter(x,y,c=st,cmap='Oranges',s=7,zorder=3)
    axs[3].axhline(59.3,color='#b42318',ls='--',lw=1,label='UFLS 第一档 59.30 Hz')
    axs[3].set_ylabel('频率 (Hz)');axs[3].set_ylim(59.15,60.05);axs[3].set_xlabel('相对同时断水时刻 (h)')
    axs[3].set_title('(d) 电网频率响应',loc='left',weight='bold');axs[3].legend(frameon=False,fontsize=7,loc='lower right');axs[3].grid(alpha=.17)
    for ax in axs:
        for u,t in trips:ax.axvline(t,color=UCOL[u],ls=':',lw=1.0,alpha=.7)
    for u,t in trips:axs[0].text(t,1.02,f'{u}跳闸',rotation=90,ha='right',va='bottom',fontsize=7,color=UCOL[u])
    axs[-1].set_xlim(0,max(t for _,t in trips)+.35)
    fig.suptitle('RQ2 | K2-G1-G2：电网事件与幸存机组冷端反馈',x=.07,ha='left',weight='bold',fontsize=14,y=.995)
    fig.text(.07,.005,'G1、G2补水均从 t=0 中断。虚线/右轴为热力与水量响应；竖线为实际冷端跳闸事件。该情景为确定性案例，不代表概率或跨系统通则。',fontsize=8,color='#475569')
    fig.tight_layout(rect=(0,.04,1,.97),h_pad=.65)
    save(fig,'paper_fig03_k2_feedback')

def fig04_scenario_outcomes():
    rows=read_csv(ROOT/'results/analysis/scenario_master.csv')
    ks=[f'K{i}' for i in range(1,7)]
    fig,axs=plt.subplots(1,2,figsize=(13,5.4),gridspec_kw={'width_ratios':[.9,1.25]})
    # Panel A: all 63 baseline scenarios by K.
    for xi,k in enumerate(ks):
        rr=[r for r in rows if r['K']==k]
        jitter=np.linspace(-.17,.17,len(rr)) if len(rr)>1 else [0]
        for j,(r,dj) in enumerate(zip(rr,jitter)):
            marker='D' if r['censored_units'] else 'o'
            fc=KCOL[k] if r['ufls_triggered'] else 'white'
            axs[0].scatter(xi+dj,float(r['H_hard_buses']),s=34,marker=marker,facecolor=fc,
                           edgecolor=KCOL[k],lw=.9,alpha=.9,zorder=3)
        axs[0].text(xi,max(float(r['H_hard_buses']) for r in rr)+1.2,f'n={len(rr)}',ha='center',fontsize=7,color=KCOL[k])
    axs[0].set_xticks(range(6),ks);axs[0].set_ylabel('硬失供母线数 H');axs[0].set_ylim(-1,33)
    axs[0].set_title('(a) K1–K6 基线逐案 H',loc='left',weight='bold');axs[0].grid(axis='y',alpha=.18)
    # Panel B: frequency vs hard service loss.
    for r in rows:
        k=r['K'];marker='D' if r['censored_units'] else 'o'
        size=24+0.42*max(0,float(r['total_shed_mw']))
        face=KCOL[k] if r['ufls_triggered'] else 'white'
        axs[1].scatter(float(r['f_nadir_hz']),float(r['H_hard_buses']),s=size,marker=marker,
                       facecolor=face,edgecolor=KCOL[k],lw=.85,alpha=.8,zorder=3)
    axs[1].axvline(59.3,color='#b42318',ls='--',lw=1,label='UFLS 第一档')
    axs[1].set_xlim(57.5,60.1);axs[1].set_ylim(-1,33)
    axs[1].set_xlabel('频率最低点 (Hz)');axs[1].set_ylabel('硬失供母线数 H')
    axs[1].set_title('(b) 频率与 H（气泡∝总切负荷）',loc='left',weight='bold');axs[1].grid(alpha=.18)
    leg=[Line2D([0],[0],marker='o',color='none',markerfacecolor=KCOL[k],markeredgecolor=KCOL[k],label=k,markersize=6) for k in ks]
    leg += [Line2D([0],[0],marker='o',color='none',markerfacecolor='white',markeredgecolor='#475569',label='无UFLS',markersize=6),
            Line2D([0],[0],marker='D',color='none',markerfacecolor='white',markeredgecolor='#475569',label='有删失单位',markersize=6)]
    axs[1].legend(handles=leg,frameon=False,ncol=4,fontsize=7,loc='upper right')
    fig.suptitle('RQ2 | K1–K6 规定情景集的电网级联结果',x=.06,ha='left',weight='bold',fontsize=14,y=1.02)
    fig.text(.06,.005,'63个基线情景为确定性枚举；每个点代表一个情景，枚举集内占比不是故障概率。H=F3∨F2b；频率、UFLS与切负荷分别解释。',fontsize=8,color='#475569')
    fig.tight_layout(rect=(0,.04,1,.94),w_pad=1.4)
    save(fig,'paper_fig04_scenario_outcomes')

def main():
    fig01_framework();fig02_coldend();fig03_k2_feedback();fig04_scenario_outcomes()
    print(f'Paper figures built at {OUT}: 4 figures (PNG+SVG); sensitivity plots await actual runs.')
if __name__=='__main__':main()
