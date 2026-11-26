"""AMBER client for notebooks and scripts (D-232): read runs, experiments and samples.

Standard library only, so it works in Colab, JupyterHub and a plain Python without extra packages.
It only reads; nothing is written to AMBER (D-141). Every read goes through the public API with
your own key, so you see exactly what you may see in the app.

The key (``amber_uk_...``, a read-only key is enough; AMBER > Settings > API keys) is found in
this order, and never has to be typed into the notebook:

1. the ``AMBER_KEY`` environment variable,
2. in Google Colab, the notebook secret ``AMBER_KEY`` (the key icon on the left),
3. the file ``~/.amber_key`` (first line), or another file given as ``key_file``.

Example::

    from amber_client import Amber, load_run_json
    amber = Amber()                      # https://amber.dfme.eu, key as above
    run = amber.run("ST05-26r001")       # the run, as the app shows it to you
    info = load_run_json("ST05-26r001_conditions/")   # the AMBER_run.json in a data folder
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

__all__ = ["Amber", "AmberError", "find_key", "load_run_json"]
__version__ = "0.1.0"

DEFAULT_URL = "https://amber.dfme.eu"
KEY_PREFIX = "amber_uk_"
KEY_ENV = "AMBER_KEY"
DEFAULT_KEY_FILE = "~/.amber_key"
RUN_JSON = "AMBER_run.json"


class AmberError(Exception):
    """A problem reading from AMBER. The message never contains the key."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def _colab_secret(name: str) -> str | None:
    try:
        from google.colab import userdata  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        value = userdata.get(name)
    except Exception:  # noqa: BLE001  # secret missing or access not granted to this notebook
        return None
    return value or None


def _check(key: str, where: str) -> str:
    key = key.strip()
    if not key.startswith(KEY_PREFIX):
        raise AmberError(f"{where} does not hold an AMBER key ({KEY_PREFIX}...)")
    return key


def find_key(key_file: str | os.PathLike[str] | None = None) -> str:
    """The API key from the environment, a Colab secret or a key file (in that order)."""
    env = os.environ.get(KEY_ENV)
    if env:
        return _check(env, f"the {KEY_ENV} environment variable")
    if key_file is None:
        secret = _colab_secret(KEY_ENV)
        if secret:
            return _check(secret, f"the Colab secret {KEY_ENV}")
    path = Path(os.path.expandvars(os.path.expanduser(str(key_file or DEFAULT_KEY_FILE))))
    try:
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        raise AmberError(
            f"no AMBER key: set {KEY_ENV}, add the Colab secret {KEY_ENV} or put the key in {path}"
        ) from None
    if not lines:
        raise AmberError(f"the key file {path} is empty")
    return _check(lines[0], f"the key file {path}")


def _quote(code: str) -> str:
    return urllib.parse.quote(code.strip(), safe="")


class Amber:
    """Read access to one AMBER instance with your personal key."""

    def __init__(
        self,
        url: str | None = None,
        key: str | None = None,
        *,
        key_file: str | os.PathLike[str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.url = (url or os.environ.get("AMBER_URL") or DEFAULT_URL).rstrip("/")
        if not self.url.startswith("https://") and not self.url.startswith("http://localhost"):
            raise AmberError("AMBER is reached over HTTPS only")
        self._key = _check(key, "the given key") if key else find_key(key_file)
        self.timeout = timeout

    def __repr__(self) -> str:  # never show the key
        return f"Amber({self.url!r})"

    def get(self, path: str, **params: Any) -> Any:
        """GET an API path (e.g. ``/api/v1/runs/ST05-26r001``) and return the JSON."""
        if not path.startswith("/"):
            path = "/" + path
        query = {k: v for k, v in params.items() if v is not None}
        full = self.url + path + (("?" + urllib.parse.urlencode(query)) if query else "")
        req = urllib.request.Request(
            full,
            headers={
                "Authorization": f"Bearer {self._key}",
                "Accept": "application/json",
                "User-Agent": f"amber-client/{__version__}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = json.loads(e.read() or b"{}").get("detail") or ""
            except (ValueError, AttributeError):
                pass
            hint = {
                401: "the key is unknown, expired or revoked",
                403: "you may not see this",
                404: "not found (or not visible to you)",
            }.get(e.code, "")
            text = "; ".join(x for x in (hint, str(detail) if detail else "") if x)
            raise AmberError(
                f"{path}: HTTP {e.code}" + (f" ({text})" if text else ""), e.code
            ) from None
        except urllib.error.URLError as e:
            raise AmberError(f"cannot reach {self.url} ({e.reason})") from None
        return json.loads(body) if body else None

    # ---- the records a notebook usually needs -------------------------------------------

    def run(self, code: str) -> Any:
        """One run by its code, e.g. ``ST05-26r001``."""
        return self.get(f"/api/v1/runs/{_quote(code)}")

    def experiment(self, code: str) -> Any:
        """One experiment by its code."""
        return self.get(f"/api/v1/experiments/{_quote(code)}")

    def sample_set(self, code: str) -> Any:
        """One sample set by its code (a piece code also finds its set)."""
        return self.get(f"/api/v1/sample-sets/{_quote(code)}")

    def batch(self, code: str) -> Any:
        """One batch by its code."""
        return self.get(f"/api/v1/batches/{_quote(code)}")

    def links(self, code: str) -> Any:
        """What a run, experiment, sample set or batch is linked to."""
        return self.get(f"/api/v1/links/{_quote(code)}")

    def station_data(self, code: str) -> Any:
        """The station data of a run: status, files, alerts (D-156)."""
        return self.get(f"/api/v1/runs/{_quote(code)}/station-data")


def load_run_json(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read ``AMBER_run.json`` from a run's data folder (D-73), or from the file itself.

    Works offline: the file was written when the folder was made. Its ``report`` token is left
    out, because a notebook does not need it and it should not end up in shared outputs.
    """
    p = Path(path).expanduser()
    if p.is_dir():
        p = p / RUN_JSON
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except OSError:
        raise AmberError(f"no {RUN_JSON} at {p}") from None
    except ValueError:
        raise AmberError(f"{p} is not valid JSON") from None
    if not isinstance(data, dict) or "run" not in data:
        raise AmberError(f"{p} is not an AMBER run file")
    data.pop("report", None)
    out: dict[str, Any] = data
    return out
