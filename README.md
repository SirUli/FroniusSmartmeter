# victron-dbus-fronius-smartmeter

## Purpose

This service is meant to be run on a Raspberry Pi with Venus OS from Victron.

The Python script cyclically reads data from the Fronius SmartMeter via the Fronius REST API and publishes information on the dbus, using the service name com.victronenergy.grid. This makes the Venus OS work as if you had a physical Victron Grid Meter installed.

This service has been modified fromt he original to allow for single phase support and separation of configuration from the service script. It also was updated to include all attributes in the VenusOS dashboard

## Credit

Special thanks goes to the following for the basis of this modified code:
   - Ralf Zimmermann - https://github.com/RalfZim/venus.dbus-fronius-smartmeter
   - VictronEnergy   - https://github.com/victronenergy/velib_python

## Configuration

If you are using the installation script the two parameters (IP Address and Number of Phases) is set automatically.

Typically the IP address for the REST API is that of your inverter connected to the Smart Meter using RS485.

## Installation

### Automatic Installation

1. Logon to VenusOS on Raspberry Pi using SSH as root

2. Run following command:

`bash <(curl -s https://raw.githubusercontent.com/unifiedcommsguy/victron-dbus-fronius-smartmeter/main/install.sh)`

3. Follow prompts and this will automatically download the service files, libraries and make the service persistent after firmware upgrade.

### Semi-Manual Installation

1. Copy `install.sh` from repo to `/tmp`

2. Set execute permissions on file:

`chmod 755 /tmp/install.sh`

3. Run `install.sh`:

`/tmp/install.sh`
   
4. Follow prompts and this will automatically download the service files, libraries and make the service persistent after firmware upgrade.
   
### Full Manual Install

   To be completed

## Operation

### Service Status

You can check the status of the service with svstat:

`svstat /service/dbus-fronius-smartmeter`

### Service Service

To restart the service, run the following command:

`/data/dbus-fronius-smartmeter/kill_me.sh`

### Config Update

If you are required to change the IP Address or Number of phases in your setup, just rerun the installation script again and it will update the service for you automatically.
