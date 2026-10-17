# R8 — EuRoC launch conditions, Santa Margarida

Reference model parameters:

- EuRoC 2026 dates: `15–21 October 2026`;
- launch site: Campo Militar de Santa Margarida;
- latitude: `39.3897° N`;
- longitude: `8.2889639° W`;
- elevation: `160 m MSL`;
- nominal launch rail heading: `133°`;
- nominal inclination: `84°` above horizontal;
- team launch rail length: `12.00 m`;
- maximum permitted ground wind speed: `8.7 m/s`;
- minimum rail departure velocity: `30 m/s`;
- minimum rail departure stability margin: `1.5 cal`;
- launch site radius: `2500 m`.

The default run uses an example wind of `5 m/s` from the west:

```python
env, motor, rocket, flight = run_simulation()
```

No-wind variant for comparing models:

```python
env, motor, rocket, flight = run_simulation(
    wind_speed=0.0,
    wind_direction_from=0.0,
)
```

Maximum permitted ground wind scenario:

```python
env, motor, rocket, flight = run_simulation(
    wind_speed=8.7,
    wind_direction_from=270.0,
)
```

A wind that is constant at every altitude is a comparison scenario, not a forecast.
Before flight, use an up-to-date vertical profile from a forecast or data from
the weather station at the launch range.

Testing a constant wind of `8.7 m/s` from eight directions produced landing
points approximately `196 m` to `1415 m` from the launcher. All remained within
the reference radius of `2500 m`. This does not replace an analysis using
an actual vertical wind profile.

Sources:

- EuRoC Launch Operations Guide, sections 4.2–4.6;
- Portuguese Space Agency announcement of the EuRoC 2026 dates, dated 6 May 2026.
