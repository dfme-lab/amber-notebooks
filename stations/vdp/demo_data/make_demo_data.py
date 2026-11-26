"""Make the FICTITIOUS demo data of a van der Pauw conductivity run (nothing here was measured).

Two kinds of files, as they come from two separate programs today:

* the vdP program: semicolon CSV, decimal comma, local time (Europe/Warsaw), a few header lines,
  four resistances per point: R12,34 and R23,41, each with + and - current; the program was
  restarted once, so there are two files, and a few points are broken (contact glitch, overload);
* the furnace log: comma CSV, ISO time in UTC, every 10 s, written by a PC whose clock is
  2 min 13 s fast.

Sample: a sintered MnCo2O4 pellet, 1.12 mm thick (small-polaron conductor, Ea 0.45 eV,
about 60 S/cm at 800 C). Program: 2 K/min to 900 C, then 50 K steps down to 300 C,
45 min hold each, cooling to room temperature. Run:  python make_demo_data.py
"""

from __future__ import annotations

import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

RUN = "ST99-26r001"  # fictitious station and run code, only for this demo
OUT = Path(__file__).resolve().parent / RUN
KB = 8.617e-5
T_MM = 1.12  # thickness, mm
EA, SIG800 = 0.45, 60.0  # eV, S/cm at 800 C
RATIO = 1.35  # R12,34 / R23,41 (contacts not perfectly symmetric)
I_A = 0.100  # A
START = datetime(2026, 11, 12, 7, 0, tzinfo=timezone.utc)
LOCAL = timezone(timedelta(hours=1))  # CET in November
CLOCK_FAST = timedelta(minutes=2, seconds=13)  # the furnace PC's clock error
rnd = random.Random(7)


def sigma(T_c: float, heating: bool) -> float:
    T = T_c + 273.15
    a = SIG800 * 1073.15 * math.exp(EA / (KB * 1073.15))
    s = a / T * math.exp(-EA / (KB * T))
    return s * (0.97 if heating else 1.0)  # slightly lower on first heating (not equilibrated)


def x_vdp(r: float) -> float:
    """x = pi R_B / Rs solving exp(-r x) + exp(-x) = 1."""
    x = math.log(2)
    for _ in range(50):
        f = math.exp(-r * x) + math.exp(-x) - 1
        d = -r * math.exp(-r * x) - math.exp(-x)
        x -= f / d
    return x


XB = x_vdp(RATIO)


