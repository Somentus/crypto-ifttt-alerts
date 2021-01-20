#!/usr/bin/env python3
"""Crypto IFTTT Alerts
Author: Somentus
Version: 0.1.1
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

# Get the location for our price alerts config.
CONFIG = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'xbt-rules.txt',
)

# Get the location for previous price file.
PREVIOUS = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'xbt-previous-price.txt',
)

# The name of our IFTTT web request event.
IFTTT_EVENT = secrets.IFTTT_EVENT

# Our IFTTT secret key. Protect this if you don't want attackers to send
# you notifications.
IFTTT_KEY = secrets.IFTTT_KEY

# The endpoint we'll use to send trigger price alert notifications.
IFTTT_URL = (
    'https://maker.ifttt.com/trigger/{0}/with/key/{1}'
    .format(IFTTT_EVENT, IFTTT_KEY)
)


class PriceRule:
    """Handle individual price rules.

    This class parses, validates, compares, and sends notifications for
    individual price rules.
    """

    # Map the operator symbol to the corresponding Python comparison operator
    OPERATOR_MAP = {'>': operator.gt, '<': operator.lt}

    # Map the operator symbol to the corresponding word
    WORD_MAP = {'>': 'above', '<': 'below'}

    def __init__(self, originalLine):
        """Initialize PriceRule.

        This requires a single line from the price rules config file.

        Args:
            originalLine (str): A single line from the price rules config.
        """
        self.originalLine = originalLine
        self.parseLine(originalLine)

    def parseLine(self, line):
        """Parse the price rule config line.

        This parses the config line, validates it, then sets required instance
        variables.

        Args:
            line (str): config line.

        Raises:
            ValueError: If the config line is invalid.
        """

        # Remove whitespace surrounding the line.
        line = line.strip()

        # Get the opreator symbol. We assume the operator symbol is the first
        # non-whitespace character.
        operatorSymbol = line[0]

        # The remainder of the line is the threshold. Remove any non numeric
        # characters.
        threshold = re.sub(r'[^\d]', '', line[1:].strip())

        # Ensure the operator symbol makes sense.
        if operatorSymbol not in ['>', '<']:
            raise ValueError('Line must start with > or <.')

        # Ensure the threshold can be converted to float.
        try:
            threshold = float(threshold)
        except TypeError:
            raise ValueError('Line must contain a valid price.')

        # If all is well, set required instance variables.
        self.operatorSymbol = operatorSymbol
        self.operator = self.OPERATOR_MAP[operatorSymbol]
        self.threshold = threshold

    def matches(self, value):
        """Check if value matches our price rule condition.

        Assuming the operator is ">" or "greater than",

        self.operator(value, self.threshold)

        is the equivalent of:

        value > self.threshold

        Args:
            value (float): The XBT price.
        """
        return self.operator(value, self.threshold)

    def notify(self, XBTPrice):
        """Construct and send a notification for this price rule.

        This doesn't check whether or not the price rule condition is met, it
        just sends the notification.

        Args:
            XBTPrice (float): The XBT price :)
        """

        # Get the correct operator word. e.g. "above" for ">".
        word = self.WORD_MAP[self.operatorSymbol]

        # Construct the data dict to send to the IFTTT webhook
        data = {
            'value1': '{0} €{1:,.2f}'.format(word, self.threshold),
            'value2': '€{:,.2f}'.format(XBTPrice)
        }

        # Send the webhook, which then triggers the mobile notification
        requests.post(IFTTT_URL, json=data)

def loadPriceRules():
    """Load the price rules config file, create a PriceRule for each line.

    Returns:
        list: A list of PriceRule objects.
    """
    rules = []

    with open(CONFIG) as configFile:
        for line in configFile:
            rules.append(PriceRule(line))

    return rules


def getXBTPrice():
    """Hit the Kraken API and get the current XBT price.

    Returns:
        float: XBT price.

    Raises:
        RuntimeError: if request fails or response is invalid.
    """
    try:
        response = requests.get(TICKER_URL)
        return float(response.json()['result']['XXBTZEUR']['a'][0])
    except (IndexError, KeyError):
        raise RuntimeError('Could not parse API response.')

def loadPreviousXBTPrice():
    """Load the previous price from file, return the previous price.

    Returns:
        float: previous XBT price.
    """

    with open(PREVIOUS) as priceFile:
        for line in priceFile:
            previous = float(line.strip())

    return previous

def saveXBTPrice(XBTPrice):
    """Save the price to a file, to function as the 
    previous price for the next run of the script.
    """
    f = open(PREVIOUS,"w+")
    f.truncate(0)
    f.write(str(XBTPrice))
    f.close()

def isSafeDistance(price1, price2):
    if abs(price1 - price2) > 250:
        return True
    else:
        return False

def checkXBT():
    # Get the current and previous XBT prices
    XBTPrice = getXBTPrice()
    XBTPreviousPrice = loadPreviousXBTPrice()

    # Iterate through each price rule, and check for matches.
    for rule in loadPriceRules():
        # If we find a match, send the notification and stop the loop.
        if rule.matches(XBTPrice) and isSafeDistance(XBTPrice, XBTPreviousPrice):
            saveXBTPrice(str(XBTPrice))
            rule.notify(XBTPrice)
            break


if __name__ == '__main__':
    checkXBT()
