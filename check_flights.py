import os
from datetime import datetime, timedelta
import requests
from fli.search import SearchDates
from fli.models import DateSearchFilters, FlightSegment, Airport, SeatType, MaxStops

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Target price in PLN (e.g., 150 PLN one-way)
MAX_PRICE_PLN = 150
DAYS_AHEAD_TO_SCAN = 60  # Scans the next 2 months for the cheapest date

# All London airports serviced from Wroclaw (Ryanair uses STN/LTN, Wizz Air uses LGW/LTN, BA/LOT use LHR)
LONDON_AIRPORTS = [Airport.STN, Airport.LTN, Airport.LGW, Airport.LHR]


def send_discord_alert(airport_code, date_str, price_pln):
    if not WEBHOOK_URL:
        print("Missing DISCORD_WEBHOOK_URL secret.")
        return

    google_flights_link = (
        f"https://www.google.com/travel/flights?q=One%20way%20flights%20to%20{airport_code}"
        f"%20from%20WRO%20on%20{date_str}&curr=PLN"
    )

    payload = {
        "embeds": [
            {
                "title": f"✈️ Cheap Flight Found: WRO ➡️ {airport_code} (London)",
                "url": google_flights_link,
                "description": (
                    f"**Price:** {price_pln} PLN (Target: ≤ {MAX_PRICE_PLN} PLN)\n"
                    f"**Date:** {date_str}\n"
                    f"**Destination Airport:** {airport_code}"
                ),
                "color": 5763719,
            }
        ]
    }
    requests.post(WEBHOOK_URL, json=payload, timeout=15)


def main():
    start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=DAYS_AHEAD_TO_SCAN)).strftime("%Y-%m-%d")

    search = SearchDates()
    cheapest_overall = None

    for london_airport in LONDON_AIRPORTS:
        try:
            filters = DateSearchFilters(
                flight_segments=[
                    FlightSegment(
                        departure_airport=[[Airport.WRO, 0]],
                        arrival_airport=[[london_airport, 0]],
                        travel_date=start_date,
                    )
                ],
                from_date=start_date,
                to_date=end_date,
                seat_type=SeatType.ECONOMY,
                stops=MaxStops.ANY,
            )

            results = search.search(filters)
            if not results:
                continue

            # Find the cheapest date for this specific London airport
            best_for_airport = min(results, key=lambda x: x.price)
            print(f"WRO -> {london_airport.name}: Best price {best_for_airport.price} on {best_for_airport.date}")

            if cheapest_overall is None or best_for_airport.price < cheapest_overall["price"]:
                cheapest_overall = {
                    "airport": london_airport.name,
                    "date": best_for_airport.date[0] if isinstance(best_for_airport.date, list) else str(best_for_airport.date),
                    "price": best_for_airport.price,
                }

        except Exception as e:
            print(f"Error checking {london_airport.name}: {e}")

    if cheapest_overall:
        print(f"\n🏆 Cheapest overall: {cheapest_overall['price']} on {cheapest_overall['date']} to {cheapest_overall['airport']}")
        if cheapest_overall["price"] <= MAX_PRICE_PLN:
            send_discord_alert(
                airport_code=cheapest_overall["airport"],
                date_str=cheapest_overall["date"],
                price_pln=cheapest_overall["price"],
            )


if __name__ == "__main__":
    main()
