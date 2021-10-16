# krakenExport
Export Kraken Orders to Cointracking.info or a csv file

## Install

1. Clone/Download `git clone https://github.com/Gaareth/krakenExport.git`
2. Install [python3](https://www.python.org/downloads/)
3. Install dependencies `pip install -r requirements.txt`
4. Download Selenium Webdriver [Geckodriver](https://github.com/mozilla/geckodriver/releases) and extract the `geckodriver` file

## Setup

### Setup Kraken API
Check out: [Kraken Support](https://support.kraken.com/hc/en-us/articles/360000919966-How-to-generate-an-API-key-pair-) to learn how to create an api key.
Make sure you only select Query Ledger Entries, Query Funds and Export Data. Copy your public and private key. Also keep in mind that anyone with this key could now query your ledger entries.

### .ENV FILE
You need to create a .env file, where you will define application relevant variables. Checkout env.example as a reference.
- ```public_key```  = \<your kraken api public key\>
- ```private_key```  = \<your kraken api private key\>

- ```cointracking_username```  = \<cointracking username\>
- ```cointracking_password```  = \<cointracking password\>

Also in case you did not save the `geckodriver` file in a PATH directory add an additional field:
- ```geckodriver```  = \<path where you saved the geckodriver file\>




### Setup Selenium
- Either put it in your PATH (e.g. on linux: /usr/bin) or setup a environment variable (see env file)


## Usage
```
python krakenExport.py --help
> usage: krakenExport.py [-h] -s START -e END [-ex EXCLUDED_TYPES] [--csv] [--cointracking]

optional arguments:
  -h, --help            show this help message and exit
  -s START, --start START
                        Start date of trades (format=[Y-m-d])
  -e END, --end END     End date of trades (format=[Y-m-d])
  -ex EXCLUDED_TYPES, --excluded-types EXCLUDED_TYPES
                        Order types to exclude. "Withdrawal" order types will be skipped by default
  --csv                 Creates csv file containing your orders.
  --cointracking        Imports orders to cointracking.info
```
### Export to CSV 
`python krakenExport.py --csv -s %Y-%m-%d -e %Y-%m-%d` <br>
The csv file will be in a subdirectory of your current directory named 'exports'

### Export to cointracking.info
Make sure that your .env file contains `cointracking_username` and `cointracking_password` <br>
`python krakenExport.py --cointracking -s %Y-%m-%d -e %Y-%m-%d`

## Scheduled Task
You could setup a cron job to perodically update cointracking with your kraken trades.


