#!/usr/bin/env python3
"""Build audited analysis dataset, figures, and self-contained HTML report for K1-K6."""
from __future__ import annotations
import base64, csv, html, json, math, re
from pathlib import Path
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib.patches as patches
from matplotlib.lines import Line2D
from matplotlib.colors import Normalize
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results' / 'analysis'
FIG = OUT / 'figures'
UNITS = ['G1','G2','G13','G22','G23','G27']
KCOL = {'K1':'#64748b','K2':'#168aad','K3':'#2a9d8f','K4':'#e9a23b','K5':'#e76f51','K6':'#8b5cf6'}
UCOL = {'G1':'#1f77b4','G2':'#ff7f0e','G13':'#2ca02c','G22':'#d62728','G23':'#9467bd','G27':'#8c564b'}
NCLASS = {'N0':'#4c78a8','N1':'#72b7b2','N2':'#f2a541','N3':'#d1495b'}
CJK_FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if Path(CJK_FONT).exists():
    font_manager.fontManager.addfont(CJK_FONT)
plt.rcParams.update({
    'font.family':'Noto Sans CJK JP', 'font.size':9,
    'axes.titlesize':12, 'axes.labelsize':9,
    'xtick.labelsize':8, 'ytick.labelsize':7,
    'axes.spines.top':False, 'axes.spines.right':False,
    'figure.facecolor':'white', 'axes.facecolor':'white',
    'savefig.facecolor':'white', 'svg.fonttype':'none',
})


def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def fnum(row, key, default=0.0):
    try:
        v = row.get(key, '')
        return float(v) if v not in ('', None) else default
    except (TypeError, ValueError):
        return default

def nclass(s):
    m = re.match(r'(N[0-3])', str(s or ''))
    return m.group(1) if m else 'NA'

def parse_units(text):
    return [x for x in str(text or '').replace('+',';').split(';') if x]

def trip_events(row, k):
    if k == 'K1':
        unit = row['initial_unit']
        return [(unit, fnum(row,'initial_trip_h'))]
    out=[]
    evs = row.get('initial_trip_events','')
    for e in filter(None, evs.split(';')):
        m=re.fullmatch(r'([^@]+)@([0-9.]+)h',e)
        if m: out.append((m.group(1),float(m.group(2))))
    for e in filter(None,row.get('other_coldend_trip_events','').split(';')):
        m=re.fullmatch(r'([^@]+)@([0-9.]+)s',e)
        if m: out.append((m.group(1),float(m.group(2))/3600.0))
    return out

def load_master():
    srcs = {
        'K1':'results/K1/tables/six_unit_comparison.csv',
        'K2':'results/K2/tables/pairwise_summary.csv',
        'K3':'results/K3/tables/triple_summary.csv',
        'K4':'results/K4/tables/quadruple_summary.csv',
        'K5':'results/K5/tables/quintuple_summary.csv',
        'K6':'results/K6/tables/six_unit_summary.csv',
    }
    rows=[]
    for k, rel in srcs.items():
        for raw in read_csv(ROOT/rel):
            if k == 'K1':
                units=[raw['initial_unit']]
                sid=f"K1-{units[0]}"
                count=1
                censored=''
                status=raw.get('simulation_stop_reason','')
            else:
                units=parse_units(raw.get('initial_makeup_failure_units',''))
                sid=raw.get('scenario_id','')
                count=int(fnum(raw,'faulted_units_tripped_count_before_stop',len(units) if k in ('K2','K3') else 0))
                # K2 and K3 archived batches fully tripped all selected units.
                if k in ('K2','K3'): count=len(units)
                censored=raw.get('faulted_units_not_tripped_before_stop','')
                status=raw.get('simulation_stop_reason','')
            events=trip_events(raw,k)
            event_units=list(dict.fromkeys(u for u,_ in events))
            actual_selected=sorted(set(event_units).intersection(units))
            first=fnum(raw,'initial_trip_h')
            h=int(fnum(raw,'n_bus_hard_failure'))
            fmin=fnum(raw,'f_nadir_hz',float('nan'))
            uf=fnum(raw,'ufls_shed_mw')
            total=fnum(raw,'total_shed_mw')
            # The legacy K1 comparison predates static_grid_shed_mw; derive the
            # non-UFLS component from its archived total-shed field.
            static=(fnum(raw,'static_grid_shed_mw') if raw.get('static_grid_shed_mw') not in ('',None)
                    else max(0.0,total-uf))
            raw_class=raw.get('impact_class','')
            buslist=parse_units(raw.get('hard_failure_buses',''))
            record={
                'K':k,'scenario_id':sid,'units':'+'.join(units),'unit_count':len(units),
                'initial_trip_h':first,'trip_order':' → '.join(f'{u}@{t:.4f}h' for u,t in events),
                'trip_count_before_stop':count,'actual_trip_units':';'.join(actual_selected),'censored_units':censored,
                'hard_stop':int('hard_service_loss' in status),
                'stop_reason':status,'f_nadir_hz':fmin,'ufls_shed_mw':uf,
                'static_grid_shed_mw':static,'total_shed_mw':total,
                'H_hard_buses':h,'hard_failure_buses':';'.join(buslist),
                'F3_buses_seen':int(fnum(raw,'n_f3_deenergized')),
                'N_class':nclass(raw_class),'raw_impact_class':raw_class,
                'cooling_tracking_elapsed_h':fnum(raw,'cooling_tracking_elapsed_h'),
                'total_load_mw':fnum(raw,'total_load_mw',189.2),
                'ufls_triggered':int(uf>1e-9),
                'source_file':rel,
                'scenario_status':raw.get('scenario_status','completed'),
            }
            rows.append(record)
    order={f'K{i}':i for i in range(1,7)}
    rows.sort(key=lambda r:(order[r['K']],r['scenario_id']))
    return rows

def write_master(rows):
    path=OUT/'scenario_master.csv'
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
    return path

def savefig(fig, name):
    fig.savefig(FIG/f'{name}.png',dpi=190,bbox_inches='tight')
    fig.savefig(FIG/f'{name}.svg',bbox_inches='tight')
    plt.close(fig)

def fig01_mechanism():
    fig,ax=plt.subplots(figsize=(14,5.4));ax.set_xlim(0,14);ax.set_ylim(0,6);ax.axis('off')
    cold=[('补水中断','补水供给 M→0'),('水池库存','水位 / 有效库存'),('循环泵与冷却塔','流量 / 出口水温'),('凝汽器','背压 / 排热'),('耗水与保护','蒸发、排污、飘滴\n低水位跳机')]
    xs=[.35,3.0,5.65,8.3,10.95]
    colors=['#e9c46a','#9bd3ae','#72b7b2','#5fa8d3','#e76f51']
    for i,((title,sub),x,c) in enumerate(zip(cold,xs,colors)):
        box=patches.FancyBboxPatch((x,3.7),2.2,1.25,boxstyle='round,pad=0.08,rounding_size=.12',facecolor=c,edgecolor='#344054',lw=1.2,alpha=.93)
        ax.add_patch(box);ax.text(x+1.1,4.48,title,ha='center',va='center',weight='bold',fontsize=10);ax.text(x+1.1,4.03,sub,ha='center',va='center',fontsize=8)
        if i<4: ax.annotate('',xy=(xs[i+1]-.08,4.32),xytext=(x+2.28,4.32),arrowprops=dict(arrowstyle='->',lw=1.7,color='#344054'))
    gridbox=patches.FancyBboxPatch((4.1,.65),5.8,1.35,boxstyle='round,pad=.1,rounding_size=.12',facecolor='#dbeafe',edgecolor='#34699a',lw=1.4)
    ax.add_patch(gridbox);ax.text(7,1.55,'电网侧准稳态级联 + 频率/UFLS + 受限再调度',ha='center',weight='bold',fontsize=10);ax.text(7,1.05,'更新幸存机组 Pg(t)；按其实际出力继续推进冷端状态',ha='center',fontsize=9)
    # Protection trip initiates a grid event; redispatch feeds back to cooling duty.
    ax.annotate('',xy=(9.55,2.02),xytext=(12.05,3.62),arrowprops=dict(arrowstyle='->',lw=1.7,color='#d1495b',connectionstyle='arc3,rad=-.08'))
    ax.text(11.3,2.78,'保护跳机 → 网侧事件',ha='center',color='#a62f45',weight='bold',fontsize=8)
    ax.annotate('',xy=(9.0,3.62),xytext=(8.45,2.02),arrowprops=dict(arrowstyle='->',lw=1.7,color='#34699a',connectionstyle='arc3,rad=.08'))
    ax.text(7.45,2.65,'Pg(t)反馈',ha='center',color='#275982',weight='bold',fontsize=8)
    ax.text(7,.12,'分析边界：冷端与频率按时间推进；AC电压/线路级联在事件断面求解，并非全状态暂态联合仿真。',ha='center',fontsize=8,color='#475467')
    ax.set_title('冷端补水中断—机组跳闸—电网级联的反馈链',loc='left',pad=8,weight='bold')
    savefig(fig,'fig01_coupling_mechanism')

