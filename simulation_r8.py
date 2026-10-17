import json
from math import atan2, cos, degrees, hypot, pi, radians, sin
from pathlib import Path
import datetime

import CoolProp.CoolProp as CP
import pytz
from rocketpy import (
    CylindricalTank,
    Environment,
    Flight,
    Fluid,
    LiquidMotor,
    MassFlowRateBasedTank,
    NoseCone,
    Rocket,
    Tail,
    TrapezoidalFins,
)


BASE_DIR = Path(__file__).resolve().parent
THRUST_FILE = BASE_DIR / "NOVA_2026_09_20.eng"
DRAG_FILE = BASE_DIR / "drag_curve.csv"
ROCKET_NAME = "R8"
SIMULATION_UPDATED_ON = "2026-09-13"
WEATHER_PROFILE_FILE = BASE_DIR / "weather" / "profile.json"

# Official parameters for the EuRoC launch site at Santa Margarida.
LAUNCH_LATITUDE = 39.3897
LAUNCH_LONGITUDE = -8.28896388888889
LAUNCH_ELEVATION = 160.0
LAUNCH_RAIL_LENGTH = 12.0
LAUNCH_INCLINATION = 84.0
LAUNCH_HEADING = 133.0

# Default: historical NOAA climate profile for 1991-2020, not a forecast.
# None retains the vertical profile; numerical values specify a wind variant.
REFERENCE_WIND_SPEED = None
REFERENCE_WIND_DIRECTION_FROM = None

EUROC_MAX_GROUND_WIND_SPEED = 8.7  # m/s
EUROC_MIN_OUT_OF_RAIL_VELOCITY = 30.0  # m/s
EUROC_MIN_OUT_OF_RAIL_STABILITY = 1.5  # calibres
EUROC_LAUNCH_SITE_RADIUS = 2500.0  # m

ROCKET_LENGTH = 4.5701
ROCKET_RADIUS = 0.076
# Lighter nose cone revision: Mass Component 2.8 kg -> 1.0 kg.
# Dry vehicle values read from OpenRocket after recalculation.
ROCKET_DRY_MASS = 41.651
ROCKET_DRY_CG = 2.448
ROCKET_DRY_INERTIA = (78.870, 78.870, 0.151)

# Masses reconstructed from the total mass, CG and inertia stored in the .ork file.
OXIDIZER_MASS = 6.600
FUEL_MASS = 1.8
NITROGEN_MASS = 0.963

def read_eng_burn_time(path):
    """Return the time of the final numerical data point in the RASP .eng curve."""

    last_time = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";"):
            continue
        fields = line.split()
        try:
            last_time = float(fields[0])
            float(fields[1])
        except (IndexError, ValueError):
            continue
    if last_time is None:
        raise ValueError(f"No thrust curve data points found in {path}")
    return last_time


# The burn time updates automatically when NOVA.eng is replaced.
BURN_TIME = read_eng_burn_time(THRUST_FILE)


def build_environment(
    wind_speed=REFERENCE_WIND_SPEED,
    wind_direction_from=REFERENCE_WIND_DIRECTION_FROM,
):
    """Climatological atmosphere for 18 October 2026, 14:00 Europe/Lisbon.

    NOAA NCEP/NCAR 1991-2020: means for 18 October, 13:00 UTC.
    Weather data: 39.388984, -8.288272. Launch site geometry is unchanged.
    This is a historical scenario, not a forecast. See WEATHER_UPDATE.md.
    Explicit wind arguments create a constant-wind variant; pressure
    and temperature still come from the supplied climate profile.
    """
    weather = json.loads(WEATHER_PROFILE_FILE.read_text(encoding="utf-8"))
    profiles = weather["profiles"]
    env = Environment(
        latitude=LAUNCH_LATITUDE,
        longitude=LAUNCH_LONGITUDE,
        elevation=LAUNCH_ELEVATION,
        date=(2026, 10, 18, 14),
        timezone="Europe/Lisbon",
    )

    wind_u = profiles["wind_u"]
    wind_v = profiles["wind_v"]
    surface_u = wind_u[0][1]
    surface_v = wind_v[0][1]
    selected_speed = hypot(surface_u, surface_v)
    if wind_speed is not None or wind_direction_from is not None:
        selected_speed = selected_speed if wind_speed is None else wind_speed
        direction = (
            (degrees(atan2(-surface_u, -surface_v)) + 360.0) % 360.0
            if wind_direction_from is None else wind_direction_from
        )
        wind_u = -selected_speed * sin(radians(direction))
        wind_v = -selected_speed * cos(radians(direction))

    if not 0.0 <= selected_speed <= EUROC_MAX_GROUND_WIND_SPEED:
        raise ValueError(
            f"The EuRoC scenario requires 0 <= wind_speed <= "
            f"{EUROC_MAX_GROUND_WIND_SPEED} m/s"
        )
    env.set_atmospheric_model(
        type="custom_atmosphere",
        pressure=profiles["pressure"],
        temperature=profiles["temperature"],
        wind_u=wind_u,
        wind_v=wind_v,
    )
    return env

