"""
ac_base_run.py - 仅AC潮流，无故障基态 (PYPOWER runpf)
使用最新的 case30.json 数据构建 PPC
"""
import json, os, numpy as np, pandas as pd
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH=os.path.join(ROOT,"data/case30.json")
with open(JSON_PATH) as f:
    jdata=json.load(f)

# 构建 ppc 字典供 pypower 使用
# ppc fields: baseMVA, bus, gen, branch, gencost
baseMVA=jdata['baseMVA']
# bus: 13 columns as in MATPOWER
bus_arr=np.array(jdata['bus'], dtype=float)
# branch: 13 columns, need to expand to 13? json has 8 columns: [f,t,r,x,b,rateA,rateB,rateC] -> need to expand to 13 with ratio, angle, status, angmin, angmax
branch_list=[]
for br in jdata['branch']:
    f,t,r,x,b,rateA,rateB,rateC = br
    # ratio=0, angle=0, status=1, angmin=-360, angmax=360
    branch_list.append([f,t,r,x,b,rateA,rateB,rateC,0,0,1,-360,360])
branch_arr=np.array(branch_list, dtype=float)
# gen: 21 columns
gen_arr=np.array(jdata['gen'], dtype=float)
# 确保 gen 有21列，若只有10列则已扩展
if gen_arr.shape[1]==10:
    # 扩展
    extra=np.zeros((gen_arr.shape[0],11))
    gen_arr=np.hstack([gen_arr, extra])
gencost_arr=np.array(jdata['gencost'], dtype=float)

ppc={
    "baseMVA": baseMVA,
    "bus": bus_arr,
    "gen": gen_arr,
    "branch": branch_arr,
    "gencost": gencost_arr,
    "version": "2"
}

from pypower.api import runpf, ppoption
ppopt=ppoption(PF_ALG=1, VERBOSE=0, OUT_ALL=0)
result, success = runpf(ppc, ppopt)
print(f"收敛: {success} (1=成功)")

bus_out=result['bus']
gen_out=result['gen']
branch_out=result['branch']

Vm=bus_out[:,7]
Va=bus_out[:,8]
Pd=bus_out[:,2]
Qd=bus_out[:,3]
print(f"电压 Vm: min {Vm.min():.4f} pu (Bus {int(bus_out[Vm.argmin(),0])}), max {Vm.max():.4f}, mean {Vm.mean():.4f}")
print(f"相角 Va: min {Va.min():.2f}°, max {Va.max():.2f}°, 跨度 {Va.max()-Va.min():.2f}°")
# 越限
Vmin_norm, Vmax_norm = 0.95, 1.05
Vmin_em, Vmax_em = 0.88, 1.11
viol_norm=((Vm<Vmin_norm)|(Vm>Vmax_norm)).sum()
viol_em=((Vm<Vmin_em)|(Vm>Vmax_em)).sum()
print(f"正常限 [0.95,1.05] 越限 {viol_norm} 母线 {'✅无越限' if viol_norm==0 else '❌有越限'}")
print(f"紧急限 [0.88,1.11] 越限 {viol_em} 母线 {'✅无越限' if viol_em==0 else '❌有越限'}")

# 发电
Pg=gen_out[:,1]
Qg=gen_out[:,2]
print(f"\n发电机出力 (AC基态, 6台):")
for i,g in enumerate(gen_out):
    print(f" G{i+1} Bus{int(g[0])}: Pg={g[1]:.2f} MW, Qg={g[2]:.2f} MVar, Vg={g[5]:.4f} pu, Pmax={g[8]:.0f} MW")

Pg_sum=Pg.sum()
Pd_sum=Pd.sum()
print(f"总发电 {Pg_sum:.2f} MW vs 总负荷 {Pd_sum:.2f} MW -> 网损 {Pg_sum-Pd_sum:.2f} MW ({(Pg_sum-Pd_sum)/Pg_sum*100:.2f}%)")
Ploss = (Pg_sum - Pd_sum)
Qg_sum=Qg.sum()
Qd_sum=Qd.sum()
print(f"总无功 Qg {Qg_sum:.2f} MVar vs Qd {Qd_sum:.2f} MVar -> 无功损耗 {Qg_sum-Qd_sum:.2f} MVar")

