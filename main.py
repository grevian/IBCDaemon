import json
import requests
from requests import ConnectionError, Timeout
from ibcboiler import IBCBoiler
import logging
import datetime
import time
import argparse

logging.basicConfig(level=logging.DEBUG)

parser = argparse.ArgumentParser(description='Read data from an IBC Boiler and send it to a web based monitoring server')
parser.add_argument('--boiler_ip', type=str, help='The boilers IP Address')

parser.add_argument('--monitor_address', type=str, help='The monitoring server hostname/address')
parser.add_argument('--secret', type=str, help='The secret to include in status updates')

args = parser.parse_args()

STANDBY_DELAY = datetime.timedelta(minutes=5)
POST_BURN_READING = datetime.timedelta(minutes=2)
SENSOR_URL = args.monitor_address

# Ensure an update is done at least on the first loop iteration, no matter the boiler status
last_update = datetime.datetime.now() - STANDBY_DELAY
last_burn = datetime.datetime.now() - POST_BURN_READING

# TODO Read from a configuration file/the command line
i = IBCBoiler(args.boiler_ip)
request_payload = {
    "sensor": "IBCBoiler",
    "secret": args.secret
}


def send_sensor_data(payload):
    try:
        r = requests.post(SENSOR_URL, data=json.dumps(payload))
    except (ConnectionError, Timeout) as e:
        logging.warn("Failed to send update to the server: %r", e)
        return

    if r.status_code != 200:
        logging.error("Server error, %r" % r.content)


def send_temperature_update(temperature_type, value):
    payload = request_payload.copy()
    payload["type"] = "boiler_temperature"
    payload["subtype"] = temperature_type
    payload["value"] = value
    send_sensor_data(payload)


def send_mbh_update(value):
    payload = request_payload.copy()
    payload["type"] = "mbh"
    payload["value"] = value
    send_sensor_data(payload)


def send_boiler_update(boiler):
    send_temperature_update("supply", boiler.supply_temperature)
    send_temperature_update("return", boiler.return_temperature)
    send_temperature_update("target", boiler.target_temperature)
    send_mbh_update(boiler.mbh)


while True:
    logging.debug("Updating Boiler Information")
    i.refresh()

    if i.status in (IBCBoiler.Status.Heating,
                    IBCBoiler.Status.Purging,
                    IBCBoiler.Status.Igniting,
                    IBCBoiler.Status.Initializing):
        # Update immediately, values change very quickly while heating
        last_update = datetime.datetime.now()
        last_burn = last_update
        send_boiler_update(i)
        logging.info("Sending Update: Boiler in active status")
    elif i.status == IBCBoiler.Status.Standby:
        # Only update if a lot of time has passed, updates during standby are much less significant
        if last_update + STANDBY_DELAY <= datetime.datetime.now():
            last_update = datetime.datetime.now()
            send_boiler_update(i)
            logging.info("Sending Update: Boiler in standby")
        # Continue sending updates for a few minutes after the last time the burner was active
        elif last_burn + POST_BURN_READING >= datetime.datetime.now():
            last_update = datetime.datetime.now()
            send_boiler_update(i)
            logging.info("Sending Update: Boiler was recently active")
    elif i.status == IBCBoiler.Status.Circulating:
        last_update = datetime.datetime.now()
        send_boiler_update(i)
        logging.info("Sending Update: Boiler is circulating")
    else:
        # Log a warning here, maybe an error/off state?
        logging.warning("Boiler is in an unexpected state: %r", i.status)

    time.sleep(10)
