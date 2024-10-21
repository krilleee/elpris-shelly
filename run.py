import requests
from ShellyPy import Shelly
import time
from datetime import datetime, timedelta

ip = "10.30.10.51" # IP till Shelly enhet
threshold_price = 0.10 # SEK/kWh

# Skapar url för att hämta dagens priser
def get_url_for_today():
    today = datetime.now().strftime('%Y/%m-%d')
    return f"https://www.elprisetjustnu.se/api/v1/prices/{today}_SE3.json"

threshold_price = 0.10  # SEK/kWh

# Hämtar akturellt pris och kontrollerar Shelly-relä
def check_prices():
    url = get_url_for_today()
    response = requests.get(url)
    prices = response.json()

    current_hour = datetime.now().hour
    price_sek = prices[current_hour]["SEK_per_kWh"]

    # Anslut till Shelly
    shelly = Shelly(ip)
    
    # Kontrollera om priset är under tröskelvärdet
    if price_sek < threshold_price:
        shelly.relay(0, turn=True)
        print(url) #För temporär koll
        print(f"Relä aktiverat vid pris {price_sek} SEK/kWh")
    else:
        shelly.relay(0, turn=False)
        print(url) #För temporär koll
        print(f"Relä avaktiverat vid pris {price_sek} SEK/kWh")

# Räknar ut nästa heltimme
def wait_until_next_hour():
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    time_to_wait = (next_hour - now).total_seconds()
    print(f"Väntar till nästa hel timme: {next_hour}")
    time.sleep(time_to_wait)

# Loop för att kontrollera priset varje timme
while True:
    check_prices()
    wait_until_next_hour()