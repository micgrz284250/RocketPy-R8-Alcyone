"""Rebuild the climate scenario offline from the bundled NOAA ASCII subsets.

Requires numpy (already required by RocketPy). No forecast is generated.
"""
import hashlib
import json
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LATITUDE, LONGITUDE = 39.388984, -8.288272
ELEVATION = 160.0  # Unchanged launch elevation; used only to anchor weather.
EARTH_RADIUS = 6371000.0


def read_grid(key, variable):
    text = (HERE / 'source' / f'{key}.ascii').read_text()
    body = text.split('---------------------------------------------')[1]
    header = re.search(rf'^{variable}\.{variable}((?:\[\d+\])+)$', body, re.M)
    shape = tuple(map(int, re.findall(r'\d+', header[1])))
    data = np.full(shape, np.nan)
    rows = body[header.end():].split('\n\n')[0]
    for line in rows.splitlines():
        if not line.startswith('['):
            continue
        left, right = line.split(',', 1)
        index = tuple(map(int, re.findall(r'\d+', left)))
        data[index] = np.fromstring(right, sep=',')
    assert np.isfinite(data).all() and (np.abs(data) < 1e6).all()
    coords = {}
    for name in ['time', 'lat', 'lon', 'level']:
        match = re.search(rf'^{variable}\.{name}\[\d+\]\n([^\n]+)', body, re.M)
        if match:
            coords[name] = np.fromstring(match[1], sep=',')
    assert np.array_equal(coords['time'], [-15762780, -15762774])
    # The source's year 0001 time axis corresponds to 18 October, 12:00 and 18:00 UTC.
    lat, lon = coords['lat'], coords['lon']
    a = (LATITUDE - lat[0]) / (lat[1] - lat[0])
    b = ((LONGITUDE % 360) - lon[0]) / (lon[1] - lon[0])
    assert 0 <= a <= 1 and 0 <= b <= 1
    point = ((1-a)*(1-b)*data[..., 0, 0] + (1-a)*b*data[..., 0, 1]
             + a*(1-b)*data[..., 1, 0] + a*b*data[..., 1, 1])
    # 14:00 Europe/Lisbon on 2026-10-18 is 13:00 UTC (WEST).
    return point[0] * (5/6) + point[1] * (1/6), coords


upper = {v: read_grid(v, v)[0] for v in ['air', 'hgt', 'uwnd', 'vwnd']}
levels = read_grid('air', 'air')[1]['level']
h = EARTH_RADIUS * upper['hgt'] / (EARTH_RADIUS - upper['hgt'])
p = levels * 100  # hPa -> Pa
assert np.all(np.diff(h) > 0) and np.all(np.diff(p) < 0)
t2 = float(read_grid('air_2m', 'air')[0])
u10 = float(read_grid('uwnd_10m', 'uwnd')[0])
v10 = float(read_grid('vwnd_10m', 'vwnd')[0])

# Near-surface temperature at 2 m AGL; 10 m wind held constant below 10 m.
# Above that, interpolate to the pressure-level reanalysis profile.
above = h > ELEVATION + 10
temp_h = np.r_[ELEVATION, ELEVATION+2, h[above]]
temp = np.r_[t2, t2, upper['air'][above]]
wind_h = np.r_[ELEVATION, ELEVATION+10, h[above]]
u = np.r_[u10, u10, upper['uwnd'][above]]
v = np.r_[v10, v10, upper['vwnd'][above]]

assert h[0] <= ELEVATION < h[1], 'Ground pressure must be bracketed by data.'
# Densify pressure in log(P) versus geometric height, then RocketPy can use
# its normal linear table interpolation without a large pressure-level gap.
pressure_h = np.unique(np.r_[ELEVATION, np.arange(200, h[-1], 50), h[h > ELEVATION]])
pressure = np.exp(np.interp(pressure_h, h, np.log(p)))
profiles = {
    'pressure': np.column_stack([pressure_h, pressure]).tolist(),
    'temperature': np.column_stack([temp_h, temp]).tolist(),
    'wind_u': np.column_stack([wind_h, u]).tolist(),
    'wind_v': np.column_stack([wind_h, v]).tolist(),
}
metadata = {
    'updated_on': '2026-09-13',
    'scenario_kind': 'historical_climatological_mean_not_forecast',
    'target_local_datetime': '2026-10-18T14:00:00+01:00',
    'target_timezone': 'Europe/Lisbon',
    'target_utc_datetime': '2026-10-18T13:00:00Z',
    'weather_latitude': LATITUDE,
    'weather_longitude': LONGITUDE,
    'source': 'NOAA PSL NCEP/NCAR Reanalysis 1, 4-times-daily long-term means',
    'climatology_period': '1991-2020',
    'climatology_day': '18 October',
    'time_interpolation': '5/6 of 12 UTC + 1/6 of 18 UTC',
    'spatial_interpolation': 'bilinear at requested weather coordinates',
    'upper_grid_degrees': 2.5,
    'surface_grid': 'T62 Gaussian: approximately 1.9 degrees',
    'height_units': 'geometric metres above mean sea level',
    'pressure_units': 'Pa', 'temperature_units': 'K', 'wind_units': 'm/s',
    'wind_convention': 'u positive east; v positive north',
    'geopotential_height_conversion_radius_m': EARTH_RADIUS,
    'surface_temperature_2m_K': t2,
    'surface_wind_10m_u_mps': u10, 'surface_wind_10m_v_mps': v10,
    'surface_pressure_at_160m_Pa': float(pressure[0]),
    'limitations': [
        'Climatological vector-mean wind suppresses variability and is not mean wind speed.',
        'Coarse source grid does not resolve local terrain or launch-site gusts.',
        'No forecast, actual weather, ensemble, or worst-case flight is represented.',
        '2 m temperature is held constant down to ground; 10 m wind is held constant below 10 m.',
    ],
}
(HERE / 'profile.json').write_text(json.dumps({'metadata': metadata, 'profiles': profiles}, indent=2) + '\n', encoding='utf-8')
print(json.dumps(metadata, indent=2))
