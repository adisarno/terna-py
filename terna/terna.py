#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : fgenoese
# Created Date: Sunday 15 January 2023 at 19:31

import requests
import pandas as pd
import datetime
import time
import logging
import sys
from typing import Optional, Dict
from urllib.parse import urlencode

__title__ = "terna-py"
__version__ = "0.5.5"
__author__ = "fgenoese"
__license__ = "MIT"

URL = 'https://api.terna.it/transparency/oauth/accessToken'
BASE_URL = 'https://api.terna.it/'
RATE_LIMIT = 1.1  # seconds between requests to respect the rate limit

class TernaPandasClient:
    def __init__(
            self, api_key: str, api_secret: str, session: Optional[requests.Session] = None,
            proxies: Optional[Dict] = None, timeout: Optional[int] = None,
            log_level: Optional[int] = logging.ERROR):
        """
        Parameters
        ----------
        api_client : str
        api_secret : str
        session : requests.Session
        proxies : dict
            requests proxies
        timeout : int
        log_level : int, optional
            Logging level (default: logging.ERROR)
        """
        
        # Set up logger
        log = logging.getLogger(__name__)
        log.setLevel(log_level)
        log.propagate = False  # prevent double logging
        if not log.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(log_level)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            log.addHandler(handler)
        self.logger = log
        self.logger.debug("Client initialized with log level %s", logging.getLevelName(log_level))
        
        if api_key is None:
            raise TypeError("API key cannot be None")
        if api_secret is None:
            raise TypeError("API secret cannot be None")
        self.api_key = api_key
        self.api_secret = api_secret
        if session is None:
            session = requests.Session()
        self.session = session
        self.proxies = proxies
        self.timeout = timeout
        self.token = None
        self.token_expiration = datetime.datetime.now()
        self.time_of_last_request = time.monotonic() - 1

    def _request_token(self, data: Dict = {}) -> str:
        """
        Parameters
        ----------
        data : dict
        
        Returns
        -------
        access_token : str
        """
        # keep current token if still valid
        if self.token_expiration - datetime.timedelta(seconds =5) > datetime.datetime.now() and self.token: # Still valid token
            print ("Using existing token:", self.token)
            return self.token


        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        base_data = {
            'client_id': self.api_key,
            'client_secret': self.api_secret,
            'grant_type': 'client_credentials',
        }
        data.update(base_data)

        try:
            time_elapsed = time.monotonic() - self.time_of_last_request
            if time_elapsed < RATE_LIMIT:
                self.logger.debug("[token] Waiting for %.2f seconds to respect rate limit", RATE_LIMIT - time_elapsed)
                time.sleep(RATE_LIMIT - time_elapsed)
            response = self.session.post(URL, headers=headers, data=data)
            self.time_of_last_request = time.monotonic()
            response.raise_for_status()
            self.logger.debug(f"Response content: {response.text}")

        except requests.HTTPError as exc:
            code = exc.response.status_code
            if code in [429, 500, 502, 503, 504]:
                self.logger.error(code)
            raise
        
        else:
            if response.status_code == 200:
                token = response.json().get('access_token')
                expires_in = response.json().get('expires_in')
                self.token_expiration = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
                self.token = token
                return token
            else:
                self.logger.error(f"Request failed with status code {response.status_code}")
                return None
    
    def _base_request(self, item, data: Dict) -> pd.DataFrame:
        """
        Parameters
        ----------
        data : dict
        
        Returns
        -------
        pd.DataFrame
        """

        access_token = self._request_token()
        #params = urlencode(data, doseq=True)
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        _url = f"{BASE_URL}{item}"
        self.logger.debug("API endpoint: " + _url)
        self.logger.debug(f"Request data: {data}")
        
        try:
            time_elapsed = time.monotonic() - self.time_of_last_request
            if time_elapsed < RATE_LIMIT:
                self.logger.debug("[base request] Waiting for %.2f seconds to respect rate limit", RATE_LIMIT - time_elapsed)
                time.sleep(RATE_LIMIT - time_elapsed)
            response = self.session.get(_url, headers=headers, params=data)
            self.logger.debug(f"Request URL: {response.url}")
            self.time_of_last_request = time.monotonic()
            response.raise_for_status()
            self.logger.debug(f"Response status: {response.status_code}")
            self.logger.debug(f"Response headers: {response.headers}")
            self.logger.debug(f"Response content: {response.text[:500]}")

        except requests.HTTPError as exc:
            code = exc.response.status_code
            if code in [429, 500, 502, 503, 504]:
                self.logger.error(f"Request failed with status code {code}")
            raise
        else:
            if response.status_code == 200:
                json = response.json()
                if 'result' in json:
                    json.pop('result')
                    key = list(json.keys())[0]
                    df = pd.json_normalize(json[key])
                    # Normalize column name to 'Date' if 'date' exists
                    if 'date' in df.columns and 'Date' not in df.columns:
                        df.rename(columns={'date': 'Date'}, inplace=True)
                    if 'Date' in df.columns or 'date' in df.columns:
                        df['Date'] = pd.to_datetime(df['Date'])
                        df['Date'] = df['Date'].map(lambda x: TernaPandasClient._adjust_tz(x, tz="Europe/Rome"))
                        df.sort_values(by='Date', inplace=True)
                        df.index = df['Date']
                        df.index.name = None
                        df.drop(columns=['Date'], inplace=True)
                    elif 'Year' in df.columns:
                        df.index = df['Year']
                        df.drop(columns=['Year'], inplace=True)
                    for col in df.columns:
                        try:
                            df[col] = pd.to_numeric(df[col])
                        except (ValueError, TypeError):
                            pass
                    return df
                else:
                    return None
            else:
                self.logger.error(f"Request failed with status code {response.status_code}")
                return None
    
        
    def _fetch_with_optional_params(self, endpoint, start=None, end=None, **kwargs):
        extra = {k: v for k, v in kwargs.items() if v is not None}

        # Chiamata senza start e end se non sono forniti
        if start is None and end is None:
            return self.fetch_data(endpoint, extra_params=extra)
        
        return self.fetch_data(endpoint, start=start, end=end, extra_params=extra)


    def fetch_data(self, item: str, start: pd.Timestamp = None, end: pd.Timestamp = None, 
               extra_params: Optional[dict] = None) -> pd.DataFrame:
        """
        General method for fetching different types of data.

        Parameters
        ----------
        item : str
            API endpoint for the request.
        start : pd.Timestamp, optional
            Start date (if applicable).
        end : pd.Timestamp, optional
            End date (if applicable).
        extra_params : dict, optional
            Additional parameters for the API request.

        Returns
        -------
        pd.DataFrame
        """
        data = {}

        if start is not None and end is not None:
            data['dateFrom'] = start.strftime('%d/%m/%Y')
            data['dateTo'] = end.strftime('%d/%m/%Y')

        if extra_params:
            data.update(extra_params)

        print(f"\n{item}")
        return self._base_request(item, data)
    
    def get_total_load(self, start, end, bzone=None):
        return self._fetch_with_optional_params('load/v2.0/total-load', start, end, biddingZone=bzone)
    
    def get_market_load(self, start, end, bzone=None):
        return self._fetch_with_optional_params('load/v2.0/market-load', start, end, biddingZone=bzone)
    
    def get_peak_valley_load(self, start, end):
        return self._fetch_with_optional_params('load/v2.0/peak-valley-load', start, end)
    
    def get_peak_valley_load_details(self, start, end):
        return self._fetch_with_optional_params('load/v2.0/peak-valley-load-details', start, end)
    
    def get_actual_generation(self, start, end, gen_type=None):
        return self._fetch_with_optional_params('generation/v2.0/actual-generation', start, end, type=gen_type)
    
    def get_renewable_generation(self, start, end, res_gen_type=None):
        return self._fetch_with_optional_params('generation/v2.0/renewable-generation', start, end, type=res_gen_type)
    
    def get_energy_balance(self, start, end, energy_bal_type=None):
        return self._fetch_with_optional_params('generation/v2.0/energy-balance', start, end, type=energy_bal_type)
    
    def get_installed_capacity(self, year=None, gen_type=None):
        return self._fetch_with_optional_params('generation/v2.0/installed-capacity', year=year, type=gen_type)
    
    def get_scheduled_foreign_exchange(self, start, end):
        return self._fetch_with_optional_params('transmission/v2.0/scheduled-foreign-exchange', start, end)
    
    def get_scheduled_internal_exchange(self, start, end):
        return self._fetch_with_optional_params('transmission/v2.0/scheduled-internal-exchange', start, end)
    
    def get_physical_foreign_flow(self, start, end):
        return self._fetch_with_optional_params('transmission/v2.0/physical-foreign-flow', start, end)
    
    def get_physical_internal_flow(self, start, end):
        return self._fetch_with_optional_params('transmission/v2.0/physical-internal-flow', start, end)
    
    def get_IMCEI(self, year=None, month=None):
        return self._fetch_with_optional_params('load/v2.0/monthly-index-industrial-electrical-consumption', year=year, month=month)

    # Rimossa
    # def get_secondary_adjustment_levels(self, start, end):  
    #     return self._fetch_with_optional_params('market-and-fees/v1.0/secondary-adjustment-levels', start, end)
  
    # def get_wind_forecast(self, start, end):
    #     return self.fetch_data('market/v1.0/input/wind-production-forecast', start, end)
 
    
    # May 2025 
      
    def get_forecast_load(self, start, end, sessionType = None):
       return self._fetch_with_optional_params('market/v1.0/input/forecast-load', start, end, sessionType = sessionType)
    
    def get_costs(self, start, end, sessionType = None, direction = None):
        return self._fetch_with_optional_params('market/v1.0/output/costs', start, end, sessionType = sessionType, direction = direction)
    
    def get_quantity(self, start, end, sessionType = None, direction = None):
        return self._fetch_with_optional_params('market/v1.0/output/quantity', start, end, sessionType = sessionType, direction = direction)
    
    def get_accepted_offers(self, start, end, sessionType = None, direction = None):
        return self._fetch_with_optional_params('market/v1.0/output/accepted-offers', start, end, sessionType = sessionType, direction = direction)
    
    def get_submitted_offers(self, start, end, sessionType = None, direction = None):
        return self._fetch_with_optional_params('market/v1.0/input/submitted-offers', start, end, sessionType = sessionType, direction = direction)
    
    def get_prices(self, start, end, priceType = None, sessionType = None, direction = None):
        '''
        Parameters
        ----------
        .session_type	MSD1
        .type		    MARGINAL
        .direction	    UP
        
        '''
        return self._fetch_with_optional_params('market/v1.0/output/prices', start, end, priceType = priceType, sessionType = sessionType, direction = direction)

    def get_plant_outages(self, start, end):
        return self._fetch_with_optional_params('outages/v1.0/generation-unit-unavailability', start, end)

    # June 2025 
    
    def get_detail_available_capacity(self, start, end):
        return self._fetch_with_optional_params('adequacy/v1.0/detail-available-capacity', start, end)

    @staticmethod
    def _adjust_tz(dt, tz):
        delta = dt.minute % 15
        if delta == 0:
            return dt.tz_localize(tz, ambiguous=True)
        else:
            return (dt - datetime.timedelta(minutes=delta+15*(4-delta))).tz_localize(tz, ambiguous=False)

    def __repr__(self):
        return f"<TernaPandasClient(api_key={self.api_key[:4]}***, api_secret={self.api_secret[:4]}***)>"