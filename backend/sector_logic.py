"""Sector membership detection module."""
from typing import List, Tuple, Optional


# Toronto–Ottawa incoming airports (IATA + ICAO where applicable)
TARGET_ARR_AIRPORTS = {
    "YYZ",  # Toronto Pearson
    "CYYZ",
    "YTZ",  # Billy Bishop Toronto City
    "CYTZ",
    "YHM",  # Hamilton
    "CYHM",
    "YKF",  # Waterloo
    "CYKF",
    "YOW",  # Ottawa
    "CYOW",
}


def is_flight_in_sector(arr_airport: Optional[str]) -> bool:
    """
    Determine if a flight is in sector based on arrival airport.

    A flight is "in sector" if it is arriving into Toronto or Ottawa airports.
    """
    if not arr_airport:
        return False
    return str(arr_airport).upper() in TARGET_ARR_AIRPORTS


def mark_sector_membership(df):
    """Add in_sector column to dataframe."""
    df['in_sector'] = df['arr_airport'].apply(is_flight_in_sector)
    return df
