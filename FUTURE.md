# FUTURE.md — joystick_drivers

> ROS2 metapackage of joystick/gamepad driver nodes — publishes `sensor_msgs/Joy` from physical input devices (USB gamepad, SpaceNav 6-DOF mouse, PS3 controller, Wiimote).
> Last updated: 2026-03-05

## Purpose
Upstream hardware interface for all joystick/gamepad control pipelines. Bridges Linux input devices to ROS2 topics. The `joy` package (SDL2-based) is the primary driver used with Xbox/generic USB controllers in the STRAPS stack. This is an upstream community package (ros-drivers/joystick_drivers).

## Sub-Packages

| Package | Description |
|---------|-------------|
| `joystick_drivers` | Top-level metapackage (no nodes) |
| `joy` | Generic joystick driver via SDL2; primary package for USB gamepads |
| `joy_linux` | Alternative Linux `/dev/input/jsX` driver (no SDL2 dependency) |
| `ps3joy` | Python driver for PlayStation 3 controller via Bluetooth |
| `spacenav` | Driver for 3D Connexion SpaceNavigator 6-DOF mouse |
| `sdl2_vendor` | CMake vendor package for SDL2 (used by `joy`) |
| `wiimote` | Nintendo Wiimote driver (Bluetooth) |
| `wiimote_msgs` | Custom message types for Wiimote (ImuData, State, TimedSwitch) |

## Nodes

### joy (primary)
| Node | Purpose |
|------|---------|
| `joy_node` | Reads USB gamepad via SDL2, publishes `sensor_msgs/Joy` + `sensor_msgs/JoyFeedback` |
| `joy_enumerate_devices` | CLI tool listing available SDL2 joystick devices |

### joy_linux
| Node | Purpose |
|------|---------|
| `joy_linux_node` | Reads `/dev/input/jsX` directly, publishes `sensor_msgs/Joy` |

### ps3joy
| Node | Purpose |
|------|---------|
| `ps3joy_node.py` | Manages PS3 controller Bluetooth pairing + publishes Joy |

### spacenav
| Node | Purpose |
|------|---------|
| `spacenav_node` | Reads SpaceNavigator USB HID, publishes `geometry_msgs/Vector3` + `sensor_msgs/Joy` |

### wiimote
| Node | Purpose |
|------|---------|
| `wiimote_controller_node` | Lifecycle node — reads Wiimote Bluetooth, publishes IMU + Joy |
| `teleop_wiimote_node` | Converts Wiimote input to `geometry_msgs/Twist` for robot movement |

## Design Pattern

**Event-driven SDL2 poll loop** (`joy`):
- Opens SDL2 joystick device by `device_id` or `device_name`
- `autorepeat_rate` controls how often Joy is published even when no input changes (0 = only on change)
- `coalesce_interval_ms` batches rapid events before publishing
- Supports force-feedback/rumble via `sensor_msgs/JoyFeedback` subscriber

**joy_linux** uses the legacy Linux `/dev/input` ioctl interface — simpler but no rumble/feedback support.

## ROS Interfaces

### joy — Publishers
| Topic | Type | Notes |
|-------|------|-------|
| `joy` | `sensor_msgs/Joy` | Button/axis states |
| `joy/set_feedback` | (sub) | `sensor_msgs/JoyFeedbackArray` — rumble input |

### joy — Parameters
| Param | Default | Description |
|-------|---------|-------------|
| `device_id` | `0` | SDL2 joystick device index |
| `device_name` | `''` | If set, overrides device_id; matches by name |
| `deadzone` | `0.5` | Axis deadzone (0.0–0.9) |
| `autorepeat_rate` | `20.0` | Hz; publish rate even without input changes (0 = event-only) |
| `sticky_buttons` | `false` | If true, button state toggles (latches) instead of momentary |
| `coalesce_interval_ms` | `1` | Batch window for input events before publishing |

### spacenav — Publishers
| Topic | Type | Notes |
|-------|------|-------|
| `spacenav/offset` | `geometry_msgs/Vector3` | Linear 3-DOF |
| `spacenav/rot_offset` | `geometry_msgs/Vector3` | Rotational 3-DOF |
| `spacenav/joy` | `sensor_msgs/Joy` | Combined Joy message |

## Launch Files

```bash
# joy (SDL2, Xbox controller)
ros2 launch joy joy-launch.py

# joy composed (in component container)
ros2 launch joy joy-composed-launch.py

# joy_linux (legacy)
ros2 run joy_linux joy_linux_node

# spacenav
ros2 launch spacenav classic-launch.py

# wiimote
ros2 launch wiimote wiimote_lifecycle.launch.py
```

## Config Files
- `joy/config/joy-params.yaml`: Default params for `joy_node` (device_id=0, deadzone=0.5, autorepeat_rate=20Hz).
- `wiimote/config/wiimote_params.yaml` and `teleop_wiimote_params.yaml`: Wiimote-specific tuning.
- `ps3joy/diagnostics.yaml`: Diagnostics config for PS3 driver.

## Key Dependencies

| Dependency | Usage |
|------------|-------|
| `sdl2_vendor` / `libsdl2-dev` | SDL2 joystick API for `joy` package |
| `libspnav-dev` | SpaceNavigator HID library for `spacenav` |
| `cwiid` | Wiimote Bluetooth library (Python) |

## Build Notes
```bash
rosdep install --from-paths /home/ubuntu/Zelda/Projects/all_repos/joystick_drivers --ignore-src
colcon build --packages-up-to joystick_drivers
```

`sdl2_vendor` is built first as a CMake ExternalProject if system SDL2 is absent. For most Ubuntu systems, `libsdl2-dev` from apt satisfies the dependency.

## Known Issues

| Severity | Description |
|----------|-------------|
| Info | Upstream community package — do not fork. Pin to a release tag. |
| Low | `joy_linux` does not support force-feedback (rumble) — use `joy` (SDL2) for Xbox controller vibration |
| Low | PS3 pairing requires Bluetooth in discoverable mode; driver script runs as root on some systems |
| Info | `wiimote_msgs` are custom types from this repo — not available in the standard ROS distribution |
