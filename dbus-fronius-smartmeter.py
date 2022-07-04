#!/usr/bin/env python

"""
Reading information from the Fronius Smart Meter via http REST API and puts the info on dbus.

Created by Ralf Zimmermann (mail@ralfzimmermann.de) in 2020
Credit to Ralf Zimmermann - https://github.com/RalfZim/venus.dbus-fronius-smartmeter
Used https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py as basis for this service.

Amended by Ben De Longis (unifiedcommsguy@gmail.com) in June 2021 to include following features:

- External config file config.py
- Support for all fields in VenusOS Screen (including Power/Current etc)
- Support for single phase meters

This code can be found: https://github.com/unifiedcommsguy/victron-dbus-fronius-smartmeter

Amended by Uli (https://github.com/SirUli) from 2022 on:
- Compatibility with python 3
- Correct display of values in UI
- Installation via SetupHelper (https://github.com/kwindrem/SetupHelper)
"""
from dbus.mainloop.glib import DBusGMainLoop
import config as cfg # import config.py file
from gi.repository import GLib
import platform
import logging
import sys
import os
import requests # for http GET
import _thread   # for daemon = True
from ve_utils import exit_on_error

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))
from vedbus import VeDbusService

class DbusDummyService:
  def __init__(self, servicename, deviceinstance, paths, productname='Fronius Smart Meter', connection='Fronius Smart Meter service'):
    self._dbusservice = VeDbusService(servicename)
    self._paths = paths

    logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

    # Create the management objects, as specified in the ccgx dbus-api document
    self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
    self._dbusservice.add_path('/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
    self._dbusservice.add_path('/Mgmt/Connection', connection)

    # Create the mandatory objects
    self._dbusservice.add_path('/DeviceInstance', deviceinstance)
    self._dbusservice.add_path('/ProductId', 16) # value used in ac_sensor_bridge.cpp of dbus-cgwacs
    self._dbusservice.add_path('/ProductName', productname)
    self._dbusservice.add_path('/FirmwareVersion', 0.1)
    self._dbusservice.add_path('/HardwareVersion', 0)
    self._dbusservice.add_path('/Role', 'grid')
    self._dbusservice.add_path('/Connected', 1)

    _kwh = lambda p, v: (str(v) + 'kWh')
    _a = lambda p, v: (str(v) + 'A')
    _w = lambda p, v: (str(v) + 'W')
    _v = lambda p, v: (str(v) + 'V')
    _s = lambda p, v: (str(v) + 's')
    _x = lambda p, v: (str(v))
    
    self._dbusservice.add_path('/Ac/Energy/Forward', None, gettextcallback=_kwh)
    self._dbusservice.add_path('/Ac/Energy/Reverse', None, gettextcallback=_kwh)
    self._dbusservice.add_path('/Ac/L1/Current', None, gettextcallback=_a)
    self._dbusservice.add_path('/Ac/L1/Energy/Forward', None, gettextcallback=_kwh)
    self._dbusservice.add_path('/Ac/L1/Energy/Reverse', None, gettextcallback=_kwh)
    self._dbusservice.add_path('/Ac/L1/Power', None, gettextcallback=_w)
    self._dbusservice.add_path('/Ac/L1/Voltage', None, gettextcallback=_v)
    self._dbusservice.add_path('/Ac/L2/Current', None, gettextcallback=_a)
    self._dbusservice.add_path('/Ac/L2/Energy/Forward', None, gettextcallback=_kwh)
    self._dbusservice.add_path('/Ac/L2/Energy/Reverse', None, gettextcallback=_kwh)
    self._dbusservice.add_path('/Ac/L2/Power', None, gettextcallback=_w)
    self._dbusservice.add_path('/Ac/L2/Voltage', None, gettextcallback=_v)
    self._dbusservice.add_path('/Ac/L3/Current', None, gettextcallback=_a)
    self._dbusservice.add_path('/Ac/L3/Energy/Forward', None, gettextcallback=_kwh)
    self._dbusservice.add_path('/Ac/L3/Energy/Reverse', None, gettextcallback=_kwh)
    self._dbusservice.add_path('/Ac/L3/Power', None, gettextcallback=_w)
    self._dbusservice.add_path('/Ac/L3/Voltage', None, gettextcallback=_v)
    self._dbusservice.add_path('/Ac/Power', None, gettextcallback=_w)
    self._dbusservice.add_path('/Ac/Current', None, gettextcallback=_a)
    self._dbusservice.add_path('/Ac/Voltage', None, gettextcallback=_v)

    for path, settings in self._paths.items():
      self._dbusservice.add_path(
        path, settings['initial'], writeable=True, onchangecallback=self._handlechangedvalue)

    # pause 200ms before the next request
    GLib.timeout_add(200, exit_on_error, self._update)

  def _update(self):
    URL = "http://" + cfg.fronius["ipaddress"] + "/solar_api/v1/GetMeterRealtimeData.cgi?Scope=Device&DeviceId=0&DataCollection=MeterRealtimeData"
    meter_r = requests.get(url = URL)
    meter_data = meter_r.json()
    MeterModel = meter_data['Body']['Data']['Details']['Model']

    # Common Items
    MeterConsumption = float(meter_data['Body']['Data']['PowerReal_P_Sum'])
    self._dbusservice['/Ac/Power'] = MeterConsumption # positive: consumption, negative: feed into grid
    self._dbusservice['/Ac/Current'] = float(meter_data['Body']['Data']['Current_AC_Sum'])
    self._dbusservice['/Ac/Energy/Forward'] = float(meter_data['Body']['Data']['EnergyReal_WAC_Sum_Consumed']) / 1000
    self._dbusservice['/Ac/Energy/Reverse'] = float(meter_data['Body']['Data']['EnergyReal_WAC_Sum_Produced']) / 1000
    self._dbusservice['/Ac/L1/Voltage'] = float(meter_data['Body']['Data']['Voltage_AC_Phase_1'])
    self._dbusservice['/Ac/L1/Current'] = float(meter_data['Body']['Data']['Current_AC_Phase_1'])
    self._dbusservice['/Ac/L1/Power'] = float(meter_data['Body']['Data']['PowerReal_P_Phase_1'])
    if 'EnergyReal_WAC_Phase_1_Consumed' in meter_data['Body']['Data']:
      self._dbusservice['/Ac/L1/Energy/Forward'] = float(meter_data['Body']['Data']['EnergyReal_WAC_Phase_1_Consumed']) / 1000
    if 'EnergyReal_WAC_Phase_1_Produced' in meter_data['Body']['Data']:
      self._dbusservice['/Ac/L1/Energy/Reverse'] = float(meter_data['Body']['Data']['EnergyReal_WAC_Phase_1_Produced']) / 1000

    if cfg.fronius["numphases"] == '1':
      self._dbusservice['/Ac/L2/Voltage'] = 0.0
      self._dbusservice['/Ac/L3/Voltage'] = 0.0
      self._dbusservice['/Ac/L2/Current'] = 0.0
      self._dbusservice['/Ac/L3/Current'] = 0.0
      self._dbusservice['/Ac/L2/Power'] = 0.0
      self._dbusservice['/Ac/L3/Power'] = 0.0
      self._dbusservice['/Ac/L2/Energy/Forward'] = 0.0
      self._dbusservice['/Ac/L2/Energy/Reverse'] = 0.0
      self._dbusservice['/Ac/L3/Energy/Forward'] = 0.0
      self._dbusservice['/Ac/L3/Energy/Reverse'] = 0.0
    else:
      self._dbusservice['/Ac/L2/Voltage'] = float(meter_data['Body']['Data']['Voltage_AC_Phase_2'])
      self._dbusservice['/Ac/L3/Voltage'] = float(meter_data['Body']['Data']['Voltage_AC_Phase_3'])
      self._dbusservice['/Ac/L2/Current'] = float(meter_data['Body']['Data']['Current_AC_Phase_2'])
      self._dbusservice['/Ac/L3/Current'] = float(meter_data['Body']['Data']['Current_AC_Phase_3'])
      self._dbusservice['/Ac/L2/Power'] = float(meter_data['Body']['Data']['PowerReal_P_Phase_2'])
      self._dbusservice['/Ac/L3/Power'] = float(meter_data['Body']['Data']['PowerReal_P_Phase_3'])
      if 'EnergyReal_WAC_Phase_2_Consumed' in meter_data['Body']['Data']:
        self._dbusservice['/Ac/L2/Energy/Forward'] = float(meter_data['Body']['Data']['EnergyReal_WAC_Phase_2_Consumed']) / 1000
      if 'EnergyReal_WAC_Phase_2_Produced' in meter_data['Body']['Data']:
        self._dbusservice['/Ac/L2/Energy/Reverse'] = float(meter_data['Body']['Data']['EnergyReal_WAC_Phase_2_Produced']) / 1000
      if 'EnergyReal_WAC_Phase_3_Consumed' in meter_data['Body']['Data']:
        self._dbusservice['/Ac/L3/Energy/Forward'] = float(meter_data['Body']['Data']['EnergyReal_WAC_Phase_3_Consumed']) / 1000
      if 'EnergyReal_WAC_Phase_3_Produced' in meter_data['Body']['Data']:
        self._dbusservice['/Ac/L3/Energy/Reverse'] = float(meter_data['Body']['Data']['EnergyReal_WAC_Phase_3_Produced']) / 1000

    logging.info("House Consumption: %s" % (MeterConsumption))
    return True

  def _handlechangedvalue(self, path, value):
    logging.debug("someone else updated %s to %s" % (path, value))
    return True # accept the change

def main():
  logging.basicConfig(level=logging.INFO)
  _thread.daemon = True # allow the program to quit

  # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
  DBusGMainLoop(set_as_default=True)

  pvac_output = DbusDummyService(
    servicename='com.victronenergy.grid.fronius',
    deviceinstance=0,
    paths={
      '/Ac/Power': {'initial': 0},
      '/Ac/Current': {'initial': 0},
      '/Ac/Energy/Forward': {'initial': 0}, # energy bought from the grid
      '/Ac/Energy/Reverse': {'initial': 0}, # energy sold to the grid
      '/Ac/L1/Voltage': {'initial': 0},
      '/Ac/L2/Voltage': {'initial': 0},
      '/Ac/L3/Voltage': {'initial': 0},
      '/Ac/L1/Current': {'initial': 0},
      '/Ac/L2/Current': {'initial': 0},
      '/Ac/L3/Current': {'initial': 0},
      '/Ac/L1/Power': {'initial': 0},
      '/Ac/L2/Power': {'initial': 0},
      '/Ac/L3/Power': {'initial': 0},
      '/Ac/L1/Energy/Forward': {'initial': 0},
      '/Ac/L1/Energy/Reverse': {'initial': 0},
      '/Ac/L2/Energy/Forward': {'initial': 0},
      '/Ac/L2/Energy/Reverse': {'initial': 0},
      '/Ac/L3/Energy/Forward': {'initial': 0},
      '/Ac/L3/Energy/Reverse': {'initial': 0},
    })

  logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
  mainloop = GLib.MainLoop()
  mainloop.run()

if __name__ == "__main__":
  main()
