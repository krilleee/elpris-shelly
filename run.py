import requests
from ShellyPy import Shelly
import time
from datetime import datetime, timedelta
from rich.console import Console
from rich.text import Text
import pyfiglet

ip = "10.30.10.51"  # IP till Shelly enhet
threshold_price = 0.10  # SEK/kWh

# Instans för konsolutskrifter med `textual`
console = Console()

# Skapar URL för att hämta dagens priser
def get_url_for_today():
    today = datetime.now().strftime('%Y/%m-%d')
    return f"https://www.elprisetjustnu.se/api/v1/prices/{today}_SE3.json"

# Hämtar aktuellt pris och kontrollerar Shelly-relä
def check_prices():
    console.clear()

    logo = pyfiglet.figlet_format("Elpris Shelly", font = "slant") 
    print(logo)

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
        text = Text(f" ✓ Relä aktiverat vid pris {price_sek:.2f} SEK/kWh", style="bold green")
        console.print(text)
    else:
        shelly.relay(0, turn=False)
        text = Text(f" ✗ Relä avaktiverat vid pris {price_sek:.2f} SEK/kWh", style="bold red")
        console.print(text)

# Räknar ut nästa heltimme
def wait_until_next_hour():
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    time_to_wait = (next_hour - now).total_seconds()
    console.print(f" Väntar till nästa hel timme: {next_hour}", style="cyan")
    time.sleep(time_to_wait)

# Loop för att kontrollera priset varje timme
while True:
    check_prices()
    wait_until_next_hour()