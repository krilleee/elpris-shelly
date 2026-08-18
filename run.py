import requests
from ShellyPy import Shelly
import time
from datetime import datetime, timedelta
from rich.console import Console
from rich.text import Text
import pyfiglet

ip = "10.30.10.51"  # IP till Shelly enhet
threshold_price = 0.80  # SEK/kWh

relay_channel = 0  # Vilken utgång som styr elpatronen. Används tex Shelly Pro 2 eller 3 finns 0, 1 och 2.
api_timeout = 10  # Sekunder att vänta på elpris-API:t per försök
shelly_timeout = 5  # Sekunder att vänta på Shelly-enheten per försök
max_attempts = 4  # Försök mot API respektive relä innan vi ger upp
backoff = 5  # Sekunder mellan försöken, dubblas för varje misslyckande
fallback_after = timedelta(hours=1)  # Hur länge reläet får behålla "on" läge vid okänt pris
auto_off_after = timedelta(minutes=20)  # Shelly slår av sig själv om vi tystnar. None = avstängt

# Instans för konsolutskrifter med `textual`
console = Console()

# Väntade driftfel: APIt, reläet, enheten svarar inte som det ska. Sådana hanteras i
# skriptet och kör vidare. Allt annat får krascha eller körs det i systemd får den startar om skriptet.
class OperationalError(Exception):
    pass

class PriceError(OperationalError):
    pass

class RelayError(OperationalError):
    pass

class UnsupportedDevice(RelayError):
    pass

# Försök vid fel och växande paus mellan dem, sätts på "max_attempts" och "backoff".
# Går alla försök åt skogen kastas det sista felet vidare till konsolen.
def retry(description, function, error_types):
    pause = backoff
    for attempt in range(1, max_attempts + 1):
        try:
            return function()
        except UnsupportedDevice:
            raise  # Permanent fel, stänger av
        except error_types as error:
            if attempt == max_attempts:
                raise
            console.print(
                f" ! {description} misslyckades ({error})"
                f" – försök {attempt}/{max_attempts}, nytt om {pause} s",
                style="yellow",
            )
            time.sleep(pause)
            pause *= 2


# ── Priser ────────────────────────────────────────────────────────────────────

# Skapar URL för att hämta dagens priser
def get_url_for_today():
    today = datetime.now().strftime('%Y/%m-%d')
    return f"https://www.elprisetjustnu.se/api/v1/prices/{today}_SE3.json"

# Hämtar dagens priser.
def fetch_prices():
    def call():
        response = requests.get(get_url_for_today(), timeout=api_timeout)
        response.raise_for_status()
        return response.json()

    try:
        return retry("Hämtning av priser", call, (requests.RequestException, ValueError))
    except (requests.RequestException, ValueError) as error:
        raise PriceError(f"API:t svarade inte ({error})") from error

# Plockar ut priset för perioden vi är i just nu.
def get_current_price(prices):
    now = datetime.now().astimezone()
    for period in prices:
        start = datetime.fromisoformat(period["time_start"])
        end = datetime.fromisoformat(period["time_end"])
        if start <= now < end:
            return period["SEK_per_kWh"]
    raise PriceError(f"Ingen prisperiod matchar {now:%Y-%m-%d %H:%M}")


# ── Relä ──────────────────────────────────────────────────────────────────────

# Sätter på reläet och läser tillbaka läget, så vi vet att det gick fram.
#
# När vi slår på reläet skickar vi med en avslagstimer som enheten själv räknar ner.
# Varje ny kontroll förlänger den så länge vi kommer åt den. Så om skriptet dör,
# nätverket faller, servern brinner upp slår Shelly av sig själv efter utsatt tid som sätts på auto_off_after.
def set_relay(turn_on):
    def call():
        # ShellyPy läser av generationen här och stödjer bara 1 och 2. En Gen3 eller
        # Gen4-enhet ger ValueError, vilket annars hade sett ut som ett nätverksfel.
        try:
            shelly = Shelly(ip, timeout=shelly_timeout)
        except ValueError as error:
            raise UnsupportedDevice(f"Enheten på {ip} stöds inte av ShellyPy ({error})") from error

        if turn_on and auto_off_after:
            shelly.relay(relay_channel, turn=True, timer=int(auto_off_after.total_seconds()))
        else:
            shelly.relay(relay_channel, turn=turn_on)
        return shelly.relay(relay_channel)

    # ShellyPy kastar flera olika feltyper vid nätverksstrul, brett except.
    try:
        status = retry(f"Reläet ({'på' if turn_on else 'av'})", call, Exception)
    except UnsupportedDevice:
        raise
    except Exception as error:
        raise RelayError(f"Nådde inte reläet på {ip} utgång {relay_channel} ({error})") from error

    # Gen2 svar med "output". Kolla på denna sedan med Gen1 om det behövs.
    state = status.get("output") if isinstance(status, dict) else None
    if state is not None and state != turn_on:
        raise RelayError(f"Utgång {relay_channel} hamnade i läge {state}, förväntade {turn_on}")

    # Kollar så reläet tagit emot timern, skickar annars varning.
    if turn_on and auto_off_after and isinstance(status, dict) and not status.get("timer_duration"):
        console.print(
            f" ! Utgång {relay_channel} är på, men enheten satte ingen avslagstimer."
            " Fail-safe:n saknas tills nästa lyckade kontroll.",
            style="bold yellow",
        )

