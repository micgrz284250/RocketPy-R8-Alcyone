# RocketPy R8 V3 weather update

Last updated: **13 September 2026**.

Scenario: **18 October 2026, 14:00 Europe/Lisbon**, equivalent to **13:00 UTC** (WEST, UTC+1).
Weather data extraction/interpolation location: **39.388984, −8.288272**.

As agreed, this uses a **historical climate profile, not a forecast or a weather observation for 18 October 2026**.

## Source and method

The selected public dataset is **NOAA PSL, NCEP/NCAR Reanalysis 1**, using the **1991–2020** climate normal and the “4-times-daily long-term mean” product. It provides consistent long-term temperature data, heights of pressure surfaces and both wind components. A 30-year climate normal bases the scenario on a multi-year reference period rather than an arbitrarily chosen historical day. However, its spatial resolution is substantially lower than that of the newer ERA5 reanalysis.

The profile uses means for **18 October** at **12:00 and 18:00 UTC**. Interpolation to 13:00 UTC uses weights of 5/6 and 1/6 respectively. The NOAA time axis uses the nominal year 0001; the downloaded indices 1162 and 1163 correspond to these two times. These are means for 1991–2020, not observations from the year 0001.

Temperature, wind and geopotential height data come from 17 pressure levels: 1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30, 20 and 10 hPa. The data were bilinearly interpolated to the requested location on a 2.5° grid. Near-surface temperature was taken from 2 m AGL and wind from 10 m AGL, using the T62 Gaussian grid (approximately 1.9°).

Geopotential heights were converted to geometric metres above mean sea level: z = R·H/(R−H), with R = 6,371,000 m. This converts the height coordinate of the weather data; it does not change the simulation's Earth model. Pressure was converted from hPa to Pa, interpolated in log(P) against height and resampled at 50 m intervals. RocketPy reads the resulting tables through the existing `custom_atmosphere` model.

The launch elevation remains 160 m MSL. Pressure at this elevation was interpolated between the two surrounding pressure levels. Temperature at 2 m AGL was held constant down to the ground; wind at 10 m AGL was held constant below 10 m. Above these heights, the values were joined to the pressure-level profiles. The wind convention is positive u towards the east and positive v towards the north.

| Near-surface quantity | Applied value |
| --- | ---: |
| Temperature | 17.45°C |
| Pressure at 160 m MSL | 996.78 hPa |
| Wind component u | 0.9794 m/s |
| Wind component v | 0.7431 m/s |
| Magnitude of the mean wind vector | approximately 1.23 m/s |
| Meteorological direction (wind from) | approximately 233° |

**The magnitude of the mean wind vector is not the mean wind speed.** Averaging components can partly cancel winds from opposite directions. This scenario does not represent gusts, directional variability, local terrain or extreme conditions. A single simulated flight is not an uncertainty interval or a forecast of the landing point on launch day.

Sources:

- [NOAA PSL — NCEP/NCAR Reanalysis 1 description](https://psl.noaa.gov/data/gridded/data.ncep.reanalysis.html)
- [NOAA PSL — pressure-level data catalogue](https://psl.noaa.gov/thredds/catalog/Datasets/ncep.reanalysis/Monthlies/pressure/catalog.html)
- [NOAA PSL — near-surface data catalogue](https://psl.noaa.gov/thredds/catalog/Datasets/ncep.reanalysis/Monthlies/surface_gauss/catalog.html)
- Exact URLs for all downloaded subsets, metadata and SHA-256 checksums: `weather/source/sources.json` and the accompanying `.ascii` and `.das` files.