#!/usr/bin/env python3
"""Crypto IFTTT Alerts
Author: Somentus
Version: 0.2.1
Project based on Tyler's guide:
https://howchoo.com/pi/your-first-ifttt-project-bitcoin-price-alerts
"""

import operator
import re
import requests
import os
import secrets

# The endpoint we'll hit to get XBT price info.
TICKER_URL = 'https://api.kraken.com/0/public/Ticker?pair=XBTEUR'

# Get the location for previous price file.
PREVIOUS = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'xbt-previous-price.txt',
)

# The name of our IFTTT web request event.
IFTTT_EVENT = secrets.IFTTT_EVENT

# Our IFTTT secret key. Protect this if you don't
# want attackers to send you notifications.
IFTTT_KEY = secrets.IFTTT_KEY

# The endpoint we'll use to send trigger price alert notifications.
IFTTT_URL = (
    'https://maker.ifttt.com/trigger/{0}/with/key/{1}'
    .format(IFTTT_EVENT, IFTTT_KEY)
)

def notify(XBTPrice, XBTPreviousPrice):
    """Construct and send a notification for this price rule.

    This doesn't check whether or not the current price differs enough
    from the previous price, it just sends the notification.

    Args:
        XBTPrice (float): The current XBT price
        XBTPreviousPrice (float): The XBT price last time a notification was sent
    """

    # Get the correct operator word. e.g. "above",
    # and calculate the proper limit to compare to.
    if XBTPrice > XBTPreviousPrice:
        word = 'above'
        threshold = int(XBTPrice / 1000) * 1000
    else:
        word = 'below'
        threshold = (int(XBTPrice / 1000) + 1) * 1000
    # XBTPrice is never equal to XBTPreviousPrice,
    # or notify would not have been called

    # Construct the data to send to the IFTTT webhook
    data = {
        'value1': '{0} €{1:,d}'.format(word, threshold),
        'value2': '€{:,d}'.format(int(XBTPrice))
    }

    # Send the webhook, which then triggers the mobile notification
    requests.post(IFTTT_URL, json=data)

def getXBTPrice():
    """Hit the Kraken API and get the current XBT price.

    Returns:
        float: The current XBT price.

    Raises:
        RuntimeError: if request fails or response is invalid.
    """
    try:
        response = requests.get(TICKER_URL)
        return float(response.json()['result']['XXBTZEUR']['a'][0])
    except (IndexError, KeyError):
        raise RuntimeError('Could not parse API response.')

def loadPreviousXBTPrice():
    """Load the previous price from file and return the loaded price.

    Returns:
        float: The XBT price last time a notification was sent
    """

    with open(PREVIOUS) as priceFile:
        for line in priceFile:
            previous = float(line.strip())

    return previous

def saveXBTPrice(XBTPrice):
    """Save the price to a file, to function as the
    previous price for the next run of the script.

    Args:
        XBTPrice (float): The current XBT price

    """

    f = open(PREVIOUS,"w+")
    f.truncate(0)
    f.write(str(XBTPrice))
    f.close()

def isSafeDistance(XBTPrice, XBTPreviousPrice):
    """Calculates if the two prices differ enough
    from each other to warrant sending a notification.

    Args:
        XBTPrice (float): The current XBT price
        XBTPreviousPrice (float): The XBT price last time a notification was sent

    Returns:
        boolean: True if prices differ enough, otherwise False
    """
    if abs(XBTPrice - XBTPreviousPrice) > 250:
        return True
    else:
        return False

def checkXBT():
    """Checks if the new XBT price has changed
    significantly since last sending a notification.
    If so, stores new price and sends a new notification.
    """

    XBTPrice = getXBTPrice()
    XBTPreviousPrice = loadPreviousXBTPrice()

    if isSafeDistance(XBTPrice, XBTPreviousPrice):
        saveXBTPrice(str(XBTPrice))
        notify(XBTPrice, XBTPreviousPrice)

if __name__ == '__main__':
    checkXBT()
