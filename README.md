# victron-dbus-fronius-smartmeter

## Purpose

This service is meant to be run on a Raspberry Pi with Venus OS from Victron.

The Python script periodically reads data from a Fronius SmartMeter via the Fronius REST API and publishes information on the dbus. This makes the Venus OS work as if you had a Victron Grid Meter installed.

This service has been modified from the original to allow for single phase support and separation of configuration from the service script. It also was updated to include all attributes in the VenusOS dashboard

## Credit

Special thanks goes to the following for the basis of this modified code:

- [https://github.com/RalfZim/venus.dbus-fronius-smartmeter](https://github.com/RalfZim/venus.dbus-fronius-smartmeter)
- [https://github.com/unifiedcommsguy/victron-dbus-fronius-smartmeter](https://github.com/unifiedcommsguy/victron-dbus-fronius-smartmeter)
- [https://github.com/ayasystems/dbus-fronius-smart-meter](https://github.com/ayasystems/dbus-fronius-smart-meter)
- [https://github.com/trixing/venus.dbus-fronius-smartmeter](https://github.com/trixing/venus.dbus-fronius-smartmeter)
- [https://github.com/victronenergy/velib_python](https://github.com/victronenergy/velib_python)

## Installation

This script is meant to be installed through the [SetupHelper](https://github.com/kwindrem/SetupHelper) of kwindrem.

## Configuration

The script should auto-detect the IP of the Fronius device if it is on the same network. Otherwise specify the IP using --ip.

## Operation

### Service Status

You can check the status of the service with svstat:

`svstat /service/victron-dbus-fronius-smartmeter`

### Service Service

To restart the service, run the following command:

`/data/victron-dbus-fronius-smartmeter/kill_me.sh`
