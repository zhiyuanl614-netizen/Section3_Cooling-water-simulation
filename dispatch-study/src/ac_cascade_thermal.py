"""
ac_cascade_thermal.py - 纯AC级联仿真 (6台火电，RTS-96爬坡)
目标：找出大规模级联边界（爬坡也无法弥补）
"""
import json, os, itertools, copy
import numpy as np, pandas as pd
from collections import defaultdict, deque

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH=os.path.join(ROOT,"data/case30.json")
with open(JSON_PATH) as f:
    jdata=json.load(f)

baseMVA=jdata['baseMVA']
bus_ids=[b[0] for b in jdata['bus']]
bus_idx={bid:i for i,bid in enumerate(bus_ids)}
gen_buses=[g[0] for g in jdata['gen']]
gen_data=jdata['gen']  # 21列
# 提取爬坡
ramp_agc=[g[16] if len(g)>16 else 0 for g in gen_data]
ramp_10=[g[17] if len(g)>17 else 0 for g in gen_data]
ramp_30=[g[18] if len(g)>18 else 0 for g in gen_data]
Pmax=[g[8] for g in gen_data]
Pmin=[g[9] for g in gen_data]
Pg_init=[g[1] for g in gen_data]  # 初态
print(f"火电机组 {len(gen_data)}台: Pmax={Pmax} MW, 初态Pg={Pg_init}")
print(f"爬坡 RU(MW/min)={ramp_agc}, 10min={ramp_10}, 30min={ramp_30}")
print(f"总发电能力 {sum(Pmax)} MW, 总负荷 {sum(b[2] for b in jdata['bus'])} MW, 备用 {sum(Pmax)-sum(b[2] for b in jdata['bus']):.1f} MW")

from pypower.api import runpf, ppoption

def build_ppc_from_jdata(jdata_mod, gen_pg_override=None):
    """从jdata构建ppc，gen_pg_override: {gen_idx: Pg_new}"""
    bus_arr=np.array(jdata_mod['bus'], dtype=float)
    branch_list=[]
    for br in jdata_mod['branch']:
        f,t,r,x,b,rateA,rateB,rateC = br
        branch_list.append([f,t,r,x,b,rateA,rateB,rateC,0,0,1,-360,360])
    branch_arr=np.array(branch_list, dtype=float)
    gen_arr=np.array(jdata_mod['gen'], dtype=float)
    if gen_pg_override is not None:
        for idx, pg in gen_pg_override.items():
            gen_arr[idx,1]=pg
            # 若pg==0且原status=1，保持status=1但Pg=0（模拟退出但潮流中仍有母线）；若彻底退出则status=0
            # 这里退出设Pg=0且status=0
            if pg==0 and jdata_mod['gen'][idx][7]==1 and idx in gen_pg_override and gen_pg_override[idx]==0:
                # 判断是否为故障退出：若该idx在outage中，status=0
                pass
    gencost_arr=np.array(jdata_mod['gencost'], dtype=float)
    ppc={"baseMVA": baseMVA, "bus": bus_arr, "gen": gen_arr, "branch": branch_arr, "gencost": gencost_arr, "version":"2"}
    return ppc

def run_ac(ppc):
    ppopt=ppoption(PF_ALG=1, VERBOSE=0, OUT_ALL=0)
    try:
        result, success = runpf(ppc, ppopt)
        return result, success
    except Exception as e:
        return None, False

def find_islands(branch_active, bus_ids):
    """BFS找孤岛，branch_active: bool array, 返回 list of sets(bus)"""
    adj=defaultdict(list)
    for i, br in enumerate(jdata['branch']):
        if not branch_active[i]:
            continue
        f,t=br[0],br[1]
        adj[f].append(t); adj[t].append(f)
    visited=set()
    islands=[]
    for bid in bus_ids:
        if bid in visited:
            continue
        # BFS
        q=deque([bid]); comp=set([bid]); visited.add(bid)
        while q:
            cur=q.popleft()
            for nb in adj[cur]:
                if nb not in visited:
                    visited.add(nb); comp.add(nb); q.append(nb)
        islands.append(comp)
    return islands

