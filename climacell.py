''' Module for accessing ClimaCell Weather API '''
import requests

from error import LocationNotFoundError

SIGNUP_LINK = 'https://developer.climacell.co/sign-up'


class ClimaCell:
    def __init__(self):
        self.latitude = None
        self.longitude = None
        self.unit_system = None
        self.apikey = None
        self.signup_link = SIGNUP_LINK

    def get_weather(self, fields=['temp', 'weather_code']):
        ''' Get weather from API '''
        querystring = {
            'lat': self.latitude,
            'lon': self.longitude,
            'unit_system': self.unit_system,
            'apikey': self.apikey,
            'fields': fields
        }

        url = 'https://api.climacell.co/v3/weather/realtime'
        response = requests.get(url, params=querystring)

        try:
            response.raise_for_status()
        except requests.HTTPError:
            status_code = response.status_code
            if status_code == 403:
                raise APIKeyError()
            elif status_code == 404:
                raise LocationNotFoundError()

        return response.json()

    def set_location(self, latitude, longitude):
        if any(map(lambda x: not isinstance(x, float), (latitude, longitude))):
            raise TypeError(
                'Expected latitude and longitude to be of type float')

        self.latitude = latitude
        self.longitude = longitude

    def set_unit_system(self, unit_system):
        if not isinstance(unit_system, str):
            raise TypeError('Expected unit_system to be of type string')

        self.unit_system = unit_system

    def set_apikey(self, apikey):
        if not isinstance(apikey, str):
            raise TypeError('Expected apikey to be of type string')
        self.apikey = apikey

    def __str__(self):
        return str({
            'latitude': self.latitude,
            'longituded': self.longitude,
            'unit_system': self.unit_system,
            'apikey': self.apikey,
        })


class APIKeyError(Exception):
    """
    Exception raised when the API key is invalid

    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message="API key is invalid"):
        self.message = message
        super().__init__(self.message)
