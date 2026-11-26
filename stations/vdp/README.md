# van der Pauw conductivity (demo)

- `vdp_demo.ipynb` – from the raw files to σ(T) and the activation energy: joins the vdP program's
  files (four resistances, ± current, decimal comma, local time), removes broken points, averages
  the current directions (thermovoltage), solves the van der Pauw equation, finds the clock offset
  to the separate furnace log, keeps stable plateaus, Arrhenius fit, result table. Open in Colab:
  https://colab.research.google.com/github/dfme-lab/amber-notebooks/blob/main/stations/vdp/vdp_demo.ipynb
- `demo_data/` – **fictitious** run ST99-26r001 (MnCo2O4 pellet, Ea 0.45 eV, furnace PC clock
  2 min 13 s fast); `make_demo_data.py` makes it. Nothing there was measured.

The file layout of the real vdP program is not known yet: adapt section 2 (reading) once with a
real file; the rest stays.
