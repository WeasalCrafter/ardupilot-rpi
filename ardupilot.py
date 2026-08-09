#!/usr/bin/env python3
# companion script: records video on the pi while the fc is armed.
# listens for MAV_CMD_VIDEO_START_CAPTURE / MAV_CMD_VIDEO_STOP_CAPTURE commands
# sent by companion.lua on the flight controller over serial4.

import os
import subprocess
import threading
import time
from datetime import datetime

import cv2
from gpiozero import LED
from pymavlink import mavutil
from picamera2 import MappedArray, Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import PyavOutput

SERIAL_PORT = '/dev/ttyAMA0'
BAUD_RATE = 460800
MOUNT_DIR = '/mnt/drone'
VIDEO_SIZE = (1640, 1232)
VIDEO_BITRATE = 10000000
HEARTBEAT_INTERVAL_S = 1.0
STATUS_LED_PIN = 24
VIDEO_LED_PIN = 23
LED_BLINK_INTERVAL_S = 0.5  # 1hz blink (0.5s on, 0.5s off)
HEARTBEAT_TIMEOUT_S = 3.0
SYNC_INTERVAL_S = 5.0

camera = None
recording = False
status_led = LED(STATUS_LED_PIN)
video_led = LED(VIDEO_LED_PIN)


def make_filename():
    # YYMMDD-HHmmSS.mp4, e.g. 260619-214223.mp4
    return datetime.now().strftime('%y%m%d-%H%M%S') + '.mp4'


def draw_timestamp(request):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with MappedArray(request, 'main') as m:
        cv2.putText(m.array, timestamp, (10, VIDEO_SIZE[1] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)


def init_camera():
    global camera
    camera = Picamera2()
    video_config = camera.create_video_configuration(main={'size': VIDEO_SIZE})
    camera.configure(video_config)
    camera.pre_callback = draw_timestamp


def mount_usb_drive():
    # mounts the fstab entry for VIDEO_DIR; requires passwordless sudo for this exact command
    try:
        subprocess.run(['sudo', 'mount', MOUNT_DIR], check=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return False

def unmount_usb_drive():
    # unmounts the fstab entry for VIDEO_DIR; requires passwordless sudo for this exact command
    try:
        subprocess.run(['sudo', 'umount', MOUNT_DIR], check=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return False


def sync_while_recording():
    # periodically flushes encoded video out of the page cache and onto the usb
    # drive so footage survives a power loss that happens mid-recording, since
    # the moov atom alone (frag_keyframe+empty_moov) isn't useful if the data
    # behind it never made it to physical media
    while recording:
        time.sleep(SYNC_INTERVAL_S)
        os.sync()


def start_recording():
    global recording
    if recording:
        return True

    print(f'[COMMAND RECEIVED] Start Recording')

    mount_usb_drive()

    if not os.path.ismount(MOUNT_DIR):
        print('[ERROR] Unable to mount drive (is it plugged in?)')
        return False
    else:
        print('[INFO] Drive successfully mounted')

    filepath = os.path.join(MOUNT_DIR, "videos", make_filename())
    encoder = H264Encoder(bitrate=VIDEO_BITRATE)
    # fragmented mp4: writes the moov atom up front and flushes media in
    # fragments, so the file stays valid/playable even if recording is cut
    # short by a power loss instead of a clean stop_recording() call
    output = PyavOutput(filepath, format='mp4', options={'movflags': 'frag_keyframe+empty_moov'})
    camera.start_recording(encoder, output)
    recording = True
    video_led.blink(on_time=LED_BLINK_INTERVAL_S, off_time=LED_BLINK_INTERVAL_S)
    threading.Thread(target=sync_while_recording, daemon=True).start()
    print(f'[INFO] Outputting to {filepath}')
    return True


def stop_recording():
    global recording

    if not recording:
        return True

    camera.stop_recording()
    recording = False
    video_led.off()
    print('[COMMAND RECEIVED] Stop Recording')

    os.sync()

    if not unmount_usb_drive():
        print('[ERROR] Unable to unmount drive (is it plugged in?)')
        return False
    else:
        print('[INFO] Drive successfully unmounted')

    return True


def send_heartbeats(master):
    # lets companion.lua discover which mavlink channel the pi is on
    while True:
        master.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0, 0,
            mavutil.mavlink.MAV_STATE_ACTIVE)
        time.sleep(HEARTBEAT_INTERVAL_S)


def monitor_heartbeat(master):
    # watches time since the last parsed HEARTBEAT (tracked by pymavlink internally
    # and exposed via time_since, regardless of the type filter used elsewhere by
    # recv_match) and reflects link state on status_led so a dropped uart connection
    # doesn't leave it stuck solid
    link_up = True
    while True:
        time.sleep(1)
        lost = master.time_since('HEARTBEAT') > HEARTBEAT_TIMEOUT_S
        if lost and link_up:
            status_led.blink(on_time=LED_BLINK_INTERVAL_S, off_time=LED_BLINK_INTERVAL_S)
            print('[WARNING] Flight Computer heartbeat lost')
            link_up = False
        elif not lost and not link_up:
            status_led.on()
            print('[INFO] Flight Computer heartbeat restored')
            link_up = True


def main():
    init_camera()

    master = mavutil.mavlink_connection(SERIAL_PORT, baud=BAUD_RATE)
    print('Waiting for Flight Computer heartbeat signal...')
    status_led.blink(on_time=LED_BLINK_INTERVAL_S, off_time=LED_BLINK_INTERVAL_S)
    master.wait_heartbeat()
    status_led.on()
    print('[HEARTBEAT RECEIVED] Flight Computer Connected')

    heartbeat_thread = threading.Thread(target=send_heartbeats, args=(master,), daemon=True)
    heartbeat_thread.start()

    monitor_thread = threading.Thread(target=monitor_heartbeat, args=(master,), daemon=True)
    monitor_thread.start()

    try:
        while True:
            msg = master.recv_match(type='COMMAND_LONG', blocking=True, timeout=1)
            if msg is None:
                continue

            if msg.command == mavutil.mavlink.MAV_CMD_VIDEO_START_CAPTURE:
                success = start_recording()
            elif msg.command == mavutil.mavlink.MAV_CMD_VIDEO_STOP_CAPTURE:
                success = stop_recording()
            else:
                continue

            result = mavutil.mavlink.MAV_RESULT_ACCEPTED if success else mavutil.mavlink.MAV_RESULT_FAILED
            master.mav.command_ack_send(msg.command, result)
    finally:
        stop_recording()


if __name__ == '__main__':
    main()
