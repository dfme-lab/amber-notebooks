"""Make the FICTITIOUS demo data of run ST05-26r001 (Fiaxell SOFC station).

Nothing here was measured. The files have the layout the Fiaxell station program writes
(stations/fiaxell in the AMBER repository): <run>_conditions.csv, <run>_flow.csv,
<run>_temperature.csv, the AMBER_run.json of the data folder, and potentiostat exports in
the sub-folder <run>/ (I-V and EIS as plain CSV; real Ivium exports must be checked).

The cell model: OCV from the Nernst equation, an ohmic and a polarisation resistance with
Arrhenius temperature dependence, a Butler-Volmer-like activation term and a small
concentration loss. Run:  python make_demo_data.py   (writes ./ST05-26r001/)
"""

from __future__ import annotations

import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

RUN = "ST05-26r001"
OUT = Path(__file__).resolve().parent / RUN
F, R = 96485.0, 8.314
AREA = 1.0  # cm2, active area
START = datetime(2026, 11, 10, 6, 0, tzinfo=timezone.utc)
DT = 60  # s between log rows (the station writes every 10 s; 60 s keeps the files small)
CHANNELS = ["Air", "N2-1", "N2-2", "H2", "O2-1", "O2-2"]
rnd = random.Random(26)


def dg(T: float) -> float:
    """Gibbs energy of H2 + 1/2 O2 -> H2O(g), J/mol (linear fit, 900-1200 K)."""
    return -247_400.0 + 55.85 * T


def nernst(T_c: float, x_h2: float, x_h2o: float, po2_ox: float = 0.21) -> float:
    T = T_c + 273.15
    return -dg(T) / (2 * F) + R * T / (2 * F) * math.log(x_h2 / x_h2o * math.sqrt(po2_ox))


def r_ohm(T_c: float) -> float:  # ohm cm2, 0.10 at 800 C, Ea 0.75 eV
    return 0.10 * math.exp(0.75 * 96485 / R * (1 / (T_c + 273.15) - 1 / 1073.15))


def r_pol(T_c: float) -> float:  # ohm cm2, 0.16 at 800 C, Ea 1.25 eV
    return 0.16 * math.exp(1.25 * 96485 / R * (1 / (T_c + 273.15) - 1 / 1073.15))


def voltage(T_c: float, i: float, ocv: float) -> float:
    """Cell voltage at current density i (A/cm2)."""
    T = T_c + 273.15
    i0 = R * T / (2 * F * r_pol(T_c))  # exchange current from the polarisation resistance
    eta_act = 2 * R * T / (2 * F) * math.asinh(i / (2 * i0))
    i_lim = 2.2
    eta_conc = -R * T / (2 * F) * math.log(max(1e-6, 1 - i / i_lim))
    return ocv - i * r_ohm(T_c) - eta_act - eta_conc


# ---- the program: heat-up, reduction, three temperatures, cool-down -------------------
# (minutes from start, furnace setpoint C, H2, N2-1, O2-1, Air sccm, event)
STEPS = [
    (0, 25, 0, 200, 0, 200, "heat-up in N2 / air"),
    (390, 800, 0, 200, 0, 200, "at 800 C"),
    (420, 800, 20, 180, 0, 200, "reduction 10 % H2"),
    (480, 800, 100, 100, 0, 200, "reduction 50 % H2"),
    (540, 800, 200, 0, 3, 400, "step 1: 800 C, H2 + 3 % H2O"),
    (780, 750, 200, 0, 3, 400, "step 2: 750 C"),
    (1020, 700, 200, 0, 3, 400, "step 3: 700 C"),
    (1260, 700, 0, 200, 0, 200, "safe gas, cool-down"),
    (1680, 25, 0, 200, 0, 200, "end"),
]
MEAS = [(1, 800, 600), (2, 750, 840), (3, 700, 1080)]  # step, T, minute of the I-V / EIS


def setpoints(minute: float) -> dict[str, float]:
    """Gas setpoints (sccm) of the program step running at this minute."""
    cur = STEPS[0]
    for s in STEPS:
        if minute >= s[0]:
            cur = s
    return {"H2": cur[2], "N2-1": cur[3], "O2-1": cur[4], "Air": cur[5], "N2-2": 0.0, "O2-2": 0.0}


