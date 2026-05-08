"""
Generate fallback CSVs for learners when the API is unavailable.

This simulates having a team member on the ground who collects prices
and weather readings via phone calls or SMS when our API is down.

Usage:
    python generate_fallback_data.py
"""

import csv
from market_data import generate_market_prices, get_available_dates, MARKETS
from weather_data import generate_weather


def generate_fallback_csv(output_file: str = "fallback_market_prices.csv"):
    """
    Generate 30 days of fallback market price data in CSV format.

    Args:
        output_file: Path to write CSV file
    """
    available_dates = get_available_dates(days_back=30)

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            "date",
            "market_id",
            "market_name",
            "region",
            "commodity_id",
            "commodity_name",
            "unit",
            "unit_price_ngn",
            "recorded_at",
        ])

        # Generate data for each date and market
        for date in available_dates:
            market_data = generate_market_prices(date)

            for market_record in market_data:
                market_info = market_record["market"]

                for price in market_record["prices"]:
                    writer.writerow([
                        date,
                        market_info["id"],
                        market_info["name"],
                        market_info["region"],
                        price["commodity_id"],
                        price["commodity_name"],
                        price["unit"],
                        price["unit_price_ngn"],
                        price["recorded_at"],
                    ])

    print(f"✓ Generated {output_file} with 30 days of market price data")
    print(f"  Markets: {len(MARKETS)}")
    print(f"  Rows: {len(available_dates) * len(MARKETS) * 8}")  # 8 commodities


def generate_weather_fallback_csv(output_file: str = "fallback_weather.csv"):
    """
    Generate 30 days of fallback weather data in CSV format.

    Args:
        output_file: Path to write CSV file
    """
    available_dates = get_available_dates(days_back=30)

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "date", "market_id", "region", "season",
            "temperature_c", "humidity_percent", "rainfall_mm",
            "wind_speed_kmh", "wind_direction", "sunshine_hours",
            "cloud_cover_percent", "harmattan_active",
            "dust_intensity", "visibility_km", "air_quality_index",
        ])

        for date in available_dates:
            for market_id in MARKETS.keys():
                w = generate_weather(date, market_id)
                writer.writerow([
                    w["date"], w["market_id"], w["region"], w["season"],
                    w["temperature_c"], w["humidity_percent"], w["rainfall_mm"],
                    w["wind_speed_kmh"], w["wind_direction"], w["sunshine_hours"],
                    w["cloud_cover_percent"], w["harmattan_active"],
                    w["dust_intensity"], w["visibility_km"], w["air_quality_index"],
                ])

    print(f"✓ Generated {output_file} with 30 days of weather data")
    print(f"  Markets: {len(MARKETS)}")
    print(f"  Rows: {len(available_dates) * len(MARKETS)}")


if __name__ == "__main__":
    generate_fallback_csv()
    generate_weather_fallback_csv()
