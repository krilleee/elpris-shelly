import requests
from ShellyPy import Shelly

# Hämta elpriserna från elprisetjustnu.se
url = "https://www.elprisetjustnu.se/api/v1/prices/2024/10-07_SE3.json"
response = requests.get(url)
prices = response.json()

# Ange ett tröskelvärde i SEK/kWH
threshold_price = 1.50

for price_data in prices:
    price_sek = price_data["SEK_per_kWh"]
    if price_sek < threshold_price:
        # Anslut till Shelly
        #shelly = Shelly("IP_TILL_DIN_SHELLY_ENHET")
        # Slå på reläet om priset är lägre än tröskelvärdet
        #shelly.relay(0, turn=True)
        print(f"Relä aktiverat vid pris {price_sek} SEK/kWh")
    else:
        # Slå av reläet om priset är högre än tröskelvärdet
        #shelly.relay(0, turn=False)
        print(f"Relä avaktiverat vid pris {price_sek} SEK/kWh")