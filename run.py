import requests
from ShellyPy import Shelly
import time
from datetime import datetime

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

# Loop för att kontrollera priset varje timme
while True:
    check_prices()
    time.sleep(3600)  # Vänta en timme innan nästa kontroll