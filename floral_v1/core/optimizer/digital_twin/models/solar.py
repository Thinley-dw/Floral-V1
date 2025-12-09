import json
from pathlib import Path

import numpy as np
import pandas as pd

# Set print options
np.set_printoptions(formatter={"float": "{: 0.2f}".format})


def _solar_geometry_from_times(
    times: pd.DatetimeIndex,
    latitude_deg: float,
    longitude_deg: float,
    tilt_deg: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return cos(zenith), cos(incidence), and day-of-year for given timestamps."""
    N = times.dayofyear.to_numpy()
    hours = times.hour.to_numpy()
    L_loc = longitude_deg  # longitude of site
    L_st = 15 * round(L_loc / 15)  # Standard meridian
    lat = latitude_deg  # latitude of site

    x = np.deg2rad(360 * (N - 1) / 365)
    EOT = (
        0.258 * np.cos(x)
        - 7.416 * np.sin(x)
        - 3.648 * np.cos(2 * x)
        - 9.228 * np.sin(2 * x)
    )  # Equation of time (minutes)

    t_sol = hours + EOT / 60 - (L_st - L_loc) / 15
    omega = 15 * (t_sol - 12)

    delta = np.rad2deg(np.arcsin(0.39795 * np.cos(np.deg2rad(0.98563 * (N - 173)))))
    phi = lat
    beta = tilt_deg
    gamma = 180 if lat >= 0 else 0  # face collector toward equator

    sb = np.sin(np.deg2rad(beta))
    sd = np.sin(np.deg2rad(delta))
    sp = np.sin(np.deg2rad(phi))
    so = np.sin(np.deg2rad(omega))
    sg = np.sin(np.deg2rad(gamma))
    cb = np.cos(np.deg2rad(beta))
    cd = np.cos(np.deg2rad(delta))
    cp = np.cos(np.deg2rad(phi))
    co = np.cos(np.deg2rad(omega))
    cg = np.cos(np.deg2rad(gamma))

    sin_alpha = np.sin(np.deg2rad(phi)) * np.sin(np.deg2rad(delta)) + np.cos(np.deg2rad(phi)) * np.cos(
        np.deg2rad(delta)
    ) * np.cos(np.deg2rad(omega))
    sin_alpha = np.clip(sin_alpha, -1.0, 1.0)
    zenith = 90 - np.rad2deg(np.arcsin(sin_alpha))
    cos_zenith = np.clip(np.cos(np.deg2rad(zenith)), 0.0, None)

    cos_inc = cb * (sd * sp + cd * cp * co) - cd * so * sb * sg + sb * cg * (sd * cp - cd * co * sp)
    cos_inc = np.clip(cos_inc, 0.0, None)
    return cos_zenith, cos_inc, N


def _erbs_diffuse_fraction(kt: np.ndarray) -> np.ndarray:
    """Diffuse fraction from clearness index using Erbs correlation."""
    return np.where(
        kt <= 0.22,
        1 - 0.09 * kt,
        np.where(
            kt <= 0.8,
            0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4,
            0.165,
        ),
    )


def _transposition_to_tilt(
    ghi: np.ndarray,
    cos_zenith: np.ndarray,
    cos_incidence: np.ndarray,
    day_of_year: np.ndarray,
    tilt_deg: float,
    albedo: float = 0.141,
) -> np.ndarray:
    """Convert global horizontal irradiance to plane-of-array using simple isotropic transposition."""
    Isc = 1367  # W/m^2
    I0 = Isc * (1 + 0.034 * np.cos(np.deg2rad(360 * day_of_year / 365.25)))
    I0_h = I0 * cos_zenith
    I0_h[I0_h <= 0] = np.nan

    kt = np.divide(ghi, I0_h, out=np.zeros_like(ghi), where=I0_h > 0)
    kt = np.clip(kt, 0.0, 2.0)
    diffuse_fraction = np.clip(_erbs_diffuse_fraction(kt), 0.0, 1.0)
    dhi = diffuse_fraction * ghi

    beam_horizontal = np.clip(ghi - dhi, 0.0, None)
    dni = np.divide(beam_horizontal, cos_zenith, out=np.zeros_like(beam_horizontal), where=cos_zenith > 0)

    beta_rad = np.deg2rad(tilt_deg)
    poa = (
        dni * cos_incidence
        + dhi * ((1 + np.cos(beta_rad)) / 2)
        + ghi * albedo * ((1 - np.cos(beta_rad)) / 2)
    )
    return np.nan_to_num(poa)


def load_nasa_allsky(json_path: Path) -> tuple[pd.Series, float | None, float | None, float | None]:
    """Load NASA POWER ALLSKY_SFC_SW_DWN series and metadata."""
    payload = json.loads(Path(json_path).read_text())
    raw = payload["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
    series = pd.Series(raw, dtype=float)
    series.index = pd.to_datetime(series.index, format="%Y%m%d%H")
    series = series.sort_index()

    coords = payload.get("geometry", {}).get("coordinates", [])
    lon = float(coords[0]) if len(coords) > 0 else None
    lat = float(coords[1]) if len(coords) > 1 else None
    elev_km = float(coords[2]) / 1000 if len(coords) > 2 else None
    return series, lat, lon, elev_km


def compute_tilted_irradiance_from_nasa(
    json_path: Path,
    tilt_deg: float,
    latitude_deg: float | None = None,
    longitude_deg: float | None = None,
) -> pd.Series:
    """Convert NASA POWER hourly GHI to tilted plane-of-array irradiance."""
    ghi_series, nasa_lat, nasa_lon, _ = load_nasa_allsky(json_path)
    lat = latitude_deg if latitude_deg is not None else nasa_lat
    lon = longitude_deg if longitude_deg is not None else nasa_lon
    if lat is None or lon is None:
        raise ValueError("Latitude/longitude are required to tilt NASA irradiance.")

    times = pd.DatetimeIndex(ghi_series.index)
    cos_zenith, cos_inc, day_of_year = _solar_geometry_from_times(
        times=times,
        latitude_deg=lat,
        longitude_deg=lon,
        tilt_deg=tilt_deg,
    )
    poa = _transposition_to_tilt(
        ghi=ghi_series.to_numpy(),
        cos_zenith=cos_zenith,
        cos_incidence=cos_inc,
        day_of_year=day_of_year,
        tilt_deg=tilt_deg,
    )
    return pd.Series(poa, index=times, name="nasa_tilted_wm2")


def _compute_clear_sky_grid(
    latitude_deg: float,
    longitude_deg: float,
    elevation_km: float,
    tilt_deg: float,
) -> np.ndarray:
    """Clear-sky tilted irradiance grid shaped (365, 24)."""
    N = np.arange(1, 366)  # Day of year
    LCT = np.arange(24)  # Standard time hours
    L_loc = longitude_deg
    L_st = 15 * round(L_loc / 15)
    lat = latitude_deg
    elev = elevation_km

    x = np.deg2rad(360 * (N - 1) / 365)
    EOT = (
        0.258 * np.cos(x)
        - 7.416 * np.sin(x)
        - 3.648 * np.cos(2 * x)
        - 9.228 * np.sin(2 * x)
    )

    t_sol = LCT[None, :] + EOT[:, None] / 60 - (L_st - L_loc) / 15
    omega = 15 * (t_sol - 12)

    delta = np.rad2deg(np.arcsin(0.39795 * np.cos(np.deg2rad(0.98563 * (N - 173)))))
    delta = np.tile(delta[:, None], (1, len(LCT)))

    alpha = np.arcsin(
        np.sin(np.deg2rad(lat)) * np.sin(np.deg2rad(delta))
        + np.cos(np.deg2rad(lat))
        * np.cos(np.deg2rad(delta))
        * np.cos(np.deg2rad(omega))
    )
    zenith = 90 - np.rad2deg(alpha)
    cos_zenith = np.cos(np.deg2rad(zenith))

    Isc = 1367
    Io = Isc * (1 + 0.034 * np.cos(np.deg2rad(360 * N / 365.25)))
    Io = np.tile(Io[:, None], (1, len(LCT)))
    Io[zenith > 90] = 0

    a0 = 0.4237 - 0.00821 * (6 - elev) ** 2
    a1 = 0.5055 + 0.00595 * (6.5 - elev) ** 2
    k = 0.2711 + 0.01858 * (2.5 - elev) ** 2

    I_bn = Io * (a0 + a1 * np.exp(-k / np.cos(np.deg2rad(zenith))))
    I_dh = Io * cos_zenith * (0.2710 - 0.2939 * (a0 + a1 * np.exp(-k / np.cos(np.deg2rad(zenith)))))
    GHI = I_bn * cos_zenith + I_dh
    GHI[GHI <= 0] = np.nan

    beta = tilt_deg
    gamma = 180 if lat >= 0 else 0

    sb = np.sin(np.deg2rad(beta))
    sd = np.sin(np.deg2rad(delta))
    sp = np.sin(np.deg2rad(lat))
    so = np.sin(np.deg2rad(omega))
    sg = np.sin(np.deg2rad(gamma))
    cb = np.cos(np.deg2rad(beta))
    cd = np.cos(np.deg2rad(delta))
    cp = np.cos(np.deg2rad(lat))
    co = np.cos(np.deg2rad(omega))
    cg = np.cos(np.deg2rad(gamma))

    cos_inc = cb * (sd * sp + cd * cp * co) - cd * so * sb * sg + sb * cg * (sd * cp - cd * co * sp)
    cos_inc = np.clip(cos_inc, 0.0, None)

    rho = 0.141
    I_ta_direct = I_bn * cos_inc
    I_ta_diffuse = I_dh * ((1 + np.cos(np.deg2rad(beta))) / 2) + rho * GHI * ((1 - np.cos(np.deg2rad(beta))) / 2)
    I_ta = I_ta_direct + I_ta_diffuse
    I_ta[I_ta <= 0] = np.nan
    return np.nan_to_num(I_ta)


def compute_monthly_hourly_irradiance(
    latitude_deg: float,
    longitude_deg: float,
    elevation_km: float = 1.491,
    tilt_deg: float = 27.5,
) -> np.ndarray:
    """Return a 12 x 24 matrix of hourly irradiance averages for each month (clear-sky)."""
    I_ta = _compute_clear_sky_grid(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        elevation_km=elevation_km,
        tilt_deg=tilt_deg,
    )
    days_in_month__avg = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
    starts__avg = np.concatenate(([0], np.cumsum(days_in_month__avg)[:-1]))
    ends__avg = starts__avg + days_in_month__avg
    I_ta_houravg = np.vstack([np.mean(I_ta[s:e, :], axis=0) for s, e in zip(starts__avg, ends__avg)])
    return I_ta_houravg


def compute_hourly_irradiance_series(
    latitude_deg: float,
    longitude_deg: float,
    elevation_km: float = 1.491,
    tilt_deg: float = 27.5,
    year: int = 2023,
) -> pd.Series:
    """Return clear-sky hourly irradiance as a pandas Series spanning the year (8760 hours)."""
    I_ta = _compute_clear_sky_grid(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        elevation_km=elevation_km,
        tilt_deg=tilt_deg,
    )
    flattened = I_ta.flatten()
    start = pd.Timestamp(year=year, month=1, day=1, hour=0)
    index = pd.date_range(start, periods=flattened.size, freq="H")
    return pd.Series(flattened, index=index, name="solar_model_wm2")


if __name__ == "__main__":
    profile = compute_monthly_hourly_irradiance(
        latitude_deg=52.9225,
        longitude_deg=1.4746,
        elevation_km=1.491,
    )
    print("Average Hourly Total Aperture Irradiance for January:", profile[0, :])
