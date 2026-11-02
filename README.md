# GTR Autonomous Simulation

A Panda3D simulator for testing interchangeable autonomous vehicle architectures on the GTR track. The simulator owns vehicle dynamics, sensors, time and basic track rules. The included `camera_only/try_1` controller remains stationary; it is a starting example, not an autonomous driving system.

## Install and run

Use Python 3.10 or newer and a desktop with Panda3D graphics support:

```bash
python -m venv .venv
```

Activate the virtual environment (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on macOS/Linux), then run:

```bash
python -m pip install -r requirements.txt
python main.py
```

The window opens in READY with the car stopped. Start initializes the selected architecture and its sensors. A failure stops the run, releases its resources, resets the vehicle and displays the reason. Restart starts a fresh run. Reaching the finish displays FINISHED. Close the window or press Escape to exit.

## Architectures

Run the wizard to list, create, copy or select implementations:

```bash
python architecture_wizard.py
```

Enter names such as `camera_only/try_2` or `camera_and_LiDAR/try_1`. A blank template creates a stationary skeleton; choosing a template copies its configuration and controller, never its datasets. Selection updates `architecture` in the root `config.json`.

Each `architectures/<family>/<implementation>/` contains `config.json`, `controller.py` and `data/`. The controller defines `Controller(config, data_dir)` with `start()`, `update(observation)` and `stop()`. `start` initializes resources; `stop` releases them and flushes any architecture-owned data. `update` may return `None` to retain the previous command, or return:

```python
{"steering_deg": 0.0, "acceleration_mps2": 0.0}
```

Steering is the front road-wheel angle in degrees; positive acceleration accelerates, negative acceleration brakes, and zero does neither. The initial command is zero. Commands outside the shared vehicle limits, non-finite values and controller errors fail the run.

`observation` contains `time_s` and a `sensors` dictionary. Only configured, enabled sensors appear. `camera` holds the latest available read-only RGB NumPy array, with shape `(height, width, 3)` and `uint8` pixels; the same frame is retained until the next capture. `speed_sensor` and `steering_sensor` appear only on steps with new readings, as dictionaries containing their value and `time_s`. An absent or `"enabled": false` sensor is disabled. Sensor settings belong in the architecture's `config.json`; use the existing configuration as an example. The camera mode must have a known horizontal FOV. Camera mounting position `[right, forward, up]` in metres and orientation `[heading, pitch, roll]` in degrees are configured under `simulation.camera_mount` in the root config.

The controller receives no world, vehicle or track objects. It decides when and how to process observations and may save its own data under the supplied `data_dir`. Generated contents of these directories are ignored by Git; existing data is never automatically overwritten or copied by the simulator or wizard. No LiDAR scans are currently simulated.

The root `config.json` holds the shared car, track, physics frequency and road tolerance. Sensor sample rates and camera FPS must not exceed `physics_hz`; sample times are quantized to physics steps. Excessive render delays are capped, so simulation time can lag wall time on a slow machine.

## Checks and limitations

```bash
python -m unittest discover -s tests -v
python tests/graphics_check.py
```

The graphics check opens a real Panda3D window. Vehicle dynamics are a provisional kinematic approximation. The physical camera is a geometric rendering using configured resolution, FOV and mounting; exposure, distortion, noise and other optical effects are not simulated. Road departure uses a sampled rectangular vehicle footprint against the centerline and configurable road tolerance, not collision physics.
