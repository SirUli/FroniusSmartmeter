#!/usr/bin/env python

"""
Created by Ralf Zimmermann (mail@ralfzimmermann.de) in 2020. The original code
and its documentation can be found on:
 - https://github.com/RalfZim/venus.dbus-fronius-smartmeter
This code was created from different sources:
- [https://github.com/RalfZim/venus.dbus-fronius-smartmeter](https://github.com/RalfZim/venus.dbus-fronius-smartmeter)
- [https://github.com/unifiedcommsguy/victron-dbus-fronius-smartmeter](https://github.com/unifiedcommsguy/victron-dbus-fronius-smartmeter)
- [https://github.com/ayasystems/dbus-fronius-smart-meter](https://github.com/ayasystems/dbus-fronius-smart-meter)
- [https://github.com/trixing/venus.dbus-fronius-smartmeter](https://github.com/trixing/venus.dbus-fronius-smartmeter)
- [https://github.com/victronenergy/velib_python](https://github.com/victronenergy/velib_python)
Used https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py as basis for this service.
Reading information from the Fronius Smart Meter via http REST API and puts the info on dbus.
"""
try:
    import gobject
except ImportError:
    from gi.repository import GLib as gobject
import dbus
import json
import logging
import platform
import socket
import sys
import time
import os
import requests  # for http GET

try:
    import thread  # for daemon = True
except ImportError:
    import _thread as thread  # for daemon = True  / Python 3.x

# our own packages
sys.path.insert(
    1, os.path.join(os.path.sep, "data", "SetupHelper", "ext", "velib_python")
)
from vedbus import VeDbusService, VeDbusItemImport

log = logging.getLogger("DbusFroniusSmartMeter")
path_UpdateIndex = "/UpdateIndex"