def ac_cascade_for_outage(outage_idx, max_stages=10, trip_one_per_stage=True):
    """
    单次故障组合的AC级联
    返回: {stages, total_Ls, n_failed_bus, branch_trips, converged, final_Vm}
    """
    ng=len(gen_data)
    total_Pd=sum(b[2] for b in jdata['bus'])
    total_Pg_init=sum(Pg_init)
    # 计算缺额与可爬坡弥补
    lost_Pg=sum(Pg_init[i] for i in outage_idx)
    remaining_idx=[i for i in range(ng) if i not in outage_idx]
    # 可用爬坡（30min）
    avail_ramp30=sum(min(Pmax[i]-Pg_init[i], ramp_30[i]) for i in remaining_idx)
    avail_ramp10=sum(min(Pmax[i]-Pg_init[i], ramp_10[i]) for i in remaining_idx)
    # 简单再调度：按爬坡能力比例分配缺额，限Pmax
    Pg_new = Pg_init.copy()
    for i in outage_idx:
        Pg_new[i]=0
    deficit=lost_Pg
    # 按Pmax裕量比例分配
    if deficit>0 and remaining_idx:
        # 计算每台可增量
        inc_cap={i: min(Pmax[i]-Pg_init[i], ramp_30[i]) for i in remaining_idx}
        total_inc=sum(inc_cap.values())
        if total_inc >= deficit:
            # 按比例分配
            for i in remaining_idx:
                Pg_new[i] = Pg_init[i] + deficit * (inc_cap[i]/total_inc)
        else:
            # 全部拉满仍不足，剩余缺额需切负荷
            for i in remaining_idx:
                Pg_new[i] = Pg_init[i] + inc_cap[i]
            unsupplied = deficit - total_inc
            # unsupplied将通过后续潮流不平衡体现，最终需切负荷
            # 标记需切负荷量
            pass
    # 构建初始ppc（故障后）
    jmod=copy.deepcopy(jdata)
    # 设置故障机组状态及Pg
    for i in outage_idx:
        jmod['gen'][i][1]=0  # Pg
        jmod['gen'][i][7]=0  # status 0
    for i in remaining_idx:
        jmod['gen'][i][1]=Pg_new[i]
    # 若unsupplied>0，暂不切负荷，靠潮流不平衡（会不收敛或低电压），后续按需切

    #级联循环
    branch_active=np.ones(len(jdata['branch']), dtype=bool)
    stage_logs=[]
    total_trips=0
    final_Ls=0
    n_failed_bus=0
    converged=True
    final_Vm=None

    for stage in range(max_stages):
        # 构建当前拓扑的ppc
        # 若有跳闸，移除支路
        jstage=copy.deepcopy(jmod)
        # 保留active支路
        active_branches=[br for i,br in enumerate(jstage['branch']) if branch_active[i]]
        jstage['branch']=active_branches
        # 若无支路，跳过
        if len(active_branches)==0:
            break
        ppc=build_ppc_from_jdata(jstage)
        result, success = run_ac(ppc)
        if not success or result is None:
            # AC不收敛 -> 视为电压崩溃，需大面积切负荷
            # 尝试切负荷20%重试
            # 简化：直接判为大规模失效
            converged=False
            stage_logs.append({"stage":stage, "success":False, "n_branch_active": branch_active.sum(), "note":"AC不收敛-电压崩溃"})
            # 估算切负荷：按缺额比例
            total_Pg_after=sum(Pg_new[i] for i in remaining_idx)
            unsupplied = total_Pd - total_Pg_after
            if unsupplied>0:
                final_Ls = unsupplied
                # 估算失电母线数：按负荷比例切
                # 假设优先切末端，但这里简化按负荷大小切到满足平衡
                # 取所有负荷母线，按Pd排序切到累计>=unsupplied
                loads_sorted=sorted([(b[0],b[2]) for b in jdata['bus'] if b[2]>0], key=lambda x: x[1])
                acc=0; cnt=0
                for bid,pd in loads_sorted:
                    acc+=pd; cnt+=1
                    if acc>=unsupplied*0.9:
                        break
                n_failed_bus=cnt
            break
        # 检查支路过载和电压
        branch_out=result['branch']
        Pf=branch_out[:,13] if branch_out.shape[1]>13 else np.zeros(len(active_branches))
        rateA=branch_out[:,5]
        loading=np.abs(Pf)/np.maximum(rateA,1)*100
        overloaded=np.where(loading>100)[0]
        Vm=result['bus'][:,7]
        final_Vm=Vm.min()
        V_viol=((Vm<0.88)|(Vm>1.11)).sum()
        # 记录
        stage_logs.append({"stage":stage, "success":True, "n_branch_active": int(branch_active.sum()), "max_loading": loading.max(), "n_overloaded": len(overloaded), "min_Vm": Vm.min(), "V_viol": int(V_viol)})
        if len(overloaded)==0 and V_viol==0:
            # 无过载无电压越限，稳定
            break
        # 有过载或电压越限，跳闸
        # 选择最重载1条跳闸
        if len(overloaded)>0:
            # 需映射回原branch索引
            # 找出active中loading最大的
            worst_active_idx=np.argmax(loading)
            # 找到原branch索引
            active_indices=np.where(branch_active)[0]
            orig_idx=active_indices[worst_active_idx]
            branch_active[orig_idx]=False
            total_trips+=1
            if trip_one_per_stage:
                continue
            else:
                # 跳所有过载
                for oi in overloaded:
                    orig=np.where(branch_active)[0][oi] if oi<len(active_indices) else None
                    if orig is not None:
                        branch_active[orig]=False
                        total_trips+=1
        elif V_viol>0:
            # 电压越限但无过载，判为需切负荷，但不跳线（简化）
            # 直接结束，认为需切负荷
            break
    # 最终评估切负荷：若收敛且无过载，按功率平衡算实际缺额
    if converged and final_Vm is not None:
        # 实际缺额 = 总负荷 - 总剩余发电
        total_Pg_after=sum(Pg_new[i] for i in remaining_idx)
        unsupplied=max(0, total_Pd - total_Pg_after)
        # 若有跳闸导致孤岛无源，额外切负荷
        # 简单用跳闸数估算额外切负荷：每跳1条末端16MVA线约切10MW
        extra_Ls = total_trips * 5  # 经验
        final_Ls = unsupplied + extra_Ls
        # 失电母线数按切负荷估算：平均每母线约9.5MW (189.2/20)
        avg_load=total_Pd/20
        n_failed_bus=int(round(final_Ls/avg_load)) if avg_load>0 else 0
        n_failed_bus=min(n_failed_bus, 20)
    return {
        "outage_idx": outage_idx,
        "lost_Pg": lost_Pg,
        "avail_ramp10": avail_ramp10,
        "avail_ramp30": avail_ramp30,
        "deficit_after_ramp": max(0, lost_Pg - avail_ramp30),
        "Pg_new": Pg_new,
        "stages": len(stage_logs),
        "total_trips": total_trips,
        "final_Ls": final_Ls,
        "n_failed_bus": n_failed_bus,
        "converged": converged,
        "stage_logs": stage_logs,
        "final_minVm": final_Vm
    }

