# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import RPi.GPIO as GPIO

INVERT = False
LASER_GPIO = 18
LASER_PWM_FREQ = 60


class GCodeSuperLaserController(octoprint.plugin.StartupPlugin,
                                octoprint.plugin.ShutdownPlugin,
                                octoprint.plugin.SettingsPlugin):

    def __init__(self):
        super().__init__()
        self.output = None
        GPIO.setmode(GPIO.BCM)

    def on_startup(self, host, port):
        gpio = self._settings.get(["gpio"])
        freq = self._settings.get(["pwmFreq"])
        self._logger.info(f"Initializing laser at GPIO {gpio}")
        GPIO.setup(gpio, GPIO.OUT)
        self.output = GPIO.PWM(gpio, freq)
        self.laser_set(0)

    def on_shutdown(self):
        self.output.stop()
        GPIO.cleanup()

    def laser_set(self, power):
        if self.output:
            if power == 0:
                self._logger.debug(f"Laser OFF")
                self.output.stop()
            else:
                self._logger.debug(f"Laser ON ({power}%)")
                self.output.start(power)
        else:
            self._logger.debug(f"Cannot control laser when GPIO is not initialized")

    def get_settings_defaults(self):
        return {
            "gpio": LASER_GPIO,
            "pwmFreq": LASER_PWM_FREQ,
        }

    def hook_gcode_sending(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        parts = cmd.split()
        if gcode in ["M3", "M4"] and len(parts) > 1:

            # Strip leading "S" if present
            power_str = parts[1]
            if power_str.startswith("S"):
                power_str = power_str[1:]

            # Convert to int and check limits
            power_int = int(power_str)
            power_int = min(power_int, 255)
            power_int = max(power_int, 0)

            # Convert to percent
            # RPi.GPIO takes 0.0-100.0 instead of 0-255
            power_percent = power_int * 100 / 255

            if (gcode == "M4") ^ INVERT:
                power_percent = 100.0 - power_percent

            self.laser_set(power_percent)
            return None,  # No need to send command to printer

        if gcode == "M5":
            self.laser_set(0)
            return None,  # No need to send command to printer

    def get_update_information(self):
        return dict(
            GSLC=dict(
                displayName="GSLC",
                displayVersion=self._plugin_version,

                type="github_release",
                current=self._plugin_version,
                user="Brian",
                repo="GCodeSuperLaserController",

                pip="https://github.com/awkwardbunny/GCodeSuperLaserController/archive/{target_version}.zip"
            )
        )


__plugin_name__ = "GCodeSuperLaserController"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = GCodeSuperLaserController()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.sending": __plugin_implementation__.hook_gcode_sending,
    }
