#!/usr/bin/env python3
"""Sample a stationary SDL joystick and write joy_node center parameters; publishes nothing."""
import argparse
import ctypes
import ctypes.util
import json
import math
from pathlib import Path
import sys
import time


def load_sdl():
    lib = ctypes.CDLL(ctypes.util.find_library('SDL2') or 'libSDL2-2.0.so.0')
    for name, result, args in [
        ('SDL_Init', ctypes.c_int, [ctypes.c_uint32]),
        ('SDL_NumJoysticks', ctypes.c_int, []),
        ('SDL_JoystickNameForIndex', ctypes.c_char_p, [ctypes.c_int]),
        ('SDL_JoystickPathForIndex', ctypes.c_char_p, [ctypes.c_int]),
        ('SDL_JoystickOpen', ctypes.c_void_p, [ctypes.c_int]),
        ('SDL_JoystickGetSerial', ctypes.c_char_p, [ctypes.c_void_p]),
        ('SDL_JoystickNumAxes', ctypes.c_int, [ctypes.c_void_p]),
        ('SDL_JoystickNumHats', ctypes.c_int, [ctypes.c_void_p]),
        ('SDL_JoystickGetAxis', ctypes.c_int16, [ctypes.c_void_p, ctypes.c_int]),
        ('SDL_JoystickGetAttached', ctypes.c_int, [ctypes.c_void_p]),
        ('SDL_JoystickClose', None, [ctypes.c_void_p]),
        ('SDL_JoystickUpdate', None, []),
        ('SDL_Quit', None, []),
        ('SDL_GetError', ctypes.c_char_p, []),
    ]:
        function = getattr(lib, name)
        function.restype = result
        function.argtypes = args
    if lib.SDL_Init(0x200) != 0:  # SDL_INIT_JOYSTICK, no ROS participant or haptics
        raise RuntimeError(lib.SDL_GetError().decode())
    return lib


def text(value):
    return value.decode() if value else ''


def estimate_centers(samples, axes, max_span, max_offset):
    count = len(samples[0])
    if not axes or len(set(axes)) != len(axes) or any(a < 0 or a >= count for a in axes):
        raise ValueError('Select distinct valid axis indexes')
    result = [0.0] * count
    for axis in axes:
        values = [row[axis] for row in samples]
        center = sum(values) / len(values)
        if max(values) - min(values) > max_span:
            raise ValueError(f'Axis {axis} moved during sampling; release the stick and retry')
        if abs(center) > max_offset:
            raise ValueError(f'Axis {axis} is too far from center; check axis choice and release it')
        result[axis] = round(center, 8)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='list SDL names, paths and serials')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--device-path', help='SDL device path or stable by-path event-joystick link')
    selection.add_argument('--device-name', help='must identify exactly one attached joystick')
    parser.add_argument('--axes', default='0,1', help='released physical stick axis indexes only; Yawman thumbstick: 0,1')
    parser.add_argument('--duration', type=float, default=3.0)
    parser.add_argument('--max-span', type=float, default=0.04)
    parser.add_argument('--max-offset', type=float, default=0.25)
    parser.add_argument('--output', type=Path, help='new YAML parameter file; never overwrites a file')
    args = parser.parse_args()
    if not args.list and (args.output is None or not (args.device_path or args.device_name)):
        parser.error('--output and one device selector are required unless --list is used')
    if any(not math.isfinite(v) for v in (args.duration, args.max_span, args.max_offset)) or \
            not 0.5 <= args.duration <= 30 or not 0 < args.max_span <= 1 or \
            not 0 < args.max_offset < 1:
        parser.error('duration must be 0.5..30 s; max-span in (0,1]; max-offset in (0,1)')
    lib = load_sdl()
    handle = None
    try:
        devices = []
        for index in range(lib.SDL_NumJoysticks()):
            devices.append({'index': index, 'name': text(lib.SDL_JoystickNameForIndex(index)),
                            'path': text(lib.SDL_JoystickPathForIndex(index))})
        if args.list:
            for device in devices:
                handle = lib.SDL_JoystickOpen(device['index'])
                if handle:
                    device['serial'] = text(lib.SDL_JoystickGetSerial(handle))
                    device['axes'] = lib.SDL_JoystickNumAxes(handle)
                    device['hats'] = lib.SDL_JoystickNumHats(handle)
                    lib.SDL_JoystickClose(handle)
                    handle = None
                print(json.dumps(device))
            return
        matches = [d for d in devices if
                   (args.device_path and d['path'] and
                    Path(d['path']).resolve() == Path(args.device_path).resolve()) or
                   (args.device_name and d['name'] == args.device_name)]
        if len(matches) != 1:
            raise ValueError(f'Selector matched {len(matches)} devices; use --list and --device-path')
        handle = lib.SDL_JoystickOpen(matches[0]['index'])
        if not handle:
            raise RuntimeError(text(lib.SDL_GetError()))
        count = lib.SDL_JoystickNumAxes(handle)
        if count <= 0:
            raise ValueError('Joystick exposes no axes')
        axes = [int(a) for a in args.axes.split(',')]
        if not axes or len(set(axes)) != len(axes) or any(a < 0 or a >= count for a in axes):
            raise ValueError('Select distinct valid axis indexes')
        print(f'Keep selected stick axes released for {args.duration}s. Sampling now.', file=sys.stderr)
        samples = []
        until = time.monotonic() + args.duration
        while time.monotonic() < until:
            lib.SDL_JoystickUpdate()
            if not lib.SDL_JoystickGetAttached(handle):
                raise RuntimeError('Joystick disconnected; no calibration saved')
            samples.append([max(-32767, lib.SDL_JoystickGetAxis(handle, a)) / 32767.0
                            for a in range(count)])
            time.sleep(0.01)
        centers = estimate_centers(samples, axes, args.max_span, args.max_offset)
        # JSON arrays/strings are valid YAML, without needing PyYAML installed.
        data = '# SDL axis centers before ROS sign inversion; selected axes ' + str(axes) + '\n'
        data += '/**:\n  ros__parameters:\n    axis_centers: ' + json.dumps(centers) + '\n'
        if args.device_path:
            data += '    device_path: ' + json.dumps(args.device_path) + '\n'
        with args.output.open('x') as output:
            output.write(data)
        print(f'Saved {args.output}: axis_centers={centers}')
    finally:
        if handle:
            lib.SDL_JoystickClose(handle)
        lib.SDL_Quit()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError) as error:
        print(f'Calibration failed: {error}', file=sys.stderr)
        sys.exit(1)
