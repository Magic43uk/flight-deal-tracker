def main():
    DAYS_AHEAD_TO_SCAN = 60
    TRIP_LENGTH_DAYS = 7  # Change this to 4 or 7 depending on your preference!

    start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    # Extend end_date so round-trip returns fit within the scanning window
    end_date = (datetime.now() + timedelta(days=DAYS_AHEAD_TO_SCAN + TRIP_LENGTH_DAYS)).strftime("%Y-%m-%d")

    search = SearchDates()
    cheapest_overall = None

    for london_airport in LONDON_AIRPORTS:
        try:
            filters = DateSearchFilters(
                flight_segments=[
                    # 1. Outbound flight: WRO -> London
                    FlightSegment(
                        departure_airport=[[Airport.WRO, 0]],
                        arrival_airport=[[london_airport, 0]],
                        travel_date=start_date,
                    ),
                    # 2. Return flight: London -> WRO (Fixed trip length)
                    FlightSegment(
                        departure_airport=[[london_airport, 0]],
                        arrival_airport=[[Airport.WRO, 0]],
                        travel_date=start_date, # Google Flights matches this with trip duration filters/dates
                    )
                ],
                from_date=start_date,
                to_date=start_date + timedelta(days=DAYS_AHEAD_TO_SCAN) if isinstance(start_date, datetime) else end_date, # handled via date range
                seat_type=SeatType.ECONOMY,
                stops=MaxStops.ANY,
                passenger_info=PassengerInfo(adults=1),
            )

            # Note: For round trips, you can also specify trip duration if supported by the library, 
            # or let Google Flights find combinations for the specified segments.
            
            results = search.search(filters)
            if not results:
                continue

            best_for_airport = min(results, key=lambda x: x.price)
            print(f"WRO <-> {london_airport.name} ({TRIP_LENGTH_DAYS} days): Best price {best_for_airport.price}")

            raw_date = best_for_airport.date
            if isinstance(raw_date, (list, tuple)):
                raw_date = raw_date[0]
            date_str = raw_date.strftime("%Y-%m-%d") if hasattr(raw_date, "strftime") else str(raw_date)[:10]

            if cheapest_overall is None or best_for_airport.price < cheapest_overall["price"]:
                cheapest_overall = {
                    "airport": london_airport.name,
                    "date": date_str,
                    "price": best_for_airport.price,
                }

        except Exception as e:
            print(f"Error checking {london_airport.name}: {e}")

    if cheapest_overall:
        print(f"\n🏆 Cheapest round-trip: {cheapest_overall['price']} PLN to {cheapest_overall['airport']}")
        if cheapest_overall["price"] <= MAX_PRICE_PLN:
            send_discord_alert(
                airport_code=cheapest_overall["airport"],
                date_str=cheapest_overall["date"],
                price_pln=cheapest_overall["price"],
            )
