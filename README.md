# amber-notebooks

Notebook templates for the stations of the DFME group, opened from the run page in
[DFME Amber](https://amber.dfme.eu) (D-230, D-231).

- One folder per station: `stations/<ST code>/` (e.g. `stations/ST-005/`). `stations/_example/` is the
  starting point for a new template.
- **Public repository: never put data, results, keys or names of samples here.** Only code.
- Data that are not confidential: open a template in Google Colab (the run page has the button).
  Confidential data: only the group's Jupyter (`jupyter.amber.dfme.eu`) or your own computer.
- The AMBER client (read-only, D-232) installs straight from here:

  ```python
  %pip install -q git+https://github.com/dfme-lab/amber-notebooks
  from amber_client import Amber
  ```

  Your key: a read-only key from AMBER › Settings › API keys, as the Colab secret `AMBER_KEY`
  or in the file `~/.amber_key`. Never in a notebook.

To add a template for a station: copy `stations/_example/`, change it, open a pull request; then in
AMBER add an analysis tool for the station whose version is the link to the notebook on GitHub
(`https://github.com/dfme-lab/amber-notebooks/blob/main/stations/<ST>/<name>.ipynb`).

The client source lives in the AMBER repository (`clients/python`); this copy is updated from there.
