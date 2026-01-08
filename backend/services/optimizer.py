import itertools

def generate_parameter_grid():
    """
    Generates a massive grid of potential strategy parameters.
    Returns a list of dicts.
    """
    fast_range = [3, 5, 8, 10, 15]
    slow_range = [15, 30, 45, 60]
    vol_range = [0.10, 0.20, 0.30]
    sl_range = [0.005, 0.01, 0.015] # 0.5% - 1.5% Stop Loss
    tp_range = [0.01, 0.02, 0.03] # 1% - 3% Take Profit
    threshold_range = [0.0002, 0.0005, 0.001] # 0.02% to 0.1% confidence filter
    
    grid = []
    for f, s, v, sl, tp, th in itertools.product(fast_range, slow_range, vol_range, sl_range, tp_range, threshold_range):
        # Filter out invalid combos where fast >= slow
        if f < s:
            grid.append({
                "fast": f,
                "slow": s,
                "vol_target": v,
                "sl_pct": sl,
                "tp_pct": tp,
                "threshold": th
            })
            
    return grid

def mutate_parameters(best_arm: dict):
    """
    Takes the winning parameters and creates 'neighbor' variants.
    """
    mutations = []
    for df in [-2, 1]:
        for ds in [-5, 5]:
            for dv in [-0.05, 0.05]:
                for d_sl in [-0.002, 0.002]:
                    for d_tp in [-0.005, 0.005]:
                        for d_th in [-0.0002, 0.0002]:
                            new_f = max(2, best_arm['fast'] + df)
                            new_s = max(new_f + 5, best_arm['slow'] + ds)
                            new_v = max(0.05, min(0.5, best_arm['vol_target'] + dv))
                            new_sl = max(0.002, min(0.05, best_arm.get('sl_pct', 0.01) + d_sl))
                            new_tp = max(0.005, min(0.1, best_arm.get('tp_pct', 0.02) + d_tp))
                            new_th = max(0.0, min(0.01, best_arm.get('threshold', 0.0005) + d_th))
                            
                            mutations.append({
                                "fast": new_f,
                                "slow": new_s,
                                "vol_target": round(new_v, 2),
                                "sl_pct": round(new_sl, 4),
                                "tp_pct": round(new_tp, 4),
                                "threshold": round(new_th, 5)
                            })
    return mutations