def fig02_p5_levels():
    anchors={r['unit']:r for r in read_csv(ROOT/'data/coldend/unit_anchors.csv')}
    seq={r['unit']:r for r in read_csv(ROOT/'results/reference/coldend_p5/trip_sequence.csv')}
    fig,ax=plt.subplots(figsize=(10.8,6.2))
    for u in UNITS:
        rr=read_csv(ROOT/f'results/reference/coldend_p5/unit_series/{u}.csv')
        c=KCOL['K'+str(1+UNITS.index(u)%6)]
        normal=float(anchors[u]['level_normal_m']);trip=float(anchors[u]['level_trip_m'])
        x=[float(r['t_h']) for r in rr]
        y=[(float(r['basin_level_m'])-trip)/(normal-trip) for r in rr]
        ax.plot(x,y,lw=2,label=f"{u}（跳机 {float(seq[u]['t_trip_h']):.2f} h）",color=c)
        ax.scatter([x[-1]],[y[-1]],s=28,color=c,zorder=4)
    ax.axhline(0,color='#b42318',lw=1.4,ls='--',label='低水位保护阈值（归一化 0）')
    ax.set(xlabel='P5 固定出力参考：断水后时间（h）',ylabel='剩余水位裕度（归一化）',ylim=(-.08,1.08))
    ax.set_xlim(left=0)
    ax.set_title('P5：六机同时断水、固定故障前出力时的水池裕度轨迹',loc='left',weight='bold')
    ax.grid(axis='y',alpha=.22);ax.legend(ncol=2,frameon=False,loc='upper right')
    ax.text(.01,-.22,'注：每条轨迹在本机保护跳闸处终止；归一化仅便于比较各机不同正常/跳闸水位，不改变模型物理量。',transform=ax.transAxes,fontsize=8,color='#475467')
    savefig(fig,'fig02_p5_basin_margin')

def fig03_p5_triptime():
    seq=read_csv(ROOT/'results/reference/coldend_p5/trip_sequence.csv')
    seq=sorted(seq,key=lambda r:float(r['t_trip_h']))
    y=np.arange(len(seq));units=[r['unit'] for r in seq]
    times=[float(r['t_trip_h']) for r in seq]
    fig,ax=plt.subplots(figsize=(10.5,5.8))
    cols=['#168aad' for u in units]
    bars=ax.barh(y,times,color=cols,alpha=.86,height=.62)
    ax.set_yticks(y,units);ax.invert_yaxis();ax.set_xlabel('断水至低水位保护跳机时间（h）')
    ax.set_title('P5：机组冷端耐受时间与初始运行条件',loc='left',weight='bold')
    ax.grid(axis='x',alpha=.2)
    for i,(b,r) in enumerate(zip(bars,seq)):
        ax.text(b.get_width()+.15,i,f"{float(r['t_trip_h']):.2f} h   |   Pg0 {float(r['pg0_mw']):.1f} MW   |   可用池容 {float(r['basin_usable_m3']):.0f} m³",va='center',fontsize=8)
    ax.set_xlim(0,max(times)*1.67)
    ax.text(.01,-.14,'排序是当前锚点与固定 P0 假设下的模型结果；参数属于参考假设，不是现场校准值。',transform=ax.transAxes,fontsize=8,color='#475467')
    savefig(fig,'fig03_p5_trip_time')

def fig10_p5_thermodynamics():
    """P5 fixed-output reference: expose water, heat-transfer and condenser state jointly."""
    fig,axs=plt.subplots(3,2,figsize=(14,10),sharex=False)
    axs=axs.ravel()
    series={u:read_csv(ROOT/f'results/reference/coldend_p5/unit_series/{u}.csv') for u in UNITS}
    specs=[('basin_level_m','池水水位 (m)'),('qcw_frac','循环冷却水流量比例'),
           ('backpressure_kpa','凝汽器背压 (kPa)'),('t_sat_c','凝汽饱和温度 (°C)'),
           ('tout_c','冷却水出口温度 (°C)'),('heat_reject_mw_th','排热量 (MWth)')]
    for ax,(key,label) in zip(axs,specs):
        for u in UNITS:
            rr=series[u];x=[float(r['t_h']) for r in rr]
            y=[float(r[key]) for r in rr]
            ax.plot(x,y,color=UCOL[u],lw=1.65,label=u)
            ax.scatter([x[-1]],[y[-1]],color=UCOL[u],s=19,zorder=4)
        ax.set_ylabel(label);ax.grid(alpha=.18)
        ax.set_xlabel('断水后时间 (h)')
    # Water-loss inset indicator on the sixth panel; reported separately from heat rejection.
    ax=axs[5].twinx()
    for u in UNITS:
        rr=series[u];x=[float(r['t_h']) for r in rr]
        ax.plot(x,[float(r['evaporation_m3s'])*3600 for r in rr],color=UCOL[u],lw=1.0,ls=':',alpha=.72)
    ax.set_ylabel('蒸发量 (m³/h)',color='#526173')
    handles=[Line2D([0],[0],color=UCOL[u],lw=2,label=u) for u in UNITS]
    handles += [Line2D([0],[0],color='#526173',lw=1.5,ls='-',label='实线：主图变量'),
                Line2D([0],[0],color='#526173',lw=1.5,ls=':',label='点线：蒸发量（右轴）')]
    fig.legend(handles=handles,loc='upper center',ncol=8,frameon=False,bbox_to_anchor=(.5,.985),fontsize=8)
    fig.suptitle('P5 固定出力参考：断水后的冷端状态与热力变量',x=.07,ha='left',weight='bold',fontsize=14,y=1.02)
    fig.text(.07,.005,'颜色按机组；每条轨迹止于该机低水位保护跳闸。P5是固定P0参考：水池/流量变化驱动背压与饱和温度、冷却水温及排热变化；非耦合K1–K6出力结果。',fontsize=8,color='#475467')
    fig.tight_layout(rect=(0,.035,1,.95),h_pad=1.3,w_pad=1.2)
    savefig(fig,'fig10_p5_coldend_thermodynamics')

