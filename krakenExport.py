import argparse
import base64
import csv
import datetime
import hashlib
import hmac
import io
import os
import random
import time
import urllib.parse
import sys

import requests
import selenium.common.exceptions
from dotenv import load_dotenv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec

load_dotenv()
# Read Kraken API key and secret stored in environment variables
api_url = "https://api.kraken.com"
api_key = os.environ.get("public_key")
api_sec = os.environ.get("private_key")
if not api_sec or not api_key:
    print("Please make sure that [public_key] and [private_key] are valid fields in your .env file")
    sys.exit(-1)


def get_kraken_signature(urlpath, data, secret):
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()


# Attaches auth headers and returns results of a POST request
def kraken_request(uri_path, data, api_key, api_sec):
    headers = {'API-Key': api_key, 'API-Sign': get_kraken_signature(uri_path, data, api_sec)}
    # get_kraken_signature() as defined in the 'Authentication' section
    req = requests.post((api_url + uri_path), headers=headers, data=data)
    return req


def parse_pair(pair):
    resp = requests.get(f"https://api.kraken.com/0/public/AssetPairs?pair={pair}").json()
    if "error" in resp:
        print(f"Error while retrieving data: {resp['error']}")
        return
    results = resp["result"][pair]["wsname"]
    base = results.split("/")[0]
    quote = results.split("/")[1]

    base = base.replace("XBT", "BTC").replace("XDG", "DOGE")
    quote = quote.replace("XBT", "BTC").replace("XDG", "DOGE")
    return (base, quote)


def export_to_cointracking(start_time, end_time, excluded_types: list = None):
    if excluded_types is None:
        excluded_types = ["withdrawal"]
    export_to_csv_manual(start_time, end_time, exclude_types=excluded_types,
                         csv_filename="latest-kraken-export.csv")

    USERNAME = os.environ.get('cointracking_username')
    PASSWORD = os.environ.get('cointracking_password')
    if not USERNAME or not PASSWORD:
        print("Please make sure that [cointracking_username] and [cointracking_password] are valid fields in your "
              ".env file")
        sys.exit(-1)

    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options

    options = Options()
    options.headless = True
    webdriver_path = (os.environ.get("geckodriver") or "geckodriver")
    print(f"Webdriver path: {webdriver_path}")

    driver = webdriver.Firefox(options=options, executable_path=webdriver_path)
    driver.get("https://cointracking.info/index.php")
    time.sleep(random.randrange(5, 10) / 10)

    try:
        username = driver.find_element_by_css_selector("input#log_us")
        password = driver.find_element_by_css_selector("input#log_pw")

        time.sleep(random.randrange(1, 3))
        username.click()

        username.send_keys(USERNAME)
        time.sleep(random.randrange(1, 3))
        password.send_keys(PASSWORD)

        time.sleep(random.randrange(1, 3))

        driver.find_element_by_css_selector("input[name=\"login\"]").click()  # login

        driver.get("https://cointracking.info/import/kraken/")

        # Upload csv
        upload_button = WebDriverWait(driver, 10).until(ec.visibility_of_element_located((By.CSS_SELECTOR,
                                                                                          "input[type=\"file\"]")))

        upload_button.send_keys(
            f"{os.getcwd()}/exports/latest-kraken-export.csv")

        time.sleep(random.randrange(1, 3))

        driver.find_element_by_css_selector("a[href=\"import.php\"]").click()
        time.sleep(random.randrange(3, 5))

        driver.find_element_by_css_selector("input[name=\"import_start\"]").click()
        print("Successfully uploaded kraken CSV to cointracking.info!")
    except selenium.common.exceptions.NoSuchElementException:
        import traceback
        traceback.print_exc()
        #print(driver.page_source)
        with open("error.html", "w") as f:
            f.write(driver.page_source)


    driver.quit()