class DbusFroniusService:
    def role_changed(self, path, val):
        if val not in self.allowed_roles:
            return False
        old, inst = self.get_role_instance()
        self.settings["instance"] = "%s:%s" % (val, inst)
        return True

    def get_role_instance(self):
        val = self.settings["instance"].split(":")
        return val[0], int(val[1])

    def detect(self):

        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        client.settimeout(5)
        client.bind(("", 50050))
        for i in range(1, 5):
            log.info("Detect, try %d" % i)
            client.sendto(
                '{"GetFroniusLoggerInfo":"all"}'.encode("utf-8"),
                ("255.255.255.255", 50049),
            )
            try:
                data, addr = client.recvfrom(1024)
            except socket.timeout:
                continue
            info = json.loads(data)
            sw = info.get("LoggerInfo", {}).get("SoftwareVersion", None)
            if sw:
                self._firmware = ".".join(
                    str(s)
                    for s in [sw["Major"], sw["Minor"], sw["Release"], sw["Build"]]
                )
            log.info("Found device @%s, firmware %s" % (addr[0], self._firmware))
            return addr[0]
        return None

    def detect_dbus(self):
        dbusConn = (
            dbus.SessionBus()
            if "DBUS_SESSION_BUS_ADDRESS" in os.environ
            else dbus.SystemBus()
        )
        if not dbusConn:
            return None
        for name in dbusConn.list_names():
            if name.startswith("com.victronenergy.pvinverter."):
                log.info("Getting IP from %s" % name)
                conn = VeDbusItemImport(dbusConn, name, "/Mgmt/Connection").get_value()
                self._firmware = VeDbusItemImport(
                    dbusConn, name, "/DataManagerVersion"
                ).get_value()
                log.info("Connection Info: %s, Firmware %s" % (conn, self._firmware))
                return conn.split(" ")[0]
        return None

    def __init__(self, servicename, deviceinstance, ip=None):
        self.settings = {"instance": "grid:%d" % deviceinstance}

        self._latency = None
        self._firmware = "0.1"
        self._testdata = None
        if ip == "test":
            self._testdata = "testdata/GetMeterRealtimeData.cgi"

        self._ip = ip or self.detect_dbus() or self.detect()
        self._url = (
            "http://"
            + self._ip
            + "/solar_api/v1/GetMeterRealtimeData.cgi?"
            + "Scope=Device&DeviceId=0&DataCollection=MeterRealtimeData"
        )
        data = self._get_meter_data()

        log.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

        self._dbusservice = VeDbusService(servicename)
        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path("/Mgmt/ProcessName", __file__)
        self._dbusservice.add_path(
            "/Mgmt/ProcessVersion", "Running on Python " + platform.python_version()
        )
        self._dbusservice.add_path("/Mgmt/Connection", self._ip)

        # Create the mandatory objects
        self._dbusservice.add_path("/DeviceInstance", deviceinstance)
        self._dbusservice.add_path(
            "/ProductId", 16
        )  # value used in ac_sensor_bridge.cpp of dbus-cgwacs
        self._dbusservice.add_path(
            "/ProductName",
            data["Details"]["Manufacturer"] + " " + data["Details"]["Model"],
        )
        self._dbusservice.add_path("/FirmwareVersion", self._firmware)
        self._dbusservice.add_path("/HardwareVersion", data["Details"]["Serial"])
        self._dbusservice.add_path("/Connected", 1)

        self.allowed_roles = ["grid", "pvinverter", "genset"]
        self.default_role = "grid"
        self.role = self.default_role
        self._dbusservice.add_path("/AllowedRoles", self.allowed_roles)
        self._dbusservice.add_path(
            "/Role", self.role, writeable=True, onchangecallback=self.role_changed
        )

        _kwh = lambda p, v: (str(round(v, 2) or '') + "kWh")
        _a = lambda p, v: (str(round(v, 1) or '') + "A")
        _w = lambda p, v: (str(round(v, 1) or '') + "W")
        _v = lambda p, v: (str(round(v, 1) or '') + "V")
        _ms = lambda p, v: (str(v or '') + "ms")
        _hz = lambda p, v: (str(v or '') + "Hz")
        _x = lambda p, v: (str(v or ''))

        self._paths = {
            "/Ac/Power": {"initial": 0, "textformat": _w},
            "/Ac/Current": {"initial": 0, "textformat": _a},
            "/Ac/Frequency": {"initial": 0, "textformat": _hz},
            "/Ac/L1/Voltage": {"initial": 0, "textformat": _v},
            "/Ac/L2/Voltage": {"initial": 0, "textformat": _v},
            "/Ac/L3/Voltage": {"initial": 0, "textformat": _v},
            "/Ac/L1/Current": {"initial": 0, "textformat": _a},
            "/Ac/L2/Current": {"initial": 0, "textformat": _a},
            "/Ac/L3/Current": {"initial": 0, "textformat": _a},
            "/Ac/L1/Power": {"initial": 0, "textformat": _w},
            "/Ac/L2/Power": {"initial": 0, "textformat": _w},
            "/Ac/L3/Power": {"initial": 0, "textformat": _w},
            "/Ac/Energy/Forward": {
                "initial": 0,
                "textformat": _kwh,
            },  # energy bought from the grid
            "/Ac/Energy/Reverse": {
                "initial": 0,
                "textformat": _kwh,
            },  # energy sold to the grid
            "/Ac/L1/Energy/Forward": {"initial": 0, "textformat": _kwh},
            "/Ac/L2/Energy/Forward": {"initial": 0, "textformat": _kwh},
            "/Ac/L3/Energy/Forward": {"initial": 0, "textformat": _kwh},
            "/Ac/L1/Energy/Reverse": {"initial": 0, "textformat": _kwh},
            "/Ac/L2/Energy/Reverse": {"initial": 0, "textformat": _kwh},
            "/Ac/L3/Energy/Reverse": {"initial": 0, "textformat": _kwh},
            "/Latency": {"initial": 0, "textformat": _ms},
            path_UpdateIndex: {"initial": 0, "textformat": _x},
        }

        for path, settings in self._paths.items():
            self._dbusservice.add_path(
                path,
                settings["initial"],
                gettextcallback=settings["textformat"],
                writeable=True,
                onchangecallback=self._handlechangedvalue,
            )

        self._retries = 0
        self._failures = 0
        self._latency = None
        gobject.timeout_add(700, self._safe_update)

    def _handlechangedvalue(self, path, value):
        log.debug("someone else updated %s to %s" % (path, value))
        return True  # accept the change

    def _safe_update(self):
        try:
            self._update()
            self._retries = 0
        except Exception as e:
            log.error("Error running update %s" % e)
            self._retries += 1
            self._failures += 1
            if self._retries > 10:
                log.error("Number of retries exceeded.")
                sys.exit(1)
        return True

    def _get_meter_data(self):
        now = time.time()
        if self._testdata:
            meter_r = json.loads(open("testdata/GetMeterRealtimeData.json").read())
        else:
            meter_r = requests.get(url=self._url, timeout=10).json()
        latency = time.time() - now
        if self._latency:
            self._latency = (9 * self._latency + latency) / 10
        else:
            self._latency = latency

        return meter_r["Body"]["Data"]

    def _update(self):
        meter_data = self._get_meter_data()
        meter_consumption = meter_data["PowerReal_P_Sum"]
        meter_model = meter_data["Details"]["Model"]
        if meter_model == "Smart Meter TS 65A-3":
            # Device doesn't feature data for various paths
            self._dbusservice["/Ac/L1/Energy/Forward"] = None
            self._dbusservice["/Ac/L1/Energy/Reverse"] = None
            self._dbusservice["/Ac/L2/Energy/Forward"] = None
            self._dbusservice["/Ac/L2/Energy/Reverse"] = None
            self._dbusservice["/Ac/L3/Energy/Forward"] = None
            self._dbusservice["/Ac/L3/Energy/Reverse"] = None
        if meter_model == 'Smart Meter TS 100A-1' or meter_model == "Smart Meter 63A-1":  # set values for single phase meter
            meter_data["Voltage_AC_Phase_2"] = 0
            meter_data["Voltage_AC_Phase_3"] = 0
            meter_data["Current_AC_Phase_2"] = 0
            meter_data["Current_AC_Phase_3"] = 0
            meter_data["PowerReal_P_Phase_2"] = 0
            meter_data["PowerReal_P_Phase_3"] = 0
            self._dbusservice["/Ac/L2/Energy/Forward"] = None
            self._dbusservice["/Ac/L2/Energy/Reverse"] = None
            self._dbusservice["/Ac/L3/Energy/Forward"] = None
            self._dbusservice["/Ac/L3/Energy/Reverse"] = None
        self._dbusservice["/Ac/Frequency"] = meter_data["Frequency_Phase_Average"]
        self._dbusservice["/Ac/L1/Voltage"] = meter_data["Voltage_AC_Phase_1"]
        self._dbusservice["/Ac/L2/Voltage"] = meter_data["Voltage_AC_Phase_2"]
        self._dbusservice["/Ac/L3/Voltage"] = meter_data["Voltage_AC_Phase_3"]
        self._dbusservice["/Ac/Current"] = meter_data["Current_AC_Sum"]
        self._dbusservice["/Ac/L1/Current"] = meter_data["Current_AC_Phase_1"]
        self._dbusservice["/Ac/L2/Current"] = meter_data["Current_AC_Phase_2"]
        self._dbusservice["/Ac/L3/Current"] = meter_data["Current_AC_Phase_3"]
        # positive: consumption, negative: feed into grid
        self._dbusservice["/Ac/Power"] = meter_consumption
        self._dbusservice["/Ac/L1/Power"] = meter_data["PowerReal_P_Phase_1"]
        self._dbusservice["/Ac/L2/Power"] = meter_data["PowerReal_P_Phase_2"]
        self._dbusservice["/Ac/L3/Power"] = meter_data["PowerReal_P_Phase_3"]
        self._dbusservice["/Ac/Energy/Forward"] = (
            float(meter_data["EnergyReal_WAC_Sum_Consumed"]) / 1000.0
        )
        self._dbusservice["/Ac/Energy/Reverse"] = (
            float(meter_data["EnergyReal_WAC_Sum_Produced"]) / 1000.0
        )
        if "EnergyReal_WAC_Phase_1_Consumed" in meter_data:
            self._dbusservice["/Ac/L1/Energy/Forward"] = (
                float(meter_data["EnergyReal_WAC_Phase_1_Consumed"]) / 1000
            )
        if "EnergyReal_WAC_Phase_1_Produced" in meter_data:
            self._dbusservice["/Ac/L1/Energy/Reverse"] = (
                float(meter_data["EnergyReal_WAC_Phase_1_Produced"]) / 1000
            )
        if "EnergyReal_WAC_Phase_2_Consumed" in meter_data:
            self._dbusservice["/Ac/L2/Energy/Forward"] = (
                float(meter_data["EnergyReal_WAC_Phase_2_Consumed"]) / 1000
            )
        if "EnergyReal_WAC_Phase_2_Produced" in meter_data:
            self._dbusservice["/Ac/L2/Energy/Reverse"] = (
                float(meter_data["EnergyReal_WAC_Phase_2_Produced"]) / 1000
            )
        if "EnergyReal_WAC_Phase_3_Consumed" in meter_data:
            self._dbusservice["/Ac/L3/Energy/Forward"] = (
                float(meter_data["EnergyReal_WAC_Phase_3_Consumed"]) / 1000
            )
        if "EnergyReal_WAC_Phase_3_Produced" in meter_data:
            self._dbusservice["/Ac/L3/Energy/Reverse"] = (
                float(meter_data["EnergyReal_WAC_Phase_3_Produced"]) / 1000
            )
        self._dbusservice["/Latency"] = self._latency
        log.info(
            "Meter Power: %s, Latency: %.1fms"
            % (meter_consumption, self._latency * 1000)
        )
        # increment UpdateIndex - to show that new data is available
        index = self._dbusservice[path_UpdateIndex] + 1  # increment index
        if index > 255:  # maximum value of the index
            index = 0  # overflow from 255 to 0
        self._dbusservice[path_UpdateIndex] = index
        return meter_data


def main():
    # logging.basicConfig(level=logging.INFO)

    root = logging.getLogger()
    # Log Level logging.INFO to get more details
    root.setLevel(logging.ERROR)

    handler = logging.StreamHandler(sys.stdout)
    # Log Level logging.INFO to get more details
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        "%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    log.info("Startup")

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ip",
        help='IP Address of Smart Meter, leave empty to autodetect, specify "test" to use canned data',
    )
    args = parser.parse_args()
    if args.ip:
        log.info("User supplied IP: %s" % args.ip)
    else:
        log.info("Auto detecting IP")

    try:
        thread.daemon = True  # allow the program to quit
    except NameError:
        # Python 3
        pass

    from dbus.mainloop.glib import DBusGMainLoop

    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    pvac_output = DbusFroniusService(
        servicename="com.victronenergy.grid.fronius", deviceinstance=40, ip=args.ip
    )

    logging.info(
        "Connected to dbus, and switching over to gobject.MainLoop() (= event based)"
    )
    mainloop = gobject.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()