def build_environment_pred(delta: int, hour: int):
    today_pt = datetime.datetime.now(pytz.timezone("Europe/Lisbon")).date()
    date = today_pt + datetime.timedelta(days=delta)
    env = Environment(
        latitude=LAUNCH_LATITUDE,
        longitude=LAUNCH_LONGITUDE,
        elevation=LAUNCH_ELEVATION,
        date=(date.year, date.month, date.day, hour),
        timezone="Europe/Lisbon",
    )
    env.set_atmospheric_model(type="windy", file="GFS")
    env.info()
    return env


def _constant_outflow(mass):
    rate = mass / BURN_TIME
    return lambda time: rate if 0 <= time < BURN_TIME else 0.0


def build_motor():
    """Build the liquid propulsion model; dry structure is included in the Rocket mass."""

    oxidizer_geometry = CylindricalTank(radius=0.149 / 2, height=0.62, spherical_caps=False)
    fuel_geometry = CylindricalTank(radius=0.149 / 2, height=0.18, spherical_caps=False)
    nitrogen_geometry = CylindricalTank(radius=0.149 / 2, height=0.61, spherical_caps=False)

    oxidizer_density = CP.PropsSI("D", "T", 293.15, "P", 55e5, "N2O")
    fuel_density = CP.PropsSI("D", "T", 313.15, "P", 1e5, "Ethanol")
    nitrogen_density = CP.PropsSI("D", "T", 263.15, "P", 200e5, "Nitrogen")

    oxidizer_liquid = Fluid("N2O liquid", oxidizer_density)
    oxidizer_gas = Fluid("N2O gas placeholder", oxidizer_density)
    fuel_liquid = Fluid("Ethanol liquid", fuel_density)
    fuel_gas = Fluid("Ethanol gas placeholder", fuel_density)
    nitrogen_liquid = Fluid("Nitrogen liquid placeholder", nitrogen_density)
    nitrogen_gas = Fluid("Nitrogen gas", nitrogen_density)

    zero_flow = lambda _time: 0.0

    oxidizer_tank = MassFlowRateBasedTank(
        name="Oxidiser tank",
        geometry=oxidizer_geometry,
        flux_time=BURN_TIME,
        liquid=oxidizer_liquid,
        gas=oxidizer_gas,
        initial_liquid_mass=OXIDIZER_MASS,
        initial_gas_mass=0.0,
        liquid_mass_flow_rate_in=zero_flow,
        gas_mass_flow_rate_in=zero_flow,
        liquid_mass_flow_rate_out=_constant_outflow(OXIDIZER_MASS),
        gas_mass_flow_rate_out=zero_flow,
    )

    fuel_tank = MassFlowRateBasedTank(
        name="Fuel tank",
        geometry=fuel_geometry,
        flux_time=BURN_TIME,
        liquid=fuel_liquid,
        gas=fuel_gas,
        initial_liquid_mass=FUEL_MASS,
        initial_gas_mass=0.0,
        liquid_mass_flow_rate_in=zero_flow,
        gas_mass_flow_rate_in=zero_flow,
        liquid_mass_flow_rate_out=_constant_outflow(FUEL_MASS),
        gas_mass_flow_rate_out=zero_flow,
    )

    nitrogen_tank = MassFlowRateBasedTank(
        name="Nitrogen tank",
        geometry=nitrogen_geometry,
        flux_time=BURN_TIME,
        liquid=nitrogen_liquid,
        gas=nitrogen_gas,
        initial_liquid_mass=0.0,
        initial_gas_mass=NITROGEN_MASS,
        liquid_mass_flow_rate_in=zero_flow,
        gas_mass_flow_rate_in=zero_flow,
        liquid_mass_flow_rate_out=zero_flow,
        gas_mass_flow_rate_out=_constant_outflow(NITROGEN_MASS),
    )

    motor = LiquidMotor(
        thrust_source=str(THRUST_FILE),
        dry_mass=0.0,
        dry_inertia=(0.0, 0.0, 0.0),
        center_of_dry_mass_position=0.0,
        nozzle_radius=0.072 / 2,
        burn_time=BURN_TIME,
        nozzle_position=0.0,
        coordinate_system_orientation="nozzle_to_combustion_chamber",
    )

    # Positions are measured from the nozzle towards the nose. OpenRocket spreads
    # the mass of auxiliary motors uniformly along the tanks. RocketPy calculates
    # the actual fluid level, so the geometry positions are adjusted to place
    # the initial centres of mass of the fluids at the same locations.
    motor.add_tank(oxidizer_tank, position=0.9116789029522315)
    motor.add_tank(fuel_tank, position=1.501792373375278)
    motor.add_tank(nitrogen_tank, position=2.3222133404771094)
    return motor