def fig04_k2_feedback():
    units=['G1','G2']; anchors={r['unit']:r for r in read_csv(ROOT/'data/coldend/unit_anchors.csv')}
    cool=read_csv(ROOT/'results/K2/scenarios/K2-G1-G2/cooling_demand_response.csv')
    disp=read_csv(ROOT/'results/K2/scenarios/K2-G1-G2/dispatch_trajectory.csv')
    sumrow=read_csv(ROOT/'results/K2/tables/pairwise_summary.csv')
    case=next(r for r in sumrow if r['scenario_id']=='K2-G1-G2')
    events=[]
    for field,pat,scale in [('initial_trip_events',r'([^@;]+)@([0-9.]+)h',1),
                            ('other_coldend_trip_events',r'([^@;]+)@([0-9.]+)s',1/3600)]:
        for unit,t in re.findall(pat,case.get(field,'')):
            events.append((unit,float(t)*scale))
    trip_g2=next((t for u,t in events if u=='G2'),float(case['initial_trip_h']))
    trip_g1=next((t for u,t in events if u=='G1'),9.7383)
    fig,axs=plt.subplots(5,1,figsize=(11,12),sharex=True,gridspec_kw={'height_ratios':[1,1,1.1,1.1,1]})
    # normalized basin margin
    for u in units:
        rr=[r for r in cool if r['unit']==u]
        a=anchors[u];norm=float(a['level_normal_m']);thr=float(a['level_trip_m'])
        x=[float(r['system_t_h']) for r in rr]
        y=[(float(r['basin_level_m'])-thr)/(norm-thr) for r in rr]
        axs[0].plot(x,y,label=u,color=UCOL[u],lw=1.8)
    axs[0].axhline(0,color='#b42318',ls='--',lw=1,label='低水位保护阈值')
    axs[0].set_ylabel('水位裕度\n(归一化)');axs[0].legend(frameon=False,ncol=3,loc='upper right');axs[0].grid(alpha=.18)
    # Pg traces
    x=[float(r['system_t_h']) for r in disp]
    for key,u in [('pg_bus1_mw','G1'),('pg_bus2_mw','G2')]:
        axs[1].plot(x,[float(r[key]) for r in disp],label=u,color=UCOL[u],lw=1.8)
    axs[1].set_ylabel('机组 Pg (MW)');axs[1].legend(frameon=False,ncol=2,loc='upper right');axs[1].grid(alpha=.18)
    # condenser backpressure and thermal capability
    capax=axs[2].twinx()
    for u in units:
        rr=[r for r in cool if r['unit']==u];xx=[float(r['system_t_h']) for r in rr]
        axs[2].plot(xx,[float(r['backpressure_kpa']) for r in rr],color=UCOL[u],lw=1.8,label=f'{u} 背压')
        capax.plot(xx,[float(r['thermal_cap_mw']) for r in rr],color=UCOL[u],lw=1.2,ls='--',alpha=.85,label=f'{u} 热力能力')
    axs[2].set_ylabel('背压 (kPa)');capax.set_ylabel('热力能力 (MW)')
    h1,l1=axs[2].get_legend_handles_labels();h2,l2=capax.get_legend_handles_labels()
    axs[2].legend(h1+h2,l1+l2,frameon=False,ncol=2,loc='upper left',fontsize=7);axs[2].grid(alpha=.18)
    # water demand, supply, and evaporation connect output to water balance
    for u in units:
        rr=[r for r in cool if r['unit']==u];xx=[float(r['system_t_h']) for r in rr]
        axs[3].plot(xx,[float(r['makeup_required_m3h']) for r in rr],color=UCOL[u],lw=1.6,label=f'{u} 需补水')
        axs[3].plot(xx,[float(r['makeup_supply_m3h']) for r in rr],color=UCOL[u],lw=1.1,ls='--',label=f'{u} 实际补水')
    axs[3].set_ylabel('补水流量 (m³/h)');axs[3].legend(frameon=False,ncol=2,loc='upper left',fontsize=7);axs[3].grid(alpha=.18)
    # grid response at the same system-time axis
    fx=[float(r['system_t_h']) for r in disp];fy=[float(r['frequency_hz']) for r in disp]
    axs[4].plot(fx,fy,color='#344054',lw=1.35)
    axs[4].scatter(fx,fy,c=[float(r['ufls_stage']) for r in disp],cmap='Oranges',s=8,zorder=3)
    axs[4].axhline(59.3,color='#b42318',ls='--',lw=1,label='UFLS 第一档 59.30 Hz')
    axs[4].set_ylabel('频率 (Hz)');axs[4].set_xlabel('相对同时断水时刻的系统时间（h）');axs[4].legend(frameon=False,loc='lower right',fontsize=7);axs[4].grid(alpha=.18)
    for ax in axs:
        ax.axvline(trip_g2,color=UCOL['G2'],ls=':',lw=1.2)
        ax.axvline(trip_g1,color=UCOL['G1'],ls='--',lw=1.2)
    axs[0].text(trip_g2,1.02,'G2跳闸',rotation=90,va='bottom',ha='right',fontsize=8,color=UCOL['G2'])
    axs[0].text(trip_g1,1.02,'G1跳闸',rotation=90,va='bottom',ha='right',fontsize=8,color=UCOL['G1'])
    axs[-1].set_xlim(0,max(trip_g1+.5,10))
    fig.suptitle('K2-G1-G2：冷端热力状态、机组出力与电网响应同步变化',x=.08,ha='left',weight='bold',fontsize=13)
    fig.text(.08,.005,'断水同时发生于 t=0。背压、热力能力、需补水/实补水和频率置于同一系统时间轴；竖线为G2、G1冷端跳闸。情景为确定性模型，不代表概率。',fontsize=8,color='#475467')
    fig.tight_layout(rect=(0,.03,1,.96),h_pad=.55)
    savefig(fig,'fig04_k2_g1_g2_feedback')

def fig05_k1():
    rows=[r for r in MASTER if r['K']=='K1'];rows.sort(key=lambda r:UNITS.index(r['units']))
    ys=np.arange(len(rows)); labels=[r['units'] for r in rows]
    fig,axs=plt.subplots(1,3,figsize=(13,5.5),sharey=True,gridspec_kw={'width_ratios':[1.15,1,1.05]})
    for ax in axs: ax.set_yticks(ys,labels);ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
    colors=[NCLASS[r['N_class']] for r in rows]
    axs[0].barh(ys,[r['initial_trip_h'] for r in rows],color=colors,height=.6)
    axs[0].set_xlabel('首台冷端跳闸 (h)');axs[0].set_title('冷端')
    for i,r in enumerate(rows):axs[0].text(r['initial_trip_h']+.15,i,f"{r['initial_trip_h']:.2f}",va='center',fontsize=7)
    axs[1].scatter([r['f_nadir_hz'] for r in rows],ys,c=colors,s=45,edgecolor='white',lw=.6,zorder=3)
    axs[1].axvline(59.3,color='#b42318',ls='--',lw=1,label='UFLS第一档 59.30 Hz')
    axs[1].set_xlabel('频率最低点 (Hz)');axs[1].set_title('频率');axs[1].legend(frameon=False,fontsize=7,loc='lower right')
    axs[2].barh(ys,[r['total_shed_mw'] for r in rows],color=colors,height=.6)
    axs[2].set_xlabel('累计切负荷 (MW)');axs[2].set_title('电网响应')
    for i,r in enumerate(rows):axs[2].text(r['total_shed_mw']+.2,i,f"{r['total_shed_mw']:.1f} | H={r['H_hard_buses']}",va='center',fontsize=7)
    handles=[patches.Patch(color=NCLASS[n],label=n) for n in ['N0','N3']]
    fig.legend(handles=handles,loc='lower center',ncol=4,frameon=False,bbox_to_anchor=(.5,-.02))
    fig.suptitle('K1 六个独立单机补水中断：冷端时间与网侧结果',x=.08,ha='left',weight='bold',fontsize=13)
    fig.text(.08,.035,'六案最终 H=0；类别 N0/N3 是运行状态标签，不代表硬失供。来源使用完整六案比较表。',fontsize=8,color='#475467')
    fig.tight_layout(rect=(0,.08,1,.93))
    savefig(fig,'fig05_k1_six_units')