def program(minute: float) -> float:
    """Furnace setpoint (C)."""
    t = minute
    up = (900 - 25) / 2
    if t < 20:
        return 25.0
    if t < 20 + up:
        return 25 + 2 * (t - 20)
    t -= 20 + up
    if t < 60:
        return 900.0
    t -= 60
    T = 900.0
    while T > 300:
        if t < 25:
            return T - 2 * t
        t -= 25
        T -= 50
        if t < 45:
            return T
        t -= 45
    return max(25.0, 300 - 2 * t)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total_min = 20 + (900 - 25) / 2 + 60 + 12 * 70 + 140
    # true sample temperature: lags the setpoint (first order, tau 6 min)
    temps = []
    Ts = 25.0
    n = int(total_min * 6)
    for k in range(n + 1):
        m = k / 6
        Ts += (program(m) - Ts) * (1 - math.exp(-(1 / 6) / 6))
        temps.append((m, Ts))

    # furnace log (thermocouple near the sample, +1.5 C offset, noise), clock fast
    with open(OUT / "furnace_log.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "unix_s", "pv_C", "setpoint_C", "output_pct"])
        for m, Ts in temps:
            t = START + timedelta(minutes=m) + CLOCK_FAST
            pv = Ts + 1.5 + rnd.gauss(0, 0.2)
            w.writerow([t.isoformat(timespec="seconds"), round(t.timestamp(), 1), round(pv, 2),
                        round(program(m), 1), round(min(100, max(0, 0.08 * pv + rnd.gauss(5, 1))), 1)])

    # vdP points every ~90 s; program restarted at 14:20 local (gap of 6 min)
    restart = START + timedelta(hours=6, minutes=20)
    files = {1: [], 2: []}
    m = 1.0
    peak_reached = False
    while m < total_min - 1:
        t = START + timedelta(minutes=m)
        Ts = temps[min(len(temps) - 1, int(m * 6))][1]
        if Ts > 899:
            peak_reached = True
        if Ts > 150 and not (restart <= t < restart + timedelta(minutes=6)):
            s = sigma(Ts, heating=not peak_reached)
            rs = 1 / (s * T_MM / 10)  # ohm per square
            rb = XB * rs / math.pi
            ra = RATIO * rb
            vth = 25e-6 * math.sin(m / 50) + 8e-6 * (Ts / 900)  # thermovoltage, V
            vals = []
            for r in (ra, rb):
                noise = r * 0.002
                vals += [r + vth / I_A + rnd.gauss(0, noise), r - vth / I_A + rnd.gauss(0, noise)]
            status = "OK"
            u = rnd.random()
            if u < 0.006:
                vals[0] *= 15  # contact glitch on one reading
            elif u < 0.010:
                vals = [float("nan")] * 4
                status = "OVERLOAD"
            files[1 if t < restart else 2].append((t, vals, status))
        m += 1.5 + rnd.uniform(-0.1, 0.1)

    def fmt(x: float) -> str:
        return "NaN" if math.isnan(x) else f"{x:.6f}".replace(".", ",")

    for k, rows in files.items():
        first = rows[0][0].astimezone(LOCAL)
        name = f"vdP_{first:%Y-%m-%d_%H%M}.txt"
        with open(OUT / name, "w", encoding="utf-8", newline="") as f:
            f.write("# van der Pauw measurement (DEMO, fictitious data)\n")
            f.write("# Sample: JK26s011-01 MnCo2O4 pellet\n")
            f.write(f"# Current: {I_A * 1000:.0f} mA; time: local (PC clock)\n")
            f.write("Data;Czas;R12_34_plus [Ohm];R12_34_minus [Ohm];R23_41_plus [Ohm];"
                    "R23_41_minus [Ohm];I [mA];Status\n")
            for t, v, st in rows:
                lt = t.astimezone(LOCAL)
                f.write(f"{lt:%d.%m.%Y};{lt:%H:%M:%S};" + ";".join(fmt(x) for x in v)
                        + f";{I_A * 1000:.0f};{st}\n")

    run_json = {
        "amber": {"version": 1, "run_url": None},
        "folder": f"{RUN}_JK26s011_MnCo2O4-vdP-demo",
        "run": {
            "code": RUN,
            "title": "vdP conductivity of a MnCo2O4 pellet, 900-300 C in air (DEMO, fictitious)",
            "station": {"code": "ST99", "handle": "vdp-demo", "name": "van der Pauw (demo)"},
            "operator": "AN",
            "actual_start": START.isoformat(),
            "actual_end": (START + timedelta(minutes=total_min)).isoformat(),
            "params": {"thickness_mm": T_MM, "current_mA": I_A * 1000, "atmosphere": "air"},
            "data_location": "demo data in dfme-lab/amber-notebooks",
        },
        "experiment": {
            "code": "AN26e002",
            "title": "Conductivity of spinel coating materials (DEMO)",
            "question": "What is the activation energy of MnCo2O4 between 300 and 900 C?",
        },
        "samples": [{"code": "JK26s011-01", "sample_set": "JK26s011",
                     "title": "MnCo2O4 pellet, sintered 1100 C (DEMO)",
                     "composition": "MnCo2O4"}],
        "created": START.isoformat(),
    }
    (OUT / "AMBER_run.json").write_text(json.dumps(run_json, indent=2), encoding="utf-8")
    names = sorted(p.name for p in OUT.iterdir() if p.name != "MANIFEST.txt")
    (OUT / "MANIFEST.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    print(names, {k: len(v) for k, v in files.items()})


if __name__ == "__main__":
    main()