# 支路
# branch result columns after runpf: 0:f,1:t,2:r,3:x,4:b,5:rateA,6:rateB,7:rateC,8:ratio,9:angle,10:status,11:angmin,12:angmax,13:Pf,14:Qf,15:Pt,16:Qt
Pf=branch_out[:,13]
Qf=branch_out[:,14]
Pt=branch_out[:,15] if branch_out.shape[1]>15 else -Pf
loading=np.abs(Pf)/np.maximum(branch_out[:,5],1)*100
print(f"\n支路有功流 Pf: min {Pf.min():.1f}, max {Pf.max():.1f}, 均值 {np.abs(Pf).mean():.1f} MW")
print(f"支路负载率: max {loading.max():.1f}%, 均值 {loading.mean():.1f}%")
top5=np.argsort(loading)[-5:][::-1]
print("最重载5条:")
for k in top5:
    print(f" L{k+1} {int(branch_out[k,0])}->{int(branch_out[k,1])} Pf={Pf[k]:.1f} MW Qf={Qf[k]:.1f} MVar / rateA={branch_out[k,5]:.0f} -> {loading[k]:.1f}%")
# 保存
os.makedirs(os.path.join(ROOT,"results"), exist_ok=True)
pd.DataFrame({
    "bus": bus_out[:,0].astype(int),
    "type": bus_out[:,1].astype(int),
    "Pd_MW": bus_out[:,2],
    "Qd_MVar": bus_out[:,3],
    "Vm_pu": Vm,
    "Va_deg": Va,
    "Vmax_pu": bus_out[:,11],
    "Vmin_pu": bus_out[:,12]
}).to_csv(os.path.join(ROOT,"results/ac_base_bus.csv"), index=False)
pd.DataFrame({
    "gen": [f"G{i+1}" for i in range(len(gen_out))],
    "bus": gen_out[:,0].astype(int),
    "Pg_MW": gen_out[:,1],
    "Qg_MVar": gen_out[:,2],
    "Qmax_MVar": gen_out[:,3],
    "Qmin_MVar": gen_out[:,4],
    "Vg_pu": gen_out[:,5],
    "Pmax_MW": gen_out[:,8],
    "Pmin_MW": gen_out[:,9],
    "ramp_agc_MWmin": gen_out[:,16] if gen_out.shape[1]>16 else 0,
    "ramp_10_MW": gen_out[:,17] if gen_out.shape[1]>17 else 0,
    "ramp_30_MW": gen_out[:,18] if gen_out.shape[1]>18 else 0,
}).to_csv(os.path.join(ROOT,"results/ac_base_gen.csv"), index=False)
pd.DataFrame({
    "branch": np.arange(1,len(branch_out)+1),
    "from": branch_out[:,0].astype(int),
    "to": branch_out[:,1].astype(int),
    "r_pu": branch_out[:,2],
    "x_pu": branch_out[:,3],
    "rateA_MVA": branch_out[:,5],
    "Pf_MW": Pf,
    "Qf_MVar": Qf,
    "Pt_MW": Pt,
    "loading_pct": loading
}).to_csv(os.path.join(ROOT,"results/ac_base_branch.csv"), index=False)
print("\n已保存: results/ac_base_bus.csv, ac_base_gen.csv, ac_base_branch.csv")

# 输出每母线电压表
print("\n母线电压明细:")
for i,b in enumerate(bus_out):
    print(f" Bus{int(b[0]):2d} Type{int(b[1])} Vm={Vm[i]:.4f} Va={Va[i]:6.2f}° Pd={b[2]:5.1f} Qd={b[3]:5.1f}")