def fig06_all_cases():
    rows=MASTER
    n=len(rows); fig,axs=plt.subplots(1,2,figsize=(16,17),gridspec_kw={'width_ratios':[1.15,1]})
    y=np.arange(n)
    # hard-bus horizontal bars
    ax=axs[0]
    for i,r in enumerate(rows):
        c=KCOL[r['K']]
        ax.barh(i,r['H_hard_buses'],color=('#c53030' if r['H_hard_buses']>0 else '#cbd5e1'),height=.72,edgecolor=c,lw=.65)
        if r['H_hard_buses']>0: ax.text(r['H_hard_buses']+.2,i,str(r['H_hard_buses']),va='center',fontsize=5.5)
    ax.set_yticks(y,[f"{r['K']}  {r['units'].replace('+','–')}"+(' †' if r['censored_units'] else '') for r in rows],fontsize=5.5)
    ax.invert_yaxis();ax.set_xlim(0,34);ax.set_xlabel('H：硬失供母线数');ax.set_title('情景级硬失供 H',loc='left',weight='bold');ax.grid(axis='x',alpha=.16)
    # nadir point, colored group; filled if UFLS
    ax=axs[1]
    for i,r in enumerate(rows):
        marker='D' if r['censored_units'] else 'o'
        face=KCOL[r['K']] if r['ufls_triggered'] else 'white'
        ax.scatter(r['f_nadir_hz'],i,s=22,marker=marker,facecolor=face,edgecolor=KCOL[r['K']],linewidth=.8,zorder=3)
    ax.axvline(59.3,color='#b42318',ls='--',lw=1,label='59.30 Hz UFLS第一档')
    ax.set_yticks(y,[]);ax.invert_yaxis();ax.set_xlim(57.5,60.1);ax.set_xlabel('频率最低点 (Hz)');ax.set_title('频率最低点（实心=UFLS；菱形=提前截断）',loc='left',weight='bold');ax.grid(axis='x',alpha=.16);ax.legend(frameon=False,fontsize=7,loc='lower right')
    bounds=[];start=0
    for k in [f'K{i}' for i in range(1,7)]:
        cnt=sum(r['K']==k for r in rows)
        if cnt:
            if start: 
                for a in axs:a.axhline(start-.5,color='#64748b',lw=.9)
            mid=start+(cnt-1)/2
            ax.text(1.015,mid,k,transform=ax.get_yaxis_transform(),va='center',weight='bold',color=KCOL[k])
            start+=cnt
    fig.suptitle('K1–K6 全部 63 案：硬失供、频率与提前停止总览',x=.06,ha='left',weight='bold',fontsize=14)
    fig.text(.06,.015,'† 表示至少一台被选机组在硬服务损失端点前未跳闸（删失）。H=1[F3]（仅无源失电）；F1/F2a/F2b 为过程量，不替代 H。',fontsize=8,color='#475467')
    fig.tight_layout(rect=(0,.04,.98,.96))
    savefig(fig,'fig06_all_scenario_map')

def fig07_by_k():
    ks=[f'K{i}' for i in range(1,7)]
    fig,axs=plt.subplots(1,2,figsize=(13,5.6))
    metrics=[('H_hard_buses','硬失供母线数 H'),('total_shed_mw','累计切负荷 (MW)')]
    for ax,(metric,title) in zip(axs,metrics):
        for x,k in enumerate(ks):
            vals=[r[metric] for r in MASTER if r['K']==k]
            jitter=np.linspace(-.12,.12,len(vals)) if len(vals)>1 else [0]
            ax.scatter([x+j for j in jitter],vals,color=KCOL[k],s=24,alpha=.75,zorder=3)
            if vals:
                ax.vlines(x,min(vals),max(vals),color=KCOL[k],lw=2,alpha=.55)
                ax.scatter([x],[np.median(vals)],marker='_',s=140,color='#111827',lw=2,zorder=4)
                ax.text(x,max(vals)+(.7 if metric.startswith('H') else 5),f"n={len(vals)}",ha='center',fontsize=7,color=KCOL[k])
        ax.set_xticks(range(6),ks);ax.set_title(title,loc='left',weight='bold');ax.grid(axis='y',alpha=.18)
    axs[0].set_ylabel('母线数（0–30）');axs[0].set_ylim(-1,34)
    axs[1].set_ylabel('MW');axs[1].set_ylim(bottom=0)
    fig.suptitle('按同时断水机组数分组的全部枚举结果',x=.08,ha='left',weight='bold',fontsize=13)
    fig.text(.08,.015,'点=单个情景；竖线=本层级最小–最大；短横线=中位数。每组都是确定性穷举集，比例/统计量不代表概率风险。',fontsize=8,color='#475467')
    fig.tight_layout(rect=(0,.06,1,.92))
    savefig(fig,'fig07_outcomes_by_cardinality')

def fig08_h_frequency():
    fig,ax=plt.subplots(figsize=(10.4,6.7))
    overlap=Counter((round(r['f_nadir_hz'],5),r['H_hard_buses']) for r in MASTER)
    for r in MASTER:
        size=22+0.48*max(0,r['total_shed_mw'])
        marker='D' if r['censored_units'] else 'o'
        face=KCOL[r['K']] if r['ufls_triggered'] else 'white'
        ax.scatter(r['f_nadir_hz'],r['H_hard_buses'],s=size,marker=marker,facecolor=face,edgecolor=KCOL[r['K']],lw=1.0,alpha=.82)
    for (fx,hy),count in overlap.items():
        if hy>0 and count>1:
            ax.annotate(f'×{count} 重合案',(fx,hy),xytext=(8,8),textcoords='offset points',fontsize=7,color='#344054')
    ax.axvline(59.3,color='#b42318',ls='--',lw=1,label='UFLS 第一档 59.30 Hz')
    ax.set_xlabel('频率最低点 (Hz)');ax.set_ylabel('硬失供母线数 H');ax.set_xlim(57.5,60.1);ax.set_ylim(-1,32);ax.grid(alpha=.2)
    ax.set_title('频率最低点与硬失供并非同一指标',loc='left',weight='bold')
    handles=[Line2D([0],[0],marker='o',color='none',markerfacecolor=KCOL[k],markeredgecolor=KCOL[k],label=k,markersize=7) for k in KCOL]
    handles += [Line2D([0],[0],marker='o',color='none',markerfacecolor='white',markeredgecolor='#475467',label='无UFLS',markersize=7),Line2D([0],[0],marker='D',color='none',markerfacecolor='white',markeredgecolor='#475467',label='删失情景',markersize=7)]
    ax.legend(handles=handles,frameon=False,ncol=4,loc='upper right',fontsize=8)
    ax.text(.01,-.17,'气泡大小随累计切负荷变化，仅作视觉编码；并非EENS。K6只有一个组合，不能据此估计发生概率。',transform=ax.transAxes,fontsize=8,color='#475467')
    savefig(fig,'fig08_frequency_vs_hard_loss')

def fig09_bus_incidence():
    cases=[r for r in MASTER if r['H_hard_buses']>0]
    buses=list(range(1,31));mat=np.zeros((len(cases),30),dtype=int)
    for i,r in enumerate(cases):
        hs={int(b) for b in r['hard_failure_buses'].split(';') if b}
        for b in hs:mat[i,b-1]=1
    fig,ax=plt.subplots(figsize=(14,8))
    ax.imshow(mat,aspect='auto',interpolation='nearest',cmap=matplotlib.colors.ListedColormap(['#f1f5f9','#c53030']),vmin=0,vmax=1)
    ax.set_xticks(np.arange(30),buses);ax.set_xlabel('IEEE30 母线编号');ax.set_yticks(np.arange(len(cases)),[f"{r['K']} {r['units'].replace('+','–')} (H={r['H_hard_buses']})" for r in cases],fontsize=7)
    ax.set_title('出现硬失供情景的母线端点矩阵（红色=该案母线 H=1）',loc='left',weight='bold')
    # group boundaries
    prev=None
    for i,r in enumerate(cases):
        if prev is not None and r['K']!=prev:ax.axhline(i-.5,color='#334155',lw=1.2)
        prev=r['K']
    ax.set_xticks(np.arange(-.5,30,1),minor=True);ax.grid(which='minor',axis='x',color='white',lw=.35);ax.tick_params(which='minor',bottom=False)
    fig.text(.08,.015,'硬失供定义 H=1[F3]（仅无源失电）；事件矩阵不把一般 F1 越限、F2a严重低压、F2b数值端点或负荷削减标为硬失供。',fontsize=8,color='#475467')
    fig.tight_layout(rect=(0,.04,1,1))
    savefig(fig,'fig09_hard_bus_incidence')

