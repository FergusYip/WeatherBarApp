import requests

from error import LocationNotFoundError


def get_ip_location():
    ''' Get the geolocation of the user via a request to IP-API '''

    response = requests.get('http://ip-api.com/json/')

    try:
        response.raise_for_status()
    except requests.HTTPError:
        raise LocationNotFoundError()

    data = response.json()

    if data['status'] == 'fail':
        raise LocationNotFoundError()

    return data