# 枚举 k=1..6
all_results={}
for k in [1,2,3,4,5,6]:
    combos=list(itertools.combinations(range(len(gen_data)), k))
    print(f"\n=== k={k} {len(combos)}组合 ===")
    k_results=[]
    for combo in combos:
        res=ac_cascade_for_outage(list(combo))
        k_results.append(res)
        # 打印最严重
    # 统计
    Ls_list=[r['final_Ls'] for r in k_results]
    failed_list=[r['n_failed_bus'] for r in k_results]
    trips_list=[r['total_trips'] for r in k_results]
    print(f" k={k} 均值切负荷 {np.mean(Ls_list):.1f} MW, 最大 {np.max(Ls_list):.1f} MW")
    print(f"  均值失电母线 {np.mean(failed_list):.2f}, 最大 {np.max(failed_list)}, 最小 {np.min(failed_list)}")
    print(f"  均值跳闸 {np.mean(trips_list):.2f}, 最大 {np.max(trips_list)}")
    # 大停电概率 (≥3母线 或 ≥30%负荷57MW)
    prob_large_bus=sum(1 for f in failed_list if f>=3)/len(failed_list)*100
    prob_large_load=sum(1 for ls in Ls_list if ls>=57)/len(Ls_list)*100
    prob_large=max(prob_large_bus, prob_large_load)
    print(f"  大停电概率(≥3母线) {prob_large_bus:.1f}%, (≥57MW) {prob_large_load:.1f}%")
    # 找出最严重组合
    worst=max(k_results, key=lambda x: (x['n_failed_bus'], x['final_Ls']))
    print(f"  最严重: G{worst['outage_idx']} Bus{[gen_buses[i] for i in worst['outage_idx']]} lostPg={worst['lost_Pg']:.1f}MW ramp30={worst['avail_ramp30']:.1f} deficitAfterRamp={worst['deficit_after_ramp']:.1f}")
    print(f"   -> Ls={worst['final_Ls']:.1f}MW, nFailed={worst['n_failed_bus']}, trips={worst['total_trips']}, stages={worst['stages']}, minVm={worst['final_minVm']}")
    # 打印爬坡不足判定
    for r in k_results:
        if r['deficit_after_ramp']>0.1:
            print(f"    * G{list(r['outage_idx'])} 爬坡不足: lost{ r['lost_Pg']:.1f} > ramp{ r['avail_ramp30']:.1f} deficit{r['deficit_after_ramp']:.1f} -> Ls{r['final_Ls']:.1f}")
            break
    all_results[k]=k_results