def build_mechanism_metrics():
    """Long-form selected-unit cold-end indicators and case endpoints for K2-K6."""
    anchors={r['unit']:r for r in read_csv(ROOT/'data/coldend/unit_anchors.csv')}
    cases=[]
    for r in MASTER:
        if r['K']=='K1':
            continue  # K1 is seeded from the fixed-output P5 trip reference, not a coupled cooling trajectory.
        cases.append({**r,'endpoint_type':'first_H_or_observed_window'})
    cont_path=ROOT/'results/K6/continuation/tables/six_unit_summary.csv'
    if cont_path.exists():
        cr=read_csv(cont_path)[0]
        trip=set(parse_units(cr.get('initial_trip_units','')))
        trip.update(e.split('@',1)[0] for e in cr.get('other_coldend_trip_events','').split(';') if e)
        cases.append({'K':'K6','scenario_id':cr['scenario_id'],'units':cr['initial_makeup_failure_units'].replace(';','+'),
            'actual_trip_units':';'.join(sorted(trip)),'censored_units':cr.get('faulted_units_not_tripped_before_stop',''),
            'H_hard_buses':int(fnum(cr,'n_bus_hard_failure')),'total_shed_mw':fnum(cr,'total_shed_mw'),
            'endpoint_type':'full_continuation'})
    unit_rows=[];case_rows=[]
    for case in cases:
        k=case['K'];sid=case['scenario_id']
        sub=ROOT/'results'/k/'scenarios'/sid/'cooling_demand_response.csv'
        if case['endpoint_type']=='full_continuation':
            sub=ROOT/'results/K6/continuation/scenarios'/sid/'cooling_demand_response.csv'
        if not sub.exists():
            continue
        rows=read_csv(sub); actual=set(parse_units(case.get('actual_trip_units','')))
        selected=[]
        for u in case['units'].split('+'):
            rr=[x for x in rows if x.get('unit')==u]
            if not rr: continue
            def vals(key):
                out=[]
                for x in rr:
                    try:
                        v=float(x.get(key,''))
                        if math.isfinite(v):out.append(v)
                    except (TypeError,ValueError):pass
                return out
            base={key:next((float(x[key]) for x in rr if x.get(key,'') not in ('',None)),float('nan'))
                  for key in ['backpressure_kpa','thermal_cap_mw','heat_reject_mw_th','evaporation_m3h','makeup_required_m3h']}
            bp=vals('backpressure_kpa');cap=vals('thermal_cap_mw');heat=vals('heat_reject_mw_th')
            evap=vals('evaporation_m3h');makeup=vals('makeup_required_m3h');levels=vals('basin_level_m')
            a=anchors[u];normal=float(a['level_normal_m']);trip=float(a['level_trip_m'])
            margin=min(max(0.0,(v-trip)/(normal-trip)) for v in levels) if levels else float('nan')
            item={'K':k,'scenario_id':sid,'unit':u,'endpoint_type':case['endpoint_type'],
                'trip_observed':int(u in actual),'selected_unit_censored':int(u not in actual),
                'max_backpressure_rise_kpa':max(bp)-base['backpressure_kpa'] if bp and math.isfinite(base['backpressure_kpa']) else float('nan'),
                'min_basin_margin_norm':margin,
                'min_thermal_cap_ratio':min(cap)/base['thermal_cap_mw'] if cap and base['thermal_cap_mw']>0 else float('nan'),
                'max_heat_reject_ratio':max(heat)/base['heat_reject_mw_th'] if heat and base['heat_reject_mw_th']>0 else float('nan'),
                'max_evaporation_ratio':max(evap)/base['evaporation_m3h'] if evap and base['evaporation_m3h']>0 else float('nan'),
                'max_makeup_required_ratio':max(makeup)/base['makeup_required_m3h'] if makeup and base['makeup_required_m3h']>0 else float('nan')}
            unit_rows.append(item);selected.append(item)
        if selected:
            def finite_min(key):
                v=[x[key] for x in selected if math.isfinite(x[key])]
                return min(v) if v else float('nan')
            def finite_max(key):
                v=[x[key] for x in selected if math.isfinite(x[key])]
                return max(v) if v else float('nan')
            case_rows.append({'K':k,'scenario_id':sid,'endpoint_type':case['endpoint_type'],
                'H_hard_buses':case['H_hard_buses'],'total_shed_mw':case['total_shed_mw'],
                'censored_units':case.get('censored_units',''),
                'max_backpressure_rise_kpa':finite_max('max_backpressure_rise_kpa'),
                'min_basin_margin_norm':finite_min('min_basin_margin_norm'),
                'min_thermal_cap_ratio':finite_min('min_thermal_cap_ratio'),
                'max_heat_reject_ratio':finite_max('max_heat_reject_ratio'),
                'max_evaporation_ratio':finite_max('max_evaporation_ratio'),
                'max_makeup_required_ratio':finite_max('max_makeup_required_ratio')})
    for name,rows in [('mechanism_unit_master.csv',unit_rows),('mechanism_case_summary.csv',case_rows)]:
        if rows:
            with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return unit_rows,case_rows

def fig11_mechanism_vs_grid(case_rows):
    fig,axs=plt.subplots(2,2,figsize=(13,9));axs=axs.ravel()
    specs=[('max_backpressure_rise_kpa','最大背压增量 (kPa)'),
           ('max_makeup_required_ratio','最大需补水量 / 初始值'),
           ('min_thermal_cap_ratio','最小热力能力 / 初始值'),
           ('max_heat_reject_ratio','最大排热量 / 初始值')]
    for ax,(metric,label) in zip(axs,specs):
        for r in case_rows:
            k=r['K'];x=r[metric]
            if not math.isfinite(x):continue
            cont=r['endpoint_type']=='full_continuation'
            marker='*' if cont else ('D' if r['censored_units'] else 'o')
            size=65 if cont else 22+0.35*max(0,r['total_shed_mw'])
            ax.scatter(x,r['H_hard_buses'],s=size,marker=marker,color=KCOL[k],
                       edgecolor='#111827' if cont else 'white',linewidth=.7,alpha=.9,zorder=3)
        ax.set_xlabel(label);ax.set_ylabel('H：硬失供母线数');ax.set_ylim(-1,32);ax.set_yticks([0,5,10,15,20,25,30]);ax.grid(alpha=.18)
    handles=[Line2D([0],[0],marker='o',color='none',markerfacecolor=KCOL[k],markeredgecolor=KCOL[k],label=k,markersize=7) for k in ['K2','K3','K4','K5','K6']]
    handles += [Line2D([0],[0],marker='D',color='none',markerfacecolor='#94a3b8',markeredgecolor='#475569',label='所选机组存在删失',markersize=7),
                Line2D([0],[0],marker='*',color='none',markerfacecolor=KCOL['K6'],markeredgecolor='#111827',label='K6 延续至六机全跳',markersize=12)]
    fig.legend(handles=handles,ncol=7,loc='upper center',frameon=False,bbox_to_anchor=(.5,.99),fontsize=8)
    fig.suptitle('冷端变化与网侧硬失供端点：K2–K6已观测轨迹',x=.06,ha='left',weight='bold',fontsize=14,y=1.035)
    fig.text(.06,.005,'每个基础点是一案（气泡面积随总切负荷变化）；度量仅针对被选断水机组，截断案只统计已观测窗口。K1采用P5固定出力跳闸参考，未混入耦合冷端轨迹。K6星号为独立延续结果；点/比例不是概率。',fontsize=8,color='#475467')
    fig.tight_layout(rect=(0,.04,1,.94),h_pad=1.4,w_pad=1.25)
    savefig(fig,'fig11_coldend_metrics_vs_grid')