# Kontrollerar Shelly-relä efter priset
def apply_price(price_sek):
    # Kontrollera om priset är under tröskelvärdet
    if price_sek < threshold_price:
        set_relay(True)
        text = Text(f" ✓ Relä aktiverat vid pris {price_sek:.2f} SEK/kWh", style="bold green")
        console.print(text)
    else:
        set_relay(False)
        text = Text(f" ✗ Relä avaktiverat vid pris {price_sek:.2f} SEK/kWh", style="bold red")
        console.print(text)


# ── Utskrifter och felhantering ───────────────────────────────────────────────

# Ritar logo inför varje kontroll
def render_header():
    if console.is_terminal: #Så vi slipper få den i journal loggen
        console.clear()

    logo = pyfiglet.figlet_format("Elpris Shelly", font = "slant")
    print(logo)

# Tips som skrivs ut om vi inte nåt reläet.
def print_relay_hint():
    console.print(f"   Kontrollera att ip = \"{ip}\" stämmer och att enheten är strömsatt", style="yellow")
    console.print(f"   Testa från servern: curl http://{ip}/shelly", style="yellow")
    console.print(
        f"   Läs av utgången: curl \"http://{ip}/rpc/Switch.GetStatus?id={relay_channel}\"",
        style="yellow",
    )
    console.print(f"   Testar att komma åt reälaet igen vid nästa prisperiod", style="yellow")

# PrisAPI felhantering så inte reläet står på om vi inte får något pris.
def handle_price_failure(error, last_price):
    console.print(f" ! Kunde inte avgöra priset: {error}", style="bold red")

    without_price = datetime.now() - last_price
    if without_price < fallback_after:
        minutes_left = int((fallback_after - without_price).total_seconds() // 60)
        console.print(
            f" → Behåller reläets läge i {minutes_left} min till, slår av efter det",
            style="yellow",
        )
        return

    try:
        set_relay(False)
        console.print(
            f" ✗ Relä avaktiverat: priset har varit okänt i över"
            f" {int(fallback_after.total_seconds() // 60)} min",
            style="bold red",
        )
    except RelayError as relay_error:
        console.print(f" ! Nådde inte heller reläet: {relay_error}", style="bold red")
        print_relay_hint()

# Relä felhantering.
def handle_relay_failure(error, failing_since):
    console.print(f" ! {error}", style="bold red")

    # Fel generation på enhet.
    if isinstance(error, UnsupportedDevice):
        console.print(
            "   ShellyPy stödjer bara generation 1 och 2. Nyare enheter (Gen3, Gen4)"
            " kräver ett annat bibliotek eller direkta HTTP-anrop mot enheten.",
            style="yellow",
        )
        return

    minutes = int((datetime.now() - failing_since).total_seconds() // 60)
    if auto_off_after:
        console.print(
            f" → Relä onåbart i {minutes} min. Reläet slår av sig självt"
            f" {int(auto_off_after.total_seconds() // 60)} min efter senaste kontakten.",
            style="yellow",
        )
    else:
        console.print(
            f" → Onåbart i {minutes} min. Reläets läge är okänt och kan inte ändras"
            " förrän enheten svarar igen.",
            style="yellow",
        )

    print_relay_hint()


# ── Huvudloop ─────────────────────────────────────────────────────────────────

# Räknar ut nästa kvart: 00, 15, 30 eller 45
def wait_until_next_quarter():
    now = datetime.now()
    next_quarter = (now + timedelta(minutes=15)).replace(second=0, microsecond=0)
    next_quarter = next_quarter.replace(minute=next_quarter.minute // 15 * 15)
    time_to_wait = (next_quarter - now).total_seconds()
    console.print(f" Väntar till nästa prisperiod: {next_quarter:%H:%M}", style="cyan")
    time.sleep(time_to_wait)

# Kontrollera priset varje kvart.
def main():
    last_price = datetime.now()
    relay_failing_since = None

    while True:
        render_header()

        try:
            price_sek = get_current_price(fetch_prices())
        except PriceError as error:
            handle_price_failure(error, last_price)
        else:
            last_price = datetime.now()
            try:
                apply_price(price_sek)
                relay_failing_since = None
            except RelayError as error:
                if relay_failing_since is None:
                    relay_failing_since = datetime.now()
                handle_relay_failure(error, relay_failing_since)

        wait_until_next_quarter()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(" Avslutar.", style="cyan")
