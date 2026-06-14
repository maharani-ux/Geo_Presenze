from geopy.distance import geodesic

def check_location(slat, slng, clat, clng, radius_m):
    dist = geodesic((slat, slng), (clat, clng)).meters
    return dist, dist <= radius_m

def is_gps_suspicious(accuracy):
    return accuracy is not None and accuracy < 2