def fig12_k6_continuation():
    sid='K6-G1-G2-G13-G22-G23-G27'
    first=read_csv(ROOT/f'results/K6/scenarios/{sid}/cooling_demand_response.csv')
    cont=read_csv(ROOT/f'results/K6/continuation/scenarios/{sid}/cooling_demand_response.csv')
    cr=read_csv(ROOT/'results/K6/continuation/tables/six_unit_summary.csv')[0]
    first_summary=read_csv(ROOT/'results/K6/tables/six_unit_summary.csv')[0]
    anchors={r['unit']:r for r in read_csv(ROOT/'data/coldend/unit_anchors.csv')}
    trips=[]
    for unit,t in re.findall(r'([^@;]+)@([0-9.]+)h',cr.get('initial_trip_events','')):
        trips.append((unit,float(t)))
    for unit,t in re.findall(r'([^@;]+)@([0-9.]+)s',cr.get('other_coldend_trip_events','')):
        trips.append((unit,float(t)/3600))
    first_events=[]
    for _,t in re.findall(r'([^@;]+)@([0-9.]+)h',first_summary.get('initial_trip_events','')):
        first_events.append(float(t))
    for _,t in re.findall(r'([^@;]+)@([0-9.]+)s',first_summary.get('other_coldend_trip_events','')):
        first_events.append(float(t)/3600)
    first_h=max(first_events)
    disp=read_csv(ROOT/f'results/K6/continuation/scenarios/{sid}/dispatch_trajectory.csv')
    fig,axs=plt.subplots(4,1,figsize=(12,11),sharex=True,gridspec_kw={'height_ratios':[1.05,1,1,1]})
    for u in UNITS:
        rr=[r for r in cont if r['unit']==u]
        x=[float(r['system_t_h']) for r in rr]
        normal=float(anchors[u]['level_normal_m']);thr=float(anchors[u]['level_trip_m'])
        margin=[(float(r['basin_level_m'])-thr)/(normal-thr) if r.get('basin_level_m') else float('nan') for r in rr]
        axs[0].plot(x,margin,color=UCOL[u],lw=1.7,label=u)
        bp_x=[];bp_y=[]
        for r in rr:
            try: bp_x.append(float(r['system_t_h']));bp_y.append(float(r['backpressure_kpa']))
            except (TypeError,ValueError):pass
        axs[1].plot(bp_x,bp_y,color=UCOL[u],lw=1.6)
        pg_x=[];pg_y=[]
        for r in rr:
            try:pg_x.append(float(r['system_t_h']));pg_y.append(float(r['pg_command_mw']))
            except (TypeError,ValueError):pass
        axs[2].plot(pg_x,pg_y,color=UCOL[u],lw=1.5)
        if rr and rr[-1].get('status')=='coldend_trip' and pg_y:
            axs[2].scatter([pg_x[-1]],[pg_y[-1]],color=UCOL[u],marker='x',s=28,zorder=5)
    axs[0].axhline(0,color='#b42318',ls='--',lw=1,label='低水位跳闸阈值')
    axs[0].set_ylabel('水位裕度\n(归一化)');axs[0].legend(ncol=7,frameon=False,loc='upper right',fontsize=7);axs[0].grid(alpha=.18)
    axs[1].set_ylabel('凝汽器背压 (kPa)');axs[1].grid(alpha=.18)
    dx=[0.0]+[float(r['system_t_h']) for r in disp]
    dy=[60.0]+[float(r['frequency_hz']) for r in disp]
    axs[2].set_ylabel('Pg命令（跳闸前，MW）');axs[2].grid(alpha=.18)
    axs[3].plot(dx,dy,color='#344054',lw=1.2)
    stage=[0.0]+[float(r['ufls_stage']) for r in disp]
    axs[3].scatter(dx,dy,c=stage,cmap='Oranges',s=7,zorder=3)
    axs[3].axhline(59.3,color='#b42318',ls='--',lw=1,label='UFLS 第一档 59.30 Hz')
    axs[3].set_ylabel('频率 (Hz)');axs[3].set_xlabel('六机同时断水后的系统时间（h）');axs[3].legend(frameon=False,loc='lower right',fontsize=7);axs[3].grid(alpha=.18)
    for ax in axs: ax.axvline(first_h,color='#6b7280',ls=':',lw=1.5)
    for u,t in trips:
        for ax in axs: ax.axvline(t,color=UCOL[u],ls='--',lw=.65,alpha=.28)
        axs[0].text(t,1.03,u,rotation=90,va='bottom',ha='right',fontsize=7,color=UCOL[u])
    axs[0].text(first_h,0.78,'原 first-H 停止\nG22跳闸 / H=2',ha='right',va='top',fontsize=8,color='#475467',bbox=dict(fc='white',ec='#cbd5e1',alpha=.9))
    axs[-1].set_xlim(0,max(t for _,t in trips)+.5)
    fig.suptitle('K6 独立延续：首个 H 端点之后继续追踪冷端—频率响应',x=.07,ha='left',weight='bold',fontsize=14)
    fig.text(.07,.005,'六机断水仍同时始于 t=0。首个H结果保留在 results/K6/；本延续单独写入 results/K6/continuation/。六台目标机组最终均冷端跳闸，模型端点 H=30、F3=30；运行出现 PYPOWER 奇异矩阵/除零警告，因此这是带数值警告的模型端点，不等同于独立验证的现场 blackout。',fontsize=8,color='#475467')
    fig.tight_layout(rect=(0,.04,1,.95),h_pad=.8)
    savefig(fig,'fig12_k6_full_continuation')

