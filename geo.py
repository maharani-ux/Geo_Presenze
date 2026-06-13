"""
services/geo.py
───────────────
Geolocation helpers using the Haversine formula via geopy.
"""
from geopy.distance import geodesic


def check_location(
    student_lat: float,
    student_lng: float,
    campus_lat:  float,
    campus_lng:  float,
    radius_m:    float,
) -> tuple[float, bool]:
    """
    Calculate distance between student and campus centre.

    Returns:
        (distance_metres, is_within_zone)
    """
    student_point = (student_lat, student_lng)
    campus_point  = (campus_lat,  campus_lng)
    distance = geodesic(student_point, campus_point).meters
    return distance, distance <= radius_m


def is_gps_suspicious(accuracy_metres: float | None) -> bool:
    """
    Heuristic: real phones report GPS accuracy of 5–30 m.
    Spoofed / mocked locations often report exactly 0 or 1 m.
    """
    if accuracy_metres is None:
        return False
    return accuracy_metres < 2.0
