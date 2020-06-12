import requests

from error import LocationNotFoundError


def get_ip_location():
    ''' Get the geolocation of the user via a request to IP geolocation API '''

    response = requests.get('https://ipapi.co/json/')

    try:
        response.raise_for_status()
    except requests.HTTPError:
        raise LocationNotFoundError()

    data = response.json()

    if data.get('error') is True or data.get('city') is None:
        raise LocationNotFoundError()

    return data