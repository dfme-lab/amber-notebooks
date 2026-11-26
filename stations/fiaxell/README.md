# Fiaxell SOFC station (ST05)

- `fiaxell_demo.ipynb` – the whole path of one run, from AMBER to a result for the experiment:
  run overview (furnace, gas flows), OCV against Nernst, I-V and power density, EIS (ohmic and
  polarisation resistance), Arrhenius plot, a summary table. Open in Colab:
  https://colab.research.google.com/github/dfme-lab/amber-notebooks/blob/main/stations/fiaxell/fiaxell_demo.ipynb
- `demo_data/` – **fictitious** data of run ST05-26r001 in the layout the station program writes
  (`make_demo_data.py` makes them). Nothing there was measured.

With real data: upload the run's data folder (it holds `AMBER_run.json`) and set `FOLDER` in the
notebook. The potentiostat file layout (I-V, EIS columns) must be checked against real Ivium exports.
