# Given a house price, find the bill per month if the house is bought with a 360 month loan
house_price = 1800 * 1e4
loan = house_price * 0.8
cash = house_price * 0.2
rate = 0.0215
num_month = 360
house_rent = 30000
decay_rate = 0.014

# Other constants
cpi_inflation = 0.02
rent_inflation = 0.02
house_infaltion = 0.03
stock_inflation = 0.06