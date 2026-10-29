# ROS 2 Driver for Generic Joysticks and Game Controllers

The joy package contains joy_node, and game_controller node which interface generic joysticks and game controllers to ROS 2. These nodes publish "sensor_msgs/msg/Joy" messages, which contain the state of the devices button and axes. Examples of game controllers are ones that come with recently released game consoles and their after market clones.

The game_controller_node uses SDL2's built device mapping database to give buttons and axes a consistent order in the "sensor_msgs/msg/Joy". Custom mappings can also be supplied using SDL's SDL_GAMECONTROLLERCONFIG environment variable.  A third party tool can be used to create the mapping string. The joy_node supports both joysticks and game controllers but the order that buttons and axes appear with the message will dependend on the manufacturer of the device.

For game_controller_node the following tables detail the indexes of buttons and axes.

| Index | Button |
| -  | - |
| 0  | A (CROSS) |
| 1  | B (CIRCLE) |
| 2  | X (SQUARE) |
| 3  | Y (TRIANGLE) |
| 4  | BACK (SELECT) |
| 5  | GUIDE (Middle/Manufacturer Button) |
| 6  | START |
| 7  | LEFTSTICK |
| 8  | RIGHTSTICK |
| 9  | LEFTSHOULDER |
| 10 | RIGHTSHOULDER |
| 11 | DPAD_UP |
| 12 | DPAD_DOWN |
| 13 | DPAD_LEFT |
| 14 | DPAD_RIGHT |
| 15 | MISC1 (Depends on the controller manufacturer, but is usually at a similar location on the controller as back/start) |
| 16 | PADDLE1 (Upper left, facing the back of the controller if present) |
| 17 | PADDLE2 (Upper right, facing the back of the controller if present) |
| 18 | PADDLE3 (Lower left, facing the back of the controller if present) |
| 19 | PADDLE4 (Lower right, facing the back of the controller if present) |
| 20 | TOUCHPAD (If present. Button status only) |

| Index | Axis |
| - | - |
| 0 | LEFTX |
| 1 | LEFTY |
| 2 | RIGHTX |
| 3 | RIGHTY |
| 4 | TRIGGERLEFT |
| 5 | TRIGGERRIGHT |

For joy_node run `ros2 run joy joy_node` in one terminal and `ros2 topic echo /joy` in another. Pressing buttons and moving sticks can be used to determine at which location they appear in "sensor_msgs/msg/Joy".

## Supported Hardware

This nodes should work with any joystick or game controller that is supported by SDL.

## Published Topics

* joy ([sensor_msgs/msg/Joy](http://docs.ros.org/api/sensor_msgs/html/msg/Joy.html)): outputs the joystick state.

## Subscribed Topics
* joy/set_feedback ([sensor_msgs/msg/JoyFeedback](http://docs.ros.org/api/sensor_msgs/html/msg/JoyFeedback.html): Controls the "rumble" device of a joystick, if it has one.

## Parameters

* device_id (int, default: 0)
  * The joystick device to use. `ros2 run joy joy_enumerate_devices` wil list the attached devices.

* device_name (string, default: "")
  * The joystick name to use.  This can be useful when multiple different joysticks are attached.  If both device_name and device_id are specified, device_name takes precedence.

* deadzone (double, default: 0.05)
  * Amount by which the joystick has to move before it is considered to be off-center. This parameter is specified relative to an axis normalized between -1 and 1. Thus, 0.1 means that the joystick has to move 10% of the way to the edge of an axis's range before that axis will output a non-zero value.

* autorepeat_rate (double, default: 20.0)
  * Rate in Hz at which a joystick that has a non-changing state will resend the previously sent message.  If set to 0.0, autorepeat will be disabled, meaning joy messages will only be published when the joystick changes.  Cannot be larger than 1000.0.

* sticky_buttons (bool, default: false)
  * Whether buttons are "sticky".  If this is false (the default), then a button press will result in a 1 being output, and a button release will result in a 0 being output.  If this is true, then a button press will toggle the current state of the button, and a button release will do nothing.  Thus, hitting the button while it is currently 0 will switch it to 1, and keep it at 1 until the button is pressed again.

* coalesce_interval_ms (int, default: 1)
  * The number of milliseconds to wait after an axis event before publishing a message.  Since the kernel sends an event for every change, this can significantly reduce the number of messages published.  Setting it to 0 disables this behavior.  The default of 1 ms is a good compromise between message delays and number of messages published.

## Technical note about interfacing with joysticks and game controllers on Linux

On Linux there are two different ways to interface with a joystick.  The distinction only makes a difference when attempting to pass through the device into a container or virtual machine.  The first interface is via the joystick driver subsystem, which generally shows up as a device in /dev/input/js0 (or other numbers at the end).  This is the way that the "joy_linux" package accesses the joystick.  The second way to interface is through the generic event subsystem, which generally shows up as /dev/input/event7 (or other numbers at the end).  This is the way that SDL (and hence this "joy" package) accesses the joysticks.

## Explicit center calibration (`joy_node`)

`axis_centers` is an optional array of per-axis centers in normalized **SDL raw**
coordinates (-1 to +1), before the driver's ROS sign inversion and deadzone. Missing
entries default to zero. Each side is scaled separately around the supplied center,
so both full-deflection endpoints remain +/-1. Values must be finite and strictly
between -1 and +1. Only physical axes are calibrated; synthetic hat axes are unchanged.
This parameter is read at startup; a new calibration takes effect after restarting
the reader. The existing `deadzone` is applied after centering and must be in [0,1).
Default empty centers preserve the original conversion. `game_controller_node` is unchanged.

Stop joystick forwarding to any robot before calibrating. The calibration utility
opens SDL directly and **does not publish ROS messages**:

```bash
ros2 run joy joy_calibrate.py --list
ros2 run joy joy_calibrate.py \
  --device-path /dev/input/by-path/<controller>-event-joystick \
  --axes 0,1 --duration 3 --output yawman-left.yaml
ros2 run joy joy_node --ros-args --params-file yawman-left.yaml
```

For the observed Yawman, physical axes 0/1 are the spring-centered thumbstick.
SDL reports six physical axes plus one hat; ROS axes 6/7 are synthetic hat values
and must not be included in physical-axis calibration.
Do not calibrate throttle or trigger axes as centered sticks. Hold selected axes
released throughout sampling. The tool rejects a selected axis with more than 0.04
raw normalized movement or a center offset above 0.25 (both thresholds configurable),
and aborts on disconnect. It writes zero offsets for all unselected axes and never
overwrites an existing file. Recheck neutral after several movements/releases;
a stable biased sample does not prove the operator released the stick.

### Two identical controllers

`device_path` selects the exact SDL device path or a symlink resolving to it, taking
precedence over `device_name`, the legacy `dev_ff`, and `device_id`. Use the path shown
by `joy_calibrate.py --list`; on Linux this is generally an input event device. A
`/dev/input/by-path/...-event-joystick` link is stable for a fixed USB socket/topology.
It identifies the socket, not the physical unit if controllers are swapped.

Names and GUIDs may be identical between controllers; enumeration indexes can change.
Serial strings are listed when SDL exposes them, but must be checked for uniqueness.
A name matching multiple attached devices is rejected instead of choosing the first.
Use two different paths and two different parameter files, with distinct ROS namespaces
and topics for two readers. The utility stores the selected device_path in the generated
file, binding its calibration to that selector. It does not configure a second routing
pipeline or decide which robot each controller drives.