def build_rocket(motor):
    """Build the geometry, mass and recovery system for the initial R8 revision."""

    rocket = Rocket(
        radius=ROCKET_RADIUS,
        mass=ROCKET_DRY_MASS,
        inertia=ROCKET_DRY_INERTIA,
        power_off_drag=str(DRAG_FILE),
        power_on_drag=str(DRAG_FILE),
        center_of_mass_without_motor=ROCKET_DRY_CG,
        coordinate_system_orientation="nose_to_tail",
    )

    nose = NoseCone(
        length=0.4896,
        kind="von karman",
        base_radius=ROCKET_RADIUS,
        rocket_radius=ROCKET_RADIUS,
        name="Nose cone",
    )
    forward_fins = TrapezoidalFins(
        n=4,
        root_chord=0.070,
        tip_chord=0.0,
        span=0.060,
        sweep_length=0.070,
        cant_angle=0.0,
        rocket_radius=ROCKET_RADIUS,
        name="Forward fin set",
    )
    main_fins = TrapezoidalFins(
        n=4,
        root_chord=0.235,
        tip_chord=0.110,
        span=0.135,
        sweep_length=0.1255395407249196,
        cant_angle=0.0,
        rocket_radius=ROCKET_RADIUS,
        name="Main fin set",
    )
    tail = Tail(
        top_radius=0.076,
        bottom_radius=0.060,
        length=0.060,
        rocket_radius=ROCKET_RADIUS,
        name="End cone",
    )

    rocket.add_surfaces(
        surfaces=[nose, forward_fins, main_fins, tail],
        # With the "bottom" method, OpenRocket stores fin offsets relative to
        # the trailing edge. RocketPy expects the leading edge of the chord.
        positions=[0.0, 0.8076, 4.1991, 4.5101],
    )
    rocket.add_motor(motor, position=ROCKET_LENGTH)

    rocket.add_parachute(
        name="Pilot Parachute",
        cd_s=1.2 * pi * 1.25**2 / 4,
        trigger="apogee",
        sampling_rate=100,
        lag=1.0,
    )
    def main_parachute_trigger(_pressure, _barometric_height, state):
        # Geometric height of 400 m AGL. This keeps the trigger independent of
        # pressure-to-altitude conversion in the custom validation atmosphere.
        return state[5] < 0 and state[2] - LAUNCH_ELEVATION < 400.0

    rocket.add_parachute(
        name="Main Parachute",
        cd_s=1.0 * pi * 4.5**2 / 4,
        trigger=main_parachute_trigger,
        sampling_rate=100,
        lag=0.0,
    )
    rocket.set_rail_buttons(
        upper_button_position=2.1486,
        lower_button_position=4.0901,
        angular_position=-130.0,
    )
    return rocket


def run_simulation(
    wind_speed=REFERENCE_WIND_SPEED,
    wind_direction_from=REFERENCE_WIND_DIRECTION_FROM,
):
    env = build_environment_pred(1, 15)
    motor = build_motor()
    rocket = build_rocket(motor)
    flight = Flight(
        rocket=rocket,
        environment=env,
        rail_length=LAUNCH_RAIL_LENGTH,
        inclination=LAUNCH_INCLINATION,
        heading=LAUNCH_HEADING,
        terminate_on_apogee=False,
        max_time=600,
    )
    return env, motor, rocket, flight


def print_summary(flight):
    wind_u = flight.env.wind_velocity_x(flight.env.elevation)
    wind_v = flight.env.wind_velocity_y(flight.env.elevation)
    wind_speed = hypot(wind_u, wind_v)
    wind_from = (degrees(atan2(-wind_u, -wind_v)) + 360.0) % 360.0
    print(f"Rocket:               {ROCKET_NAME}")
    print(
        f"Surface wind:         {wind_speed:.1f} m/s from {wind_from:.0f} deg"
    )
    print(f"Launch rail length:   {LAUNCH_RAIL_LENGTH:.2f} m")
    print(f"Loaded mass:          {flight.rocket.total_mass(0):.3f} kg")
    print(f"Initial CG:           {flight.rocket.center_of_mass(0):.3f} m")
    print(f"Apogee AGL:           {flight.apogee - flight.env.elevation:.1f} m")
    print(f"Time to apogee:       {flight.apogee_time:.3f} s")
    print(f"Out-of-rail velocity: {flight.out_of_rail_velocity:.3f} m/s")
    print(f"Maximum speed:        {flight.max_speed:.3f} m/s")
    print(f"Impact velocity:      {flight.impact_velocity:.3f} m/s")
    impact_distance = hypot(flight.x_impact, flight.y_impact)
    print(f"Impact distance:      {impact_distance:.1f} m")
    print("\nEuRoC checks")
    print(
        f"Rail velocity >= {EUROC_MIN_OUT_OF_RAIL_VELOCITY:.1f} m/s: "
        f"{flight.out_of_rail_velocity >= EUROC_MIN_OUT_OF_RAIL_VELOCITY}"
    )
    print(
        f"Rail stability >= {EUROC_MIN_OUT_OF_RAIL_STABILITY:.1f} cal: "
        f"{flight.out_of_rail_stability_margin >= EUROC_MIN_OUT_OF_RAIL_STABILITY}"
    )
    print(
        f"Impact distance <= {EUROC_LAUNCH_SITE_RADIUS:.0f} m: "
        f"{impact_distance <= EUROC_LAUNCH_SITE_RADIUS}"
    )


if __name__ == "__main__":
    _, _, _, simulated_flight = run_simulation()
    print_summary(simulated_flight)