def export_to_csv_manual(start_time: float, end_time: float, exclude_types: list = None, download=True,
                         csv_filename=None):
    """
    Query ledgers using the api

    :return: string formatted in csv
    """

    if exclude_types is None:
        exclude_types = []
    print(f"Skipping: {exclude_types}")

    csv_output = io.StringIO()
    filewriter = csv.writer(csv_output, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
    filewriter.writerow(["txid", "refid", "time", "type", "subtype", "aclass", "asset", "amount", "fee", "balance"])

    def query_ledgers(end_time_ledger: float):
        resp = kraken_request('/0/private/Ledgers', {
            "nonce": str(int(1000 * time.time())),
            "end": int(end_time_ledger),
            "start": int(start_time)
        }, api_key, api_sec)

        ledger_json = resp.json()

        for i, ledger_id in enumerate(ledger_json["result"]["ledger"]):
            ledger_info = ledger_json["result"]["ledger"][ledger_id]

            if ledger_info["type"] in exclude_types:
                continue  # skip if trade should be excluded

            filewriter.writerow([
                ledger_id,
                ledger_info["refid"],
                datetime.datetime.fromtimestamp(ledger_info["time"]).strftime("%Y-%m-%d %H:%M:%S"),
                ledger_info["type"],
                ledger_info["subtype"],
                ledger_info["aclass"],
                ledger_info["asset"],
                ledger_info["amount"],
                ledger_info["fee"],
                ledger_info["balance"]
            ])

            if i == (len(ledger_json["result"]["ledger"]) - 1):  # last element of loop
                if i >= 49:  # if batch contains max 49 elements there are probably more to fetch
                    # fetch ledgers up to most recent fetched ledger
                    query_ledgers(end_time_ledger=ledger_info["time"])

    query_ledgers(end_time)

    if download:
        if csv_filename is None:
            csv_filename = f"kraken-" \
                           f"[{datetime.datetime.fromtimestamp(start_time).strftime('%Y.%m.%d')} — " \
                           f"{datetime.datetime.fromtimestamp(end_time).strftime('%Y.%m.%d')}].csv"

        os.makedirs("exports", exist_ok=True)
        filepath = os.path.join("exports", csv_filename)
        with open(filepath, "w") as csv_file:
            csv_file.write(csv_output.getvalue())

    print(f"Generated Kraken CSV!")
    return csv_output.getvalue()


def export_to_cmc():
    from ImportCMC import add_transaction

    # Construct the request and print the result
    resp = kraken_request('/0/private/TradesHistory', {
        "nonce": str(int(1000 * time.time())),
        "trades": True
    }, api_key, api_sec)

    resp_json = resp.json()
    print("Loaded Kraken History")

    for trade in resp_json["result"]["trades"]:
        trade_info = resp_json["result"]["trades"][trade]
        trade_pair = parse_pair(trade_info["pair"])

        add_transaction(
            transaction_type=trade_info["type"],
            crypto_symbol=trade_pair[0],
            fiat_symbol=trade_pair[1],
            amount=trade_info["vol"],
            price=trade_info["price"],
            transaction_time=datetime.datetime.fromtimestamp(trade_info["time"]),
            fee=trade_info["fee"],
            note=f"Automated entry ordertxid: {trade_info['ordertxid']} postxid: {trade_info['postxid']}"
        )


# export_to_cointracking(datetime.datetime(2021, 1, 1).timestamp(), datetime.datetime.now().timestamp())
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--start", help="Start date of trades (format=[Y-m-d])", required=True,
                        type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').timestamp())
    parser.add_argument("-e", "--end", help="End date of trades (format=[Y-m-d])", required=False,
                        type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').timestamp())

    parser.add_argument("-ex", "--excluded-types", type=list, default=["withdrawal"],
                        help="Order types to exclude. \"Withdrawal\" order types will be skipped by default")

    parser.add_argument("--csv", action="store_true", help="Creates csv file containing your orders.")
    parser.add_argument("--cointracking", action="store_true", help="Imports orders to cointracking.info")

    args = vars(parser.parse_args())
    print(args)

    if args.get("end", None) is None:
        args["end"] = datetime.datetime.now().timestamp()

    if args["csv"]:
        export_to_csv_manual(args["start"], args["end"], args["excluded_types"])
    elif args["cointracking"]:
        export_to_cointracking(args["start"], args["end"], args["excluded_types"])
    else:
        print("Please use [--csv; to generate a csv export ] or [--cointracking; to export to cointracking.info]")
