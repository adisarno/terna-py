# terna-py
Python client for the Transparency API of Terna, the Italian electricity transmission system operator

[![PyPI Latest Release](https://img.shields.io/pypi/v/terna-py.svg)](https://pypi.org/project/terna-py/)
[![Downloads](https://static.pepy.tech/badge/terna-py)](https://pypi.org/project/terna-py/)

Documentation of the API: https://developer.terna.it/docs/read/APIs_catalog#en

## Installation
`python3 -m pip install terna-py`

## Usage
```python
import terna as trn
import pandas as pd

# Please follow the API documentation to register an account and create credentials
key = '<YOUR API KEY>'
secret = '<YOUR API SECRET>'

client = TernaPandasClient(api_key=key,api_secret=secret)

###########################################################################

# Note: you specifically need to set a start= and end= parameter which should be a pandas timestamp with timezone

bzone = ["Centre-North", "Centre-South", "North", "Sardinia", "Sicily", "South", "Calabria", "Italy"]
gen_type = ['Thermal', 'Wind', 'Geothermal', 'Photovoltaic', 'Self-consumption', 'Hydro']
res_gen_type = ['Wind', 'Geothermal', 'Photovoltaic', 'Hydro']
energy_bal_type = ['Thermal', 'Wind', 'Geothermal', 'Photovoltaic', 'Self-consumption', 'Hydro', 'Pumping-consumption', 'Net Foreign Exchange']
# sectors = ['ALIMENTARE', 'ALTRI', 'CARTARIA', 'CEMENTO CALCE E GESSO', 'CERAMICHE E VETRARIE', 'CHIMICA', 'MECCANICA', 'METALLI NON FERROSI', 'MEZZI DI TRASPORTO', 'SIDERURGIA']
# zone_secondary_adjustment_levels = ['Continent', 'Sicily', 'Sardinia']


# Set start to one month ago from today
start = (pd.Timestamp.now(tz='Europe/Rome') - pd.DateOffset(months=1)).replace(day=1).normalize()  + pd.Timedelta(days=1) # Start of last month
end = pd.Timestamp.now(tz='Europe/Rome').normalize() + pd.Timedelta(days=1)

# Note: all methods return Pandas DataFrames
df_tload = client.get_total_load(start=start, end=end, bzone=bzone) # Total Load 
df_mload = client.get_market_load(start=start, end=end, bzone=bzone) # Market Load
df_act_gen = client.get_actual_generation(start=start, end=end, gen_type = None)
df_res_gen = client.get_renewable_generation(start=start, end=end, res_gen_type = None)
df_ener_bal = client.get_energy_balance(start=start, end=end, energy_bal_type = None)
df_cap = client.get_installed_capacity(year=2022, gen_type=gen_type) # Fino a 2022

df_xborderschedule = client.get_scheduled_foreign_exchange(start=start, end=end)
df_xborderflow = client.get_physical_foreign_flow(start=start, end=end)

df_internalschedule = client.get_scheduled_internal_exchange(start=start, end=end)
df_internalflow = client.get_physical_internal_flow(start=start, end=end)

df_peakvalley_load = client.get_peak_valley_load(start=start, end=end)
df_peakvalley_load_details = client.get_peak_valley_load_details(start=start, end=end)


current_date = datetime.datetime.now() 
target_date = current_date - relativedelta(months=1)
target_year = target_date.year
target_month = target_date.month
monthly_data_imcei = client.get_IMCEI(year=target_year, month=target_month)
        

# %% May 2025 

df_forecast_load = client.get_forecast_load(start=start, end=end, sessionType = "MGP")
df_costs = client.get_costs(start=start, end=end, sessionType = "MSD1", direction = "UP")
df_quantity = client.get_quantity(start=start, end=end, sessionType = "MSD1", direction = "UP")
df_accepted_offers = client.get_accepted_offers(start=start, end=end, sessionType = "MSD1", direction = "UP")
df_submitted_offers = client.get_submitted_offers(start=start, end=end, sessionType = "MSD1", direction = "UP")
df_prices = client.get_prices(start=start, end=end, priceType = 'MARGINAL', sessionType = "MSD1", direction = "UP")

df_plant_outages = client.get_plant_outages(start=start, end=end)

# %% June 2025

df_detail_available_capacity = client.get_detail_available_capacity(start=start, end=end)

```