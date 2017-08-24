import json
import requests
import datetime
import logging


def to_celcius(value):
    return (value - 32)/1.8


class IBCBoiler(object):

    class Temperature(object):
        Celcius = 1
        Fahrenheight = 2

    class Status(object):
        Heating = "Heating"
        Circulating = "Circulating"
        Standby = "Standby"
        Purging = "Purging"
        Igniting = "Igniting"
        Initializing = "Initializing"

    class ObjectCodes(object):
        IBC_MASTER_BOILER_DATA = 2
        IBC_BOILER_STATUS_DATA = 3
        IBC_BOILER_RUN_PROFILE_DATA = 5
        IBC_BOILER_LOG_DATA = 6
        IBC_BOILER_BOILER_DATA = 11
        IBC_BOILER_STANDARD_DATA = 13
        IBC_BOILER_ADV_SETTINGS_DATA = 15
        IBC_BOILER_EXT_DETAIL_DATA = 19
        IBC_CLOCK_DATA = 24
        IBC_BOILER_SITE_DATA = 34

        # --- Advanced settings, things like load pairing information not useful to most people
        IBC_LOAD_PAIRING_DATA = 25
        # TODO will this tell me when I need to run a cleaning cycle?, what does that entail?
        IBC_BOILER_CLEANING_SETTINGS_DATA = 18
        IBC_BOILER_MULTI_SETTINGS_DATA = 17

        # --- These fail when hit with the parameters I was using, more discovery needed
        # Example response { "object_no": 201, "fail_code": 1, "operation": 7, "object_index": -1 }
        IBC_BOILER_ERRLOG_DATA = 7
        IBC_BOILER_SETBACK_DATA = 14
        IBC_BOILER_LOAD_SETTINGS_DATA = 16
        IBC_SITELOG_DATA = 23
        IBC_BOILER_CAPTURE_DATA = 26

        # --- DO NOT USE --- (These are either for setting values, which is not supported with this class, or look
        # dangerous enough I didn't want to hit them to find out
        # IBC_PASSWORD_DATA = 99
        # IBC_ALERT_DATA = 31
        # IBC_BOILER_BACKUP_ADVANCED = 27 # Discovered by me, http://192.168.2.13/js/adv.js:4
        # IBC_BOILER_RESTORE_ADVANCED = 28 # Discovered by me, http://192.168.2.13/js/adv.js:5
        # IBC_BOILER_RESTORE = 29
        # IBC_BOILER_FACTORY_DATA = 20
        # IBC_BOILER_FACTORY_SETTINGS_DATA = 21

    # Represents values that are not set (Disconnected sensors, etc.)
    _UNSET_SENTINEL_VALUE = 32766

    # Keep people from spamming the boiler in too quick of a loop
    MINIMUM_DELAY = datetime.timedelta(seconds=9)
    LAST_REQUEST = None

    TARGET_URL = "cgi-bin/bc2-cgi"

    def __init__(self, address, temperature_type=Temperature.Celcius):
        self.address = address

        self.temperature_flag = temperature_type
        self._status = None
        self._supply_temperature = None
        self._return_temperature = None
        self._target_temperature = None
        self._inlet_pressure = None
        self._delta_pressure = None
        self._mbh = None

        self.target = "http://%s/%s" % (self.address, self.TARGET_URL)

        # TODO Maybe hit one of the boiler info rpcs for the name/number etc.

    def _request_object(self, object):
        # TODO Cache and return the response instead of raising an exception
        # if self.LAST_REQUEST and self.LAST_REQUEST + self.MINIMUM_DELAY < datetime.datetime.now():
        #     raise Exception("Too many requests too fast!")

        self.LAST_REQUEST = datetime.datetime.now()
        # TODO not very pretty, but this is the actual format... json as a parameter
        # TODO object_no: 100 is SUPER IMPORTANT. it's the container for all the information,
        # Otherwise you're attempting to SET that information with the query values
        payload = {"json": json.dumps({"object_no": 100, "object_request": object, "boiler_no": 0})}
        response = requests.get(self.target, params=payload)

        logging.debug(response.url)
        # logging.debug(response.text)

        return response

    def refresh(self):
        response = self._request_object(IBCBoiler.ObjectCodes.IBC_BOILER_EXT_DETAIL_DATA)
        self._update(
            response.json()
        )

    def _update(self, values):
        self._status = values.get("Status", "Unknown")
        self._mbh = values.get("MBH")
        # IBC Stores the temperature as 4x for some reason
        # Store the values internally as regular Celsius values
        self._supply_temperature = values.get("SupplyT")/4
        self._return_temperature = values.get("ReturnT")/4
        self._target_temperature = values.get("TargetT")/4
        self._inlet_pressure = values.get("InletPressure")
        self._delta_pressure = values.get("DeltaPressure")

    @property
    def status(self):
        return self._status

    @property
    def mbh(self):
        return self._mbh

    @property
    def supply_temperature(self):
        if self.temperature_flag == IBCBoiler.Temperature.Celcius:
            return self._supply_temperature
        else:
            raise NotImplementedError()

    @property
    def return_temperature(self):
        if self.temperature_flag == IBCBoiler.Temperature.Celcius:
            return self._return_temperature
        else:
            raise NotImplementedError()

    @property
    def target_temperature(self):
        if self.temperature_flag == IBCBoiler.Temperature.Celcius:
            return self._target_temperature
        else:
            raise NotImplementedError()

    @property
    def inlet_pressure(self):
        return self._inlet_pressure