def build_summary(rows):
    out=[]
    for k in [f'K{i}' for i in range(1,7)]:
        rr=[r for r in rows if r['K']==k]
        if not rr:continue
        cls=Counter(r['N_class'] for r in rr)
        h=[r['H_hard_buses'] for r in rr]
        out.append({'K':k,'cases':len(rr),'H_positive':sum(x>0 for x in h),'tested_share':sum(x>0 for x in h)/len(rr),'H_max':max(h),'H_median':float(np.median(h)),'UFLS_cases':sum(r['ufls_triggered'] for r in rr),'censored_cases':sum(bool(r['censored_units']) for r in rr),'N0':cls['N0'],'N1':cls['N1'],'N2':cls['N2'],'N3':cls['N3'],'freq_min':min(r['f_nadir_hz'] for r in rr),'freq_max':max(r['f_nadir_hz'] for r in rr),'total_shed_min':min(r['total_shed_mw'] for r in rr),'total_shed_max':max(r['total_shed_mw'] for r in rr)})
    with (OUT/'group_summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    return out

def embed(path):
    b64=base64.b64encode(Path(path).read_bytes()).decode('ascii')
    return f'data:image/png;base64,{b64}'

def make_html(rows,groups,figure_captions, audit):
    p5seq=read_csv(ROOT/'results/reference/coldend_p5/trip_sequence.csv')
    p5_order=' → '.join(f"{r['unit']} ({float(r['t_trip_h']):.4f} h)" for r in p5seq)
    rows_html=''.join(f"<tr><td>{g['K']}</td><td>{g['cases']}</td><td>{g['H_positive']}/{g['cases']} ({g['tested_share']:.0%})</td><td>{g['H_max']}</td><td>{g['UFLS_cases']}/{g['cases']}</td><td>{g['N0']}/{g['N1']}/{g['N2']}/{g['N3']}</td><td>{g['censored_cases']}</td><td>{g['freq_min']:.3f}–{g['freq_max']:.3f}</td></tr>" for g in groups)
    image_blocks=[]
    for name,title,cap in figure_captions:
        image_blocks.append(f'<section class="figure"><h3>{html.escape(title)}</h3><img alt="{html.escape(title)}" src="{embed(FIG/(name+".png"))}"><p>{html.escape(cap)} <a href="figures/{name}.svg">查看矢量图</a></p></section>')
    # concise case table, full long-form available separately
    tr=[]
    for r in rows:
        flag='†' if r['censored_units'] else ''
        details=html.escape(r['trip_order'] or '没有追加跳闸事件记录')
        tr.append(f"<tr><td>{r['K']}</td><td>{html.escape(r['units'])}{flag}</td><td>{r['N_class']}</td><td>{r['initial_trip_h']:.4f}</td><td>{r['H_hard_buses']}</td><td>{r['f_nadir_hz']:.3f}</td><td>{r['ufls_shed_mw']:.2f}</td><td>{r['total_shed_mw']:.2f}</td><td>{r['trip_count_before_stop']}/{r['unit_count']}</td><td>{html.escape(r['censored_units'] or '—')}</td><td><details><summary>查看顺序</summary>{details}</details></td></tr>")
    doc=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>K1–K6 冷端—电网结果分析</title>
<style>
:root{{--ink:#172b4d;--muted:#526173;--line:#d7dee8;--paper:#fff;--wash:#f4f7fb;--accent:#1d6f8a}}*{{box-sizing:border-box}}body{{margin:0;background:#eef2f6;color:var(--ink);font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif;line-height:1.65}}main{{max-width:1120px;margin:30px auto;background:var(--paper);padding:42px 52px;box-shadow:0 8px 30px #1f29371c}}h1{{font-size:30px;line-height:1.25;margin:0 0 10px}}h2{{font-size:22px;border-bottom:2px solid var(--line);padding-bottom:7px;margin-top:42px}}h3{{font-size:16px;margin:6px 0 10px}}p{{margin:9px 0;color:#26384d}}.deck{{color:var(--muted);font-size:15px;margin-bottom:26px}}.notice{{padding:14px 17px;border-left:4px solid #d49b26;background:#fff8e6;margin:18px 0}}.summary{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0}}.card{{background:var(--wash);border:1px solid var(--line);border-radius:10px;padding:13px 15px}}.num{{font-size:24px;font-weight:700;color:var(--accent)}}.label{{font-size:12px;color:var(--muted)}}table{{border-collapse:collapse;width:100%;font-size:13px;margin:14px 0 22px}}th,td{{padding:8px 9px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}}th{{background:#eaf0f6;color:#20354c}}.figure{{margin:25px 0 36px;padding:18px;border:1px solid var(--line);border-radius:12px;background:#fff}}.figure img{{display:block;width:100%;height:auto}}.figure p{{font-size:12px;color:var(--muted);margin:10px 0 0}}a{{color:#0b6b87}}.small{{font-size:12px;color:var(--muted)}}.method{{background:#f7f9fc;border:1px solid var(--line);padding:14px 18px;border-radius:10px}}.tag{{display:inline-block;border-radius:100px;padding:2px 9px;background:#e6f1f5;color:#14566b;font-size:12px}}footer{{border-top:1px solid var(--line);margin-top:45px;padding-top:14px;color:var(--muted);font-size:12px}}@media(max-width:760px){{main{{margin:0;padding:22px}}.summary{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><main>
<h1>冷端补水中断—电网级联结果分析</h1><p class="deck">IEEE30 基态 · 冷端 P5 固定出力参考 · K1–K6 耦合情景 · 分析与可视化报告</p>
<div class="notice"><b>研究口径：</b>所有 K1–K6 是当前参数下的确定性情景模拟，不是概率样本。P5为固定故障前出力的冷端参考，不与耦合情景混作同一结果。硬失供定义 H=1[F3]（仅无源失电）；F1/F2a/F2b 为过程量、N类别及切负荷均分别报告。</div>
<div class="summary"><div class="card"><div class="num">63</div><div class="label">K1–K6 情景数</div></div><div class="card"><div class="num">{sum(r['H_hard_buses']>0 for r in rows)}</div><div class="label">发生 H&gt;0 的已模拟情景</div></div><div class="card"><div class="num">29 → 30</div><div class="label">基线最大 H → K6 延续端点</div></div><div class="card"><div class="num">3</div><div class="label">K4/K5与K6延续数值警告批次</div></div></div>
<h2>一、层级结果概览</h2><p>“H&gt;0占比”仅表示该层级已枚举组合中的情景数比例；组合结构随 K 改变，且高阶个案可能在硬失供端点提前停止，因此不能解释为概率或单调风险曲线。</p>
<table><thead><tr><th>层级</th><th>情景数</th><th>H&gt;0（枚举集内）</th><th>最大 H</th><th>UFLS触发</th><th>N0/N3</th><th>提前截断案</th><th>频率最低点范围 (Hz)</th></tr></thead><tbody>{rows_html}</tbody></table>
<p><b>P5 固定出力参考跳机顺序：</b>{p5_order}。这条序列用于说明冷端机理与锚点差异，不当作K1–K6耦合后的跳闸时间表。</p>
<div class="method"><b>主要观察</b><ul><li>K1 六个独立单机情景最终 H 均为 0；K2 有 1/15 案 H&gt;0，K3 为 5/20，K4 为 9/15，K5 为 6/6，K6 为 1/1。该结果反映当前有限的确定性枚举集，不是事故概率。</li><li>严重度并非随同时断水机组数简单递增：原K6 first-H结果在 H=2 时停止，保持为首个硬失供、可与K1–K5比较的基线；单独延续后，G27于6.2908 h、G1于7.5778 h继续冷端跳闸，六台所选机组均已跳闸，模型端点为H=30/F3=30。此延续与63案基线分开报告，不回写替换原结果。最低频率与UFLS极值仍分别来自不同K5情景。</li><li>频率最低点、UFLS、网侧静态切负荷和 H 是不同维度。K6 first-H基线最低频率59.27305 Hz且UFLS=25.5609 MW、H=2；延续端点最低频率57.23438 Hz、UFLS=52.4877 MW、H=30。均不可仅用频率或N3替代硬失供母线口径。</li></ul></div>
<h2>二、冷端机理与耦合反馈</h2>
{image_blocks[0]}{image_blocks[1]}{image_blocks[2]}{image_blocks[3]}
<h2>三、冷端热力变量：压力、温度、排热与水量</h2>
{image_blocks[9]}{image_blocks[10]}
<h2>四、K6 first-H基线与独立延续</h2>
{image_blocks[11]}
<p><b>K6延续结果：</b>独立保存于 <code>results/K6/continuation/</code>；在first-H基线（H=2，G22于5.3592 h跳闸）之后继续运行，观测到G27于6.2908 h、G1于7.5778 h跳闸，六台选定机组全部跳闸。模型把最终母线端点标记为H=30/F3=30；出现PYPOWER奇异矩阵/除零警告，故报告为有数值警告的no-source模型端点，不把它等同于经独立收敛验证的现实 blackout。</p>
<h2>五、K1–K6 情景级对比（基线仍为63案）</h2>
{image_blocks[4]}{image_blocks[5]}{image_blocks[6]}{image_blocks[7]}{image_blocks[8]}
<h2>六、情景汇总数据（63案）</h2><p class="small">† 表示至少一台被选机组在硬服务损失停止前未跳闸。完整派生长表：<a href="scenario_master.csv">scenario_master.csv</a>；冷端机理单位级/情景级派生表：<a href="mechanism_unit_master.csv">mechanism_unit_master.csv</a>、<a href="mechanism_case_summary.csv">mechanism_case_summary.csv</a>；层级统计：<a href="group_summary.csv">group_summary.csv</a>。</p>
<div style="max-height:560px;overflow:auto;border:1px solid var(--line)"><table><thead><tr><th>K</th><th>组合</th><th>N类</th><th>首跳 (h)</th><th>H</th><th>f最低</th><th>UFLS MW</th><th>总切负荷 MW</th><th>已跳/选定</th><th>未跳（删失）</th><th>跳闸顺序</th></tr></thead><tbody>{''.join(tr)}</tbody></table></div>
<h2>七、解释边界与审计说明</h2><div class="method"><ul><li>硬失供：H=1[F3]（仅无源失电）；母线编号按IEEE30算例。切负荷为功率量，不等同于用户未供电量或EENS。</li><li>数值警告：K4首案、K5第二案及K6延续均出现 PYPOWER 奇异矩阵/除零警告。K6延续的输出端点标记为六台目标机组全跳、H=30/F3=30，且 F2b 类数值失败端点不参与 H 判据；但文件级有限值检查不能证明内部潮流迭代全程收敛。故该结果是带警告的模型 no-source/全失电端点，不应表述为已独立验证的现场 blackout；相关K4/K5大范围失供结果同样保留警告并继续诊断。</li><li>K1汇总核对：`scenario_summary.csv` 与 `six_unit_comparison.csv` 均含六台机组；审计去重后 K1 恰为 6 案，未漏 G13。</li><li>参数边界：冷端锚点、补水能力/响应及爬坡等含参考假设，不能称为现场实测或校准值。AC级联在事件断面求解，不是连续暂态联合仿真。P5固定P0参考与耦合K1–K6基态出力并非完全相同（例如G1：P5为23.54 MW，K0基态潮流为25.9738 MW），故P5用于机理参考，不将其跳机时间与耦合结果作无条件一一归因。</li><li>质量检查：K1–K6总计{len(rows)}案；数值派生列、组合数、情景状态及硬失供母线集合通过脚本核对（metric_audit.py 输出 0 不自洽项）。K2–K6总切负荷与网侧静态切负荷加UFLS的最大差异为{audit['shed_reconcile_max']:.6g} MW；K1旧表未保存静态切负荷列，其非UFLS部分按历史总切负荷口径补齐。</li></ul></div>
<footer>由 `src/analysis/build_results_report.py` 生成。图表保留 PNG 与 SVG；本报告内嵌 PNG，可离线查看。</footer></main></body></html>'''
    (OUT/'analysis_report.html').write_text(doc,encoding='utf-8')

def main():
    OUT.mkdir(parents=True,exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
    global MASTER
    MASTER=load_master()
    if len(MASTER)!=63: raise RuntimeError(f'Expected 63 K1-K6 rows, got {len(MASTER)}')
    # Unit memberships and summary invariants.
    for r in MASTER:
        assert r['unit_count']==int(r['K'][1:])
        assert abs(r['total_shed_mw']-(r['static_grid_shed_mw']+r['ufls_shed_mw']))<0.002,(r['scenario_id'],r['total_shed_mw'],r['static_grid_shed_mw'],r['ufls_shed_mw'])
        assert r['H_hard_buses']>=0 and r['H_hard_buses']<=30
        hard_buses={int(b) for b in r['hard_failure_buses'].split(';') if b}
        assert len(hard_buses)==r['H_hard_buses'],(r['scenario_id'],hard_buses,r['H_hard_buses'])
        assert len([u for u in r['actual_trip_units'].split(';') if u])==r['trip_count_before_stop'],(r['scenario_id'],r['actual_trip_units'],r['trip_count_before_stop'])
        expected_censored=';'.join(sorted(set(r['units'].split('+'))-set(r['actual_trip_units'].split(';'))))
        assert expected_censored==r['censored_units'],(r['scenario_id'],expected_censored,r['censored_units'])
        assert r['N_class'] in NCLASS
    master_path=write_master(MASTER)
    groups=build_summary(MASTER)
    # The original K6 first-H files remain the baseline; continuation is a separate result tree.
    k6_first=read_csv(ROOT/'results/K6/tables/six_unit_summary.csv')[0]
    k6_cont=read_csv(ROOT/'results/K6/continuation/tables/six_unit_summary.csv')[0]
    assert int(k6_first['n_bus_hard_failure'])==2
    assert int(k6_cont['faulted_units_tripped_count_before_stop'])==6
    assert not k6_cont['faulted_units_not_tripped_before_stop']
    assert int(k6_cont['n_bus_hard_failure'])==30 and int(k6_cont['n_f3_deenergized'])==30
    assert k6_cont['simulation_stop_reason']=='all_faulted_units_tripped'
    assert k6_cont['grid_endpoint_class']=='all_30_buses_F3_deenergized_no_source'
    mechanism_unit_rows,mechanism_case_rows=build_mechanism_metrics()
    fig01_mechanism();fig02_p5_levels();fig03_p5_triptime();fig04_k2_feedback();fig05_k1()
    fig06_all_cases();fig07_by_k();fig08_h_frequency();fig09_bus_incidence()
    fig10_p5_thermodynamics();fig11_mechanism_vs_grid(mechanism_case_rows);fig12_k6_continuation()
    # P5 and K1 source audit, reported instead of silently filling the missing legacy row.
    k1_legacy=len(read_csv(ROOT/'results/K1/tables/scenario_summary.csv'))
    k1_full=len(read_csv(ROOT/'results/K1/tables/six_unit_comparison.csv'))
    audit={'rows':len(MASTER),'k1_legacy_rows':k1_legacy,'k1_full_rows':k1_full,
        'shed_reconcile_max':max(abs(r['total_shed_mw']-r['static_grid_shed_mw']-r['ufls_shed_mw']) for r in MASTER if r['K']!='K1'),
        'mechanism_unit_rows':len(mechanism_unit_rows),'mechanism_case_rows':len(mechanism_case_rows),
        'k6_first_H':int(k6_first['n_bus_hard_failure']),'k6_continuation_H':int(k6_cont['n_bus_hard_failure']),
        'k6_continuation_F3':int(k6_cont['n_f3_deenergized']),
        'k6_continuation_trip_count':int(k6_cont['faulted_units_tripped_count_before_stop']),
        'k6_continuation_stop_reason':k6_cont['simulation_stop_reason'],
        'k6_continuation_grid_endpoint':k6_cont['grid_endpoint_class']}
    (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    captions=[
      ('fig01_coupling_mechanism','冷端—电网耦合链','概念机制图；补水—水量/流量—背压/排热—保护跳机—电网再调度的反馈闭环。'),
      ('fig02_p5_basin_margin','P5水池保护裕度','六机 P5 固定出力参考轨迹；水位归一化用于跨机组比较，保护阈值为0。'),
      ('fig03_p5_trip_time','P5耐受时间与锚点条件','按保护跳机时刻排序，并标注基态出力和可用池容。'),
      ('fig04_k2_g1_g2_feedback','K2-G1-G2冷端—电网时间序列','同轴展示水位裕度、Pg、背压/热力能力、需补水/实补水和电网频率。'),
      ('fig05_k1_six_units','K1六个单机情景','使用完整六案比较表；颜色代表N类别，H在该组六案均为0。'),
      ('fig06_all_scenario_map','K1–K6情景级总览','63个基线案例按K分组；左为H，右为频率最低点；菱形表示提前截断。'),
      ('fig07_outcomes_by_cardinality','按同时断水机组数的结果分布','展示所有离散情景点及范围/中位数，不将枚举集统计解释为概率。'),
      ('fig08_frequency_vs_hard_loss','频率与硬失供','气泡大小代表累计切负荷；空心表示未触发UFLS，菱形表示删失；H>0处的×n标记代表重叠情景数。'),
      ('fig09_hard_bus_incidence','硬失供母线端点','只纳入基线H>0案例，红色表示该案相应母线判为 F3 无源失电（H=1[F3]）。'),
      ('fig10_p5_coldend_thermodynamics','P5冷端热力变量','六机固定出力参考下的池水水位、循环流量、凝汽背压、饱和温度、冷却水出口温度、排热及蒸发变化。'),
      ('fig11_coldend_metrics_vs_grid','冷端指标与网侧端点','K2–K6单案级冷端变化与H并列；K6延续以星号单独标出，基础点按观测窗口计算。'),
      ('fig12_k6_full_continuation','K6首个H之后的独立延续','显示六台机组的水位裕度、背压、Pg与频率轨迹，并标出原first-H端点和后续冷端跳闸。'),
    ]
    make_html(MASTER,groups,captions,audit)
    print(f'Analysis built: {OUT}; {len(MASTER)} scenarios; {len(captions)} figures; K1 legacy/full={k1_legacy}/{k1_full}')

if __name__=='__main__': main()