def furnace_setpoint(minute: float) -> float:
    """2 K/min ramps from 25 to 800, then holds, steps down by 50 C, cool at 2 K/min."""
    if minute < 30:
        return 25.0
    if minute < 30 + 775 / 2:
        return 25 + 2 * (minute - 30)
    if minute < 780:
        return 800.0
    if minute < 805:
        return 800 - 2 * (minute - 780)
    if minute < 1020:
        return 750.0
    if minute < 1045:
        return 750 - 2 * (minute - 1020)
    if minute < 1260:
        return 700.0
    return max(25.0, 700 - 2 * (minute - 1260))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / RUN).mkdir(exist_ok=True)
    end = START + timedelta(minutes=1680)

    # AMBER_run.json (what AMBER writes when the data folder is made)
    run_json = {
        "amber": {"version": 1, "run_url": "https://test.next.dfme.eu/runs/" + RUN},
        "folder": f"{RUN}_JK26s007_SOFC-button-cell-demo",
        "run": {
            "code": RUN,
            "title": "SOFC button cell, 700-800 C, H2 + 3 % H2O (DEMO, fictitious)",
            "station": {"code": "ST05", "handle": "fiaxell", "name": "Fiaxell SOFC test station"},
            "operator": "JK",
            "planned_start": START.isoformat(),
            "planned_end": end.isoformat(),
            "actual_start": START.isoformat(),
            "actual_end": end.isoformat(),
            "params": {"active_area_cm2": AREA},
            "data_location": "demo data in dfme-lab/amber-notebooks",
        },
        "experiment": {
            "code": "JK26e003",
            "title": "Button cells with the new LSCF cathode (DEMO)",
            "question": "Does the new cathode lower the area specific resistance at 700 C?",
        },
        "samples": [
            {
                "code": "JK26s007-01",
                "sample_set": "JK26s007",
                "title": "NiO-YSZ | YSZ | GDC | LSCF button cell (DEMO)",
                "composition": "LSCF cathode, 1 cm2",
            },
        ],
        "created": START.isoformat(),
    }
    (OUT / "AMBER_run.json").write_text(json.dumps(run_json, indent=2), encoding="utf-8")

    # flow and temperature logs
    with (
        open(OUT / f"{RUN}_flow.csv", "w", newline="") as ff,
        open(OUT / f"{RUN}_temperature.csv", "w", newline="") as tf,
    ):
        fw, tw = csv.writer(ff), csv.writer(tf)
        fields = ("pressure", "temperature", "vol_flow", "mass_flow", "setpoint")
        fw.writerow(["timestamp", "unix_s"] + [f"{c}_{k}" for c in CHANNELS for k in fields])
        tw.writerow(
            [
                "timestamp",
                "unix_s",
                "pv_C",
                "setpoint_C",
                "output_pct",
                "program_step",
                "phase",
                "paused",
            ]
        )
        pv = 25.0
        for n in range(1680 * 60 // DT + 1):
            t = START + timedelta(seconds=n * DT)
            minute = n * DT / 60
            sp = setpoints(minute)
            row = [t.isoformat(), round(t.timestamp(), 3)]
            for c in CHANNELS:
                s = sp[c]
                m = max(0.0, s + rnd.gauss(0, 0.3) if s else rnd.gauss(0, 0.05))
                row += [
                    round(1.02 + rnd.gauss(0, 0.002), 4),
                    round(23 + rnd.gauss(0, 0.2), 2),
                    round(m * 1.01, 2),
                    round(m, 2),
                    s,
                ]
            fw.writerow(row)
            fsp = furnace_setpoint(minute)
            pv += (fsp - pv) * 0.35 + rnd.gauss(0, 0.15)
            out = max(0.0, min(100.0, 8 + 0.06 * pv + 4 * (fsp - pv)))
            k = sum(1 for s in STEPS if minute >= s[0])
            tw.writerow(
                [
                    t.isoformat(),
                    round(t.timestamp(), 3),
                    round(pv, 2),
                    round(fsp, 1),
                    round(out, 1),
                    k,
                    "ramp" if abs(fsp - pv) > 3 else "hold",
                    0,
                ]
            )

    # conditions: one row when the composition is reached, one with the first OCV
    cond_rows = []
    ocv_offset = {1: -0.006, 2: -0.009, 3: -0.012}  # small leak: measured a bit below theory
    for step, T, minute in MEAS:
        x_h2, x_h2o = 0.97, 0.03
        theory = nernst(T, x_h2, x_h2o)
        t = START + timedelta(minutes=minute - 30)
        base = {
            "time_utc": t.isoformat(timespec="seconds"),
            "unix_s": round(t.timestamp(), 3),
            "event": "composition",
            "step": step,
            "composition": 1,
            "area_cm2": AREA,
            "T_C": T,
            "x_H2": x_h2,
            "x_H2O": x_h2o,
            "x_N2_fuel": 0.0,
            "x_O2_ox": 0.21,
            "pO2_fuel_bar": float(f"{math.exp(4 * F * (-theory) / (R * (T + 273.15))) * 0.21:.3e}"),
            "pO2_ox_bar": 0.21,
            "OCV_theory_V": round(theory, 4),
            "I_ref_A": 0.5,
            "FU": round(0.5 / (2 * F) / (200 / 22414 / 60), 4),
            "OU": round(0.5 / (4 * F) / (400 * 0.21 / 22414 / 60), 4),
            **{
                f"{c}_sccm": (200 if c == "H2" else 3 if c == "O2-1" else 400 if c == "Air" else 0)
                for c in CHANNELS
            },
            **{f"{c}_measured_sccm": None for c in CHANNELS},
            "OCV_measured_V": None,
            "OCV_deviation_mV": None,
        }
        cond_rows.append(base)
        meas = round(theory + ocv_offset[step], 4)
        t2 = START + timedelta(minutes=minute)
        cond_rows.append(
            {
                **base,
                "time_utc": t2.isoformat(timespec="seconds"),
                "unix_s": round(t2.timestamp(), 3),
                "event": "ocv",
                "OCV_measured_V": meas,
                "OCV_deviation_mV": round((meas - theory) * 1000, 1),
            }
        )

        # I-V: 0 -> 1.6 A/cm2 in 0.02 A/cm2 steps, 2 s per point
        with open(OUT / RUN / f"{RUN}_step{step}_IV_{T}C.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time_s", "current_A", "potential_V"])
            ocv = meas
            for k in range(81):
                i = 0.02 * k
                v = voltage(T, i, ocv) + rnd.gauss(0, 0.0008)
                if v < 0.5:
                    break
                w.writerow([2 * k, round(i * AREA, 4), round(v, 5)])

        # EIS at OCV: 100 kHz -> 0.1 Hz, two RQ arcs
        with open(OUT / RUN / f"{RUN}_step{step}_EIS_OCV_{T}C.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["freq_Hz", "Z_re_ohm", "Z_im_ohm"])
            ro, rp = r_ohm(T) / AREA, r_pol(T) / AREA
            arcs = [
                (0.35 * rp, 2e3 * math.exp((T - 800) / 40), 0.85),
                (0.65 * rp, 30 * math.exp((T - 800) / 60), 0.9),
            ]
            for k in range(71):
                fq = 10 ** (5 - k * 0.1)
                w_ = 2 * math.pi * fq
                z = complex(ro, w_ * 5e-8)  # lead inductance (positive imaginary part)
                for r, fc, a in arcs:
                    q = 1 / (r * (2 * math.pi * fc) ** a)
                    z += r / (1 + r * q * (1j * w_) ** a)
                z += complex(rnd.gauss(0, 0.0004), rnd.gauss(0, 0.0004))
                w.writerow([round(fq, 4), round(z.real, 5), round(z.imag, 5)])

    with open(OUT / f"{RUN}_conditions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cond_rows[0].keys()))
        w.writeheader()
        w.writerows(cond_rows)
    files = sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*.*") if p.name != "MANIFEST.txt")
    (OUT / "MANIFEST.txt").write_text("\n".join(files) + "\n", encoding="utf-8")
    print("written:", sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file()))


if __name__ == "__main__":
    main()
