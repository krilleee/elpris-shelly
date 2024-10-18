import requests
from ShellyPy import Shelly
import time
from datetime import datetime, timedelta

# Hämta elpriserna från elprisetjustnu.se
url = "https://www.elprisetjustnu.se/api/v1/prices/2024/10-07_SE3.json"
threshold_price = 0.4  # SEK/kWh

# Funktion för att kolla priset och kontrollera Shelly-relä
def check_prices():
    response = requests.get(url)
    prices = response.json()

    current_hour = datetime.now().hour  # Hämta aktuell timme
    price_sek = prices[current_hour]["SEK_per_kWh"]

    # Anslut till Shelly
    shelly = Shelly("10.30.10.51")
    
    # Kontrollera om priset är under tröskelvärdet
    if price_sek < threshold_price:
        shelly.relay(0, turn=True)
        print(current_hour)
        print(f"Relä aktiverat vid pris {price_sek} SEK/kWh")
    else:
        shelly.relay(0, turn=False)
        print(current_hour)
        print(f"Relä avaktiverat vid pris {price_sek} SEK/kWh")

# Funktion för att vänta till nästa hel timme
def wait_until_next_hour():
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    time_to_wait = (next_hour - now).total_seconds()
    print(f"Väntar till nästa hel timme: {next_hour}")
    time.sleep(time_to_wait)

# Loop för att kontrollera priset varje timme
while True:
    check_prices()
    wait_until_next_hour()  # Väntar tills nästa timme innan den kör igen