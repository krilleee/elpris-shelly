import requests
from ShellyPy import Shelly
import time
from datetime import datetime, timedelta
from rich.console import Console
from rich.text import Text
import pyfiglet

ip = "10.30.10.52"  # IP till Shelly enhet
threshold_price = 0.10  # SEK/kWh

# Instans för konsolutskrifter med `textual`
console = Console()

# Skapar URL för att hämta dagens priser
def get_url_for_today():
    today = datetime.now().strftime('%Y/%m-%d')
    return f"https://www.elprisetjustnu.se/api/v1/prices/{today}_SE3.json"

# Plockar ut priset för perioden vi är i just nu.
def get_current_price(prices):
    now = datetime.now().astimezone()
    for period in prices:
        start = datetime.fromisoformat(period["time_start"])
        end = datetime.fromisoformat(period["time_end"])
        if start <= now < end:
            return period["SEK_per_kWh"]
    raise LookupError(f"Ingen prisperiod matchar {now:%Y-%m-%d %H:%M}")

# Hämtar aktuellt pris och kontrollerar Shelly-relä
def check_prices():
    console.clear()

    logo = pyfiglet.figlet_format("Elpris Shelly", font = "slant") 
    print(logo)

    url = get_url_for_today()
    response = requests.get(url)
    prices = response.json()

    price_sek = get_current_price(prices)

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

# Räknar ut nästa kvart: 00, 15, 30 eller 45
def wait_until_next_quarter():
    now = datetime.now()
    next_quarter = (now + timedelta(minutes=15)).replace(second=0, microsecond=0)
    next_quarter = next_quarter.replace(minute=next_quarter.minute // 15 * 15)
    time_to_wait = (next_quarter - now).total_seconds()
    console.print(f" Väntar till nästa prisperiod: {next_quarter:%H:%M}", style="cyan")
    time.sleep(time_to_wait)

# Loop för att kontrollera priset varje kvart
while True:
    check_prices()
    wait_until_next_quarter()