# 保存
os.makedirs(os.path.join(ROOT,"results"), exist_ok=True)
summary_rows=[]
for k in [1,2,3,4,5,6]:
    k_results=all_results[k]
    Ls=[r['final_Ls'] for r in k_results]
    failed=[r['n_failed_bus'] for r in k_results]
    trips=[r['total_trips'] for r in k_results]
    summary_rows.append({
        "k": k,
        "n_combos": len(k_results),
        "mean_Ls_MW": np.mean(Ls),
        "max_Ls_MW": np.max(Ls),
        "mean_failed_bus": np.mean(failed),
        "max_failed_bus": np.max(failed),
        "mean_trips": np.mean(trips),
        "max_trips": np.max(trips),
        "prob_large_bus_ge3_pct": sum(1 for f in failed if f>=3)/len(failed)*100,
        "prob_large_load_ge57_pct": sum(1 for ls in Ls if ls>=57)/len(Ls)*100,
        "mean_deficit_after_ramp": np.mean([r['deficit_after_ramp'] for r in k_results]),
        "max_deficit_after_ramp": np.max([r['deficit_after_ramp'] for r in k_results]),
        "n_ramp_insufficient": sum(1 for r in k_results if r['deficit_after_ramp']>0.1)
    })
pd.DataFrame(summary_rows).to_csv(os.path.join(ROOT,"results/ac_thermal_cascade_summary.csv"), index=False)
# 详细
detail_rows=[]
for k in all_results:
    for r in all_results[k]:
        detail_rows.append({
            "k": k,
            "outage_idx": str(list(r['outage_idx'])),
            "outage_buses": str([gen_buses[i] for i in r['outage_idx']]),
            "lost_Pg_MW": r['lost_Pg'],
            "avail_ramp10_MW": r['avail_ramp10'],
            "avail_ramp30_MW": r['avail_ramp30'],
            "deficit_after_ramp_MW": r['deficit_after_ramp'],
            "final_Ls_MW": r['final_Ls'],
            "n_failed_bus": r['n_failed_bus'],
            "total_trips": r['total_trips'],
            "stages": r['stages'],
            "converged": r['converged'],
            "final_minVm_pu": r['final_minVm']
        })
pd.DataFrame(detail_rows).to_csv(os.path.join(ROOT,"results/ac_thermal_cascade_detailed.csv"), index=False)
print("\n已保存: results/ac_thermal_cascade_summary.csv, ac_thermal_cascade_detailed.csv")
# 判定边界
print("\n=== 大规模级联边界判定（火电爬坡也无济于事）===")
for row in summary_rows:
    k=row['k']
    insuff=row['n_ramp_insufficient']
    prob=row['prob_large_bus_ge3_pct']
    print(f" k={k}: 爬坡不足组合 {insuff}/{row['n_combos']} ({insuff/row['n_combos']*100:.1f}%), 大停电概率 {prob:.1f}%, 最大缺额 {row['max_deficit_after_ramp']:.1f}MW -> {'边界' if prob>=50 and insuff>0 else '可控' if prob<50 else '临界'}")
