import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
ROWS = 5000
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

# category: (base_vcpu, vcpu_per_1000_users, base_ram_gb, ram_gb_per_1000_users, default_family)
PROFILES = {
    "E-Commerce": (1, 0.8, 2, 1.5, "general"),
    "AI/ML": (2, 1.5, 8, 3.0, "compute"),
    "Website Hosting": (1, 0.3, 1, 0.4, "burstable"),
    "Mobile App": (1, 0.5, 2, 0.8, "general"),
    "Video Streaming": (2, 1.0, 4, 1.0, "compute"),
    "IoT": (1, 0.4, 2, 0.6, "general"),
    "Database": (2, 0.6, 8, 3.5, "memory"),
    "DevOps": (2, 0.4, 4, 0.8, "general"),
    "Data Analytics": (4, 1.0, 16, 4.0, "memory"),
    "Serverless": (1, 0.2, 1, 0.3, "burstable"),
}
PERF_MULT = {"low": 0.7, "medium": 1.0, "high": 1.5}

RULES = [
    "need_vcpu = (base_vcpu + users/1000*vcpu_per_1000_users + traffic_gb_month/400) * perf_multiplier * noise",
    "need_ram_gb = (base_ram + users/1000*ram_per_1000_users + storage_gb/200) * perf_multiplier * noise",
    "perf_multiplier: low=0.7, medium=1.0, high=1.5; noise = lognormal(0, 0.08)",
    "instance_family = category default; AI/ML with high performance -> gpu",
    "values rounded up and clipped to 1..128 vCPU and 1..1024 GB RAM",
]


def family_for(category, performance, default_family):
    if category == "AI/ML" and performance == "high":
        return "gpu"
    return default_family


def main():
    rng = np.random.default_rng(SEED)
    names = list(PROFILES)
    categories = [str(c) for c in rng.choice(names, size=ROWS)]
    users = np.round(np.exp(rng.uniform(math.log(10), math.log(100_000), ROWS))).astype(int)
    traffic = np.round(np.exp(rng.uniform(math.log(1), math.log(20_000), ROWS)), 1)
    storage = np.round(np.exp(rng.uniform(math.log(5), math.log(20_000), ROWS))).astype(int)
    performance = [str(p) for p in rng.choice(["low", "medium", "high"], size=ROWS, p=[0.25, 0.5, 0.25])]

    rows = []
    for i in range(ROWS):
        base_cpu, cpu_k, base_ram, ram_k, default_family = PROFILES[categories[i]]
        mult = PERF_MULT[performance[i]]
        vcpu = (base_cpu + users[i] / 1000 * cpu_k + traffic[i] / 400) * mult * rng.lognormal(0, 0.08)
        ram = (base_ram + users[i] / 1000 * ram_k + storage[i] / 200) * mult * rng.lognormal(0, 0.08)
        rows.append(
            {
                "category": categories[i],
                "users": int(users[i]),
                "traffic_gb_month": float(traffic[i]),
                "storage_gb": int(storage[i]),
                "performance": performance[i],
                "need_vcpu": int(min(128, max(1, math.ceil(vcpu)))),
                "need_ram_gb": int(min(1024, max(1, math.ceil(ram)))),
                "instance_family": family_for(categories[i], performance[i], default_family),
                "data_source": "synthetic",
            }
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "synthetic_dataset.csv", index=False)

    info = {
        "data_source": "synthetic",
        "warning": "Generated from documented sizing rules, NOT measured from real AWS workloads.",
        "rows": ROWS,
        "seed": SEED,
        "rules": RULES,
        "profiles": {k: dict(zip(["base_vcpu", "vcpu_per_1000_users", "base_ram_gb", "ram_gb_per_1000_users", "default_family"], v)) for k, v in PROFILES.items()},
    }
    (DATA_DIR / "dataset_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    print("Saved", len(df), "rows to", DATA_DIR / "synthetic_dataset.csv")
    print(df.head())
    print()
    print(df["instance_family"].value_counts())


if __name__ == "__main__":
    main()
