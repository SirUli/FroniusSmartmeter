#!/bin/sh

# Get IP Address for Fronius Smart Meter
echo "|==============================================================================="
echo "| Please enter the IP Address of the Fronius Smart Meter"
echo "| (typically this is same IP as Grid Connected Inverter)"
echo "|"
read -p "| IP Address: " IPADDRESS
echo "|"

# Number of Phases of Smart Meter
echo "| Please enter the number of Phases supported by the"
echo "| Fronius Smart Meter (1 or 3)"
read -p "| Num of Phases (1,3): " NUMPHASES
echo "|"
echo "|==============================================================================="
# Set Install Directory
ROOT_PATH=/data/dbus-fronius-smartmeter

# Set URL Prefixes
GIT_FRONIUS=https://raw.githubusercontent.com/unifiedcommsguy/victron-dbus-fronius-smartmeter/main
GIT_VICTRON=https://raw.githubusercontent.com/victronenergy/velib_python/master

# Create installation Path
mkdir -p ${ROOT_PATH}/service

# Get Service Files from GitHub
echo "| - Downloading files..."
wget ${GIT_FRONIUS}/dbus-fronius-smartmeter.py -O ${ROOT_PATH}/dbus-fronius-smartmeter.py 2> /dev/null
wget ${GIT_FRONIUS}/config.py -O ${ROOT_PATH}/config.py 2> /dev/null
wget ${GIT_FRONIUS}/kill_me.sh -O ${ROOT_PATH}/kill_me.sh 2> /dev/null
wget ${GIT_FRONIUS}/service/run -O ${ROOT_PATH}/service/run 2> /dev/null

# Set Permissions on files
echo "| - Setting permissions..."
chmod 755 ${ROOT_PATH}/service/run
chmod 744 ${ROOT_PATH}/kill_me.sh

# Get library files from velib_python from victronenergy
echo "| - Downloading libraries..."
wget ${GIT_VICTRON}/vedbus.py -O ${ROOT_PATH}/vedbus.py 2> /dev/null
wget ${GIT_VICTRON}/ve_utils.py -O ${ROOT_PATH}/ve_utils.py 2> /dev/null

# Update config files
echo "| - Updating config file..."
sed -i "s|###IPADDRESS###|${IPADDRESS}|g" -i ${ROOT_PATH}/config.py
sed -i "s|###NUMPHASES###|${NUMPHASES}|g" -i ${ROOT_PATH}/config.py

# Kill Running Service
echo "| - Kill Running Service..."
${ROOT_PATH}/kill_me.sh

# Activate Service
echo "| - Activating service..."
ln -s ${ROOT_PATH}/service /service/dbus-fronius-smartmeter 2> /dev/null

# Configure service to persist firmware upgrade
echo "| - Configuring service persistence..."
if grep -Fxq "# Fronius Smart Meter DBUS Service - Persistence" /data/rc.local
then
	echo -n ""
else
	echo "# Fronius Smart Meter DBUS Service - Persistence" >> /data/rc.local
fi

if grep -Fxq "ln -s ${ROOT_PATH}/service /service/dbus-fronius-smartmeter" /data/rc.local
then
	echo -n ""
else
	echo "ln -s ${ROOT_PATH}/service /service/dbus-fronius-smartmeter" >> /data/rc.local
fi

# Wait 5 Seconds
sleep 5

# Checking service Status
echo "| - Checking if service is running..."
echo -n "| "
svstat /service/dbus-fronius-smartmeter
echo "|==============================================================================="
