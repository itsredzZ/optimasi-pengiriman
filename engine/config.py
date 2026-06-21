"""
engine/config.py
==================
Parameter PSO & operasional sebagai dataclass — pengganti konstanta global
(W_MAX, C1, TARIF_DASAR, dst) di kode asli. Diisi dari tabel `settings`,
bukan hardcoded, sesuai requirement halaman Pengaturan (G) di proposal.
"""

from dataclasses import dataclass


@dataclass
class PSOParams:
    n_partikel: int = 30
    n_iterasi: int = 100
    early_stop: int = 20
    w_max: float = 0.9
    w_min: float = 0.4
    c1: float = 2.0
    c2: float = 2.0
    base_seed: int = 42


@dataclass
class OperationalParams:
    harga_solar: float = 6800       # Rp per liter
    tarif_dasar: float = 20         # Rp per (kg-tagihan x km x faktor-dimensi)
    bbm_base: float = 0.08          # konsumsi BBM dasar (L/km)
    bbm_faktor: float = 0.02        # tambahan konsumsi per 1000 kg muatan


def _to_number(value: str):
    """Konversi string dari kolom param_value ke int/float yang sesuai."""
    try:
        if "." in value:
            return float(value)
        return int(value)
    except (TypeError, ValueError):
        return value


def load_pso_params(setting_rows) -> PSOParams:
    """
    setting_rows: iterable objek Setting (atau dict sejenis) dengan
    field param_group=='pso', param_key, param_value.

    Contoh pemakaian (di halaman Streamlit):
        with get_session() as session:
            rows = session.query(Setting).filter_by(param_group="pso").all()
            pso_params = load_pso_params(rows)
    """
    values = {row.param_key: _to_number(row.param_value) for row in setting_rows}
    defaults = PSOParams()
    return PSOParams(
        n_partikel=values.get("n_partikel", defaults.n_partikel),
        n_iterasi=values.get("n_iterasi", defaults.n_iterasi),
        early_stop=values.get("early_stop_iter", defaults.early_stop),
        w_max=values.get("w_max", defaults.w_max),
        w_min=values.get("w_min", defaults.w_min),
        c1=values.get("c1", defaults.c1),
        c2=values.get("c2", defaults.c2),
        base_seed=values.get("base_seed", defaults.base_seed),
    )


def load_operational_params(setting_rows) -> OperationalParams:
    values = {row.param_key: _to_number(row.param_value) for row in setting_rows}
    defaults = OperationalParams()
    return OperationalParams(
        harga_solar=values.get("harga_solar", defaults.harga_solar),
        tarif_dasar=values.get("tarif_dasar", defaults.tarif_dasar),
        bbm_base=values.get("bbm_base", defaults.bbm_base),
        bbm_faktor=values.get("bbm_faktor", defaults.bbm_faktor),
    )