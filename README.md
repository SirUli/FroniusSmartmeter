# FroniusSmartmeter

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

This script is meant to be installed through the [SetupHelper](https://github.com/kwindrem/SetupHelper) of kwindrem. Use the following details:

- Package Name: `FroniusSmartmeter`
- GitHub User: `SirUli`
- Github branch or tag: `main`

## Configuration

The script should auto-detect the IP of the Fronius device if it is on the same network. Otherwise specify the IP using --ip.

## Service Logs

To see if the service runs without any issues, check the file ``/data/log/FroniusSmartmeter/current``. This should have as last entries something similar to:

```plaintext
@400000006404ec000994a10c *** CCGX booted (0) ***
@400000006404ec5f270ea264 FroniusSmartmeter/setup: --- starting setup script <some version>
@400000006404ec5f31dd6b44 FroniusSmartmeter/setup: ++ Installing Victron Dbus Fronius Smartmeter service
@400000006404ec5f33808c24 FroniusSmartmeter/setup: installing FroniusSmartmeter service - please wait
@400000006404ec6a01738f24 FroniusSmartmeter/setup: completed
```

If the service actually has issues, then check via the process list `ps|grep smartmeter` what this might be (if it isn't in the logs).

Also you can try to start the service manually:

```bash
python /data/FroniusSmartmeter/fronius-smartmeter.py
```

If you really run into trouble, don't hesitate to check the list of [issues here on Github](https://github.com/SirUli/FroniusSmartmeter/issues) to see if anyone else stumbled across that. If not, please open an issue!
