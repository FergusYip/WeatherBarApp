''' DrinkMore is a MacOS menu bar app to remind you to drink more water '''

import datetime
import json
import os
import webbrowser
import ssl

import rumps
import requests
import geopy
from geopy.geocoders import Nominatim

from error import LocationNotFoundError
from climacell import ClimaCell, APIKeyError
from ip_api import get_ip_location

ssl._create_default_https_context = ssl._create_unverified_context

GEOCODER = Nominatim(user_agent='WeatherBar')
INTERVAL_SECONDS = 300
CONFIG_FILE = 'config.json'

WEATHER_ICONS = {
    '☀️': ['clear'],
    '⛅': ['partly_cloudy'],
    '⛈': ['tstorm'],
    '🌤': ['mostly_clear'],
    '🌥': ['mostly_cloudy'],
    '☁️': ['cloudy'],
    '🌧': ['rain_heavy', 'rain', 'rain_light', 'drizzle'],
    '🌨': [
        'snow_heavy',
        'snow',
        'snow_light',
        'flurries',
        'freezing_rain_heavy',
        'freezing_rain',
        'freezing_rain_light',
        'freezing_drizzle',
        'ice_pellets_heavy',
        'ice_pellets',
        'ice_pellets_light',
    ],
    '🌫': ['fog', 'fog_light'],
}


def get_icon(weather_code):
    ''' Get weather icon from weather code '''
    for emoji in WEATHER_ICONS:
        if weather_code in WEATHER_ICONS[emoji]:
            return emoji
    return None


class WeatherBarApp(rumps.App):
    ''' WeatherBarApp '''
    def __init__(self):
        super(WeatherBarApp, self).__init__('WeatherBar')

        self.last_updated_menu = rumps.MenuItem(title='')
        self.display_units = rumps.MenuItem(title='',
                                            callback=self.change_units)

        # App Menu ----------------------------------------------

        self.menu.add(self.last_updated_menu)

        self.menu.add(rumps.separator)  # -----------------------

        self.menu.add(self.display_units)
        self.menu.add(rumps.MenuItem(title='Change Location'))

        self.menu.add(rumps.separator)  # -----------------------

        self.menu.add(rumps.MenuItem(title='About'))

        # -------------------------------------------------------

        self.default_config = {
            'location': '175 5th Avenue NYC',
            'latitude': 40.7410861,
            'longitude': -73.9896297241625,
            'unit_system': 'si',
            'apikey': '',
        }
        self.config = self.default_config

        self.weather = None
        self.temp = None

        self.timer = rumps.Timer(self.update_weather_timer, INTERVAL_SECONDS)

        self.climacell = ClimaCell()

        self.start()

    def start(self):
        ''' Restoring the config and start the timer '''
        detect_location = False

        try:
            self.config = self.read_config()
        except FileNotFoundError:
            # First time running app
            detect_location = True
        except:  # IncompatibleConfigError:
            rumps.alert(title='Something went wrong whilst loading settings',
                        message='Default settings have been applied')
            detect_location = True

        if not self.config['apikey']:
            print('ERROR: API Key is missing')
            self.handle_missing_apikey()

        if detect_location:
            try:
                self.config = self.local_config()
            except LocationNotFoundError:
                print('Could not get current location')
            except requests.ConnectionError:
                print('Could not get current location')
            except Exception as err:
                print(err)

        self.climacell.set_location(self.config['latitude'],
                                    self.config['longitude'])
        self.climacell.set_unit_system(self.config['unit_system'])
        self.climacell.set_apikey(self.config['apikey'])

        self.save_config()

        self.update_display_units()

        # Call to verify connection
        self.update_weather(silent=False)

        self.timer.start()

    def handle_missing_apikey(self):
        ''' Open window to alert user of missing api key '''

        print('Opening \'API Key is required\' window')

        response = rumps.alert(
            title='ClimaCell API Key is required',
            message=(
                'Click \"Register\" or go to the following url:\n'
                f'{self.climacell.signup_link}\n\n'
                'Note: This application is not affiliated with ClimaCell'),
            ok='Register',
            cancel='Quit',
            other='I have one')

        if response == 0:  # Quit
            rumps.quit_application()

        if response == 1:  # Register
            webbrowser.open(self.climacell.signup_link)

        if not self.set_apikey():  # Cancelled enter api key window
            self.handle_missing_apikey()  # Reopen api required alert

    def set_apikey(self):
        ''' Open window to set api key '''
        api_key_window = rumps.Window(
            title='Enter your API key:',
            message='Right click to paste',
            default_text=self.config['apikey'],
            ok='Confirm',
            cancel='I don\'t have one',
            dimensions=(250, 20),
        )

        response = api_key_window.run()

        if response.clicked == 0:  # Cancel
            return False

        apikey = response.text.strip()

        if not apikey:
            print('ERROR: API Key is not entered')
            rumps.alert(title='You did not enter an API Key',
                        message='Try again')
            return self.set_apikey()

        self.config['apikey'] = apikey
        self.climacell.set_apikey(apikey)
        self.save_config()

        return True

    def update_weather_timer(self, _):
        ''' Function to call update_weather from timer '''
        self.update_weather()

    def update_weather(self, silent=True):
        ''' Update the weather '''
        print('Updating weather')

        try:
            self.weather = self.climacell.get_weather()
            self.temp = int(round(self.weather['temp']['value'], 0))
            self.update_time()
            self.update_title()
        except APIKeyError:
            print('ERROR: API Key is not valid')
            rumps.alert(title='ClimaCell API Key is not valid',
                        message='Please make sure it is correct.')
            if not self.set_apikey():
                self.handle_missing_apikey()
            self.update_weather()
        except LocationNotFoundError:
            print('ERROR: Data for this location is not found')
            rumps.alert(title='Location data not found',
                        message='Please enter another location.')
            self.prefs()
        except requests.ConnectionError:
            print('ERROR: Connection Error')
            self.handle_connection_error(silent=silent)

    def update_title(self, title=None):
        ''' Update the app title in the menu bar'''
        print('Updating title')

        if title:
            self.title = title
            return

        emoji = get_icon(self.weather['weather_code']['value'])
        temp = int(round(self.temp, 0))
        self.title = f'{emoji} {temp}°'

    def update_time(self, time=None):
        ''' Update the last updated time in the app menu '''
        print('Updating time')

        if time:
            self.last_updated_menu.title = time
            return

        now = datetime.datetime.now()
        formatted = now.strftime("%b %d %H:%M:%S")
        self.last_updated_menu.title = formatted

    def update_display_units(self):
        ''' Update the units displayed in the app menu '''
        print('Updating display units')
        if self.config['unit_system'] == 'si':
            self.display_units.title = 'Metric Units (C)'
        else:
            self.display_units.title = 'Imperial Units (F)'

    def change_units(self, _):
        ''' Toggle between metric and imperial units '''
        print('Changing units')

        if self.config['unit_system'] == 'si':
            self.config['unit_system'] = 'us'
            self.temp = to_fahrenheit(self.temp)
        else:
            self.config['unit_system'] = 'si'
            self.temp = to_celsius(self.temp)

        self.climacell.set_unit_system(self.config['unit_system'])
        self.update_title()
        self.update_display_units()
        self.save_config()

    @rumps.clicked('Change Location')
    def settings(self, _):
        ''' Open the settings window '''
        self.prefs()

    def prefs(self, current_location=None):
        ''' Settings window '''

        print('Opened settings window')

        if not current_location:
            current_location = self.config['location']

        settings_window = rumps.Window(
            title='Enter your location:',
            message='Right click to paste',
            default_text=f'{current_location}',
            ok='Apply',
            cancel='Cancel',
            dimensions=(400, 40),
        )
        settings_window.add_button('Use Current Location')
        response = settings_window.run()

        # Cancel
        if response.clicked == 0:
            return

        # Use current location
        if response.clicked == 2:
            try:
                self.config = self.local_config()
                self.climacell.set_location(self.config['latitude'],
                                            self.config['longitude'])
                location = self.config['location']
                print(f'Successfully changed location to {location}')

                self.save_config()

                rumps.alert(
                    title='Success!',
                    message=f'Your location has been changed to {location}.')

                self.update_weather()
                return
            except LocationNotFoundError:
                print('Could not get current location')
                rumps.alert(title='Location not found',
                            message='Could not obtain your current location')
                self.prefs(current_location)
                return
            except requests.ConnectionError:
                print('ERROR: Connection error')
                self.handle_connection_error()
                self.prefs(current_location)
                return
            except Exception as err:
                print(err)

        if not response.text:
            print('ERROR: Empty location input')
            rumps.alert(title='Location cannot be empty', message='Try again')
            self.prefs(current_location)
            return

        location = response.text

        try:
            geolocation = GEOCODER.geocode(location)
        except geopy.exc.GeocoderServiceError:
            print('ERROR: Connection error')
            self.handle_connection_error()
            self.prefs(current_location)
            return
        except:
            print('ERROR: Someting went wrong with geopy')
            rumps.alert(title='Soemthing went wrong with geopy')
            rumps.quit_application()

        if geolocation is None:
            print('ERROR: Location not found')
            rumps.alert(title='Could not find your location',
                        message='Try again')
            self.prefs(location)
            return

        self.confirm_location(geolocation)

        latitude = geolocation.latitude
        longitude = geolocation.longitude

        self.config = modify_location(self.config, location, latitude,
                                      longitude)
        self.climacell.set_location(latitude, longitude)

        print(f'Successfully changed location to {location}')

        self.save_config()

        rumps.alert(title='Success!',
                    message=f'Your location has been changed to {location}.')

        self.update_weather()

    def save_config(self):
        ''' Save the config to a JSON file in the application support folder '''
        filename = CONFIG_FILE
        filepath = os.path.join(rumps.application_support(self.name), filename)
        with open(filepath, mode='w') as config_file:
            print('Saving config')
            json.dump(self.config, config_file)

    def read_config(self):
        ''' Load the config to a JSON file in the application support folder '''
        filename = CONFIG_FILE
        filepath = os.path.join(rumps.application_support(self.name), filename)
        with open(filepath, mode='r') as config_file:
            config = json.load(config_file)

            if not valid_config(config, self.default_config):
                raise IncompatibleConfigError()

            return config

    def local_config(self):
        '''
        Return a version of the current config where the location values are
        set to the current location of the user
        '''
        location = get_location()

        try:
            is_valid = valid_geopy_location(location['lat'], location['lon'])
        except geopy.exc.GeocoderServiceError:
            raise requests.ConnectionError()

        if not is_valid:
            raise LocationNotFoundError
        self.confirm_location(location['location'])
        return modify_location(self.config, location['location'],
                               location['lat'], location['lon'])

    def confirm_location(self, location):
        '''
        Create an alert window to ask if the location is correct.
        If incorrect, open the settings window.
        '''
        is_correct = rumps.alert(title='Is this your location?',
                                 message=location,
                                 ok='Yes',
                                 cancel='No')
        if not is_correct:
            return self.prefs(location)

        return is_correct

    def handle_connection_error(self, silent=False):
        # Do nothing
        if silent:
            return

        self.update_title('❕')
        self.update_time('No Connection')
        rumps.alert(title='Unable to get weather data',
                    message='Please check your internet connection.')

    @rumps.clicked('About')
    def about(self, _):
        ''' Send alert window displaying application information '''
        rumps.alert(
            title='About',
            message=(
                'Developed by Wai Lam Fergus Yip.\n'
                'Weather information provided by ClimaCell API\n'
                'Geocoding provided by GeoPy Contributors and IP-API\n'
                'Icon by Catalin Fertu, reused under the CC BY License.\n\n'
                'https://github.com/FergusYip/WeatherBarApp'))


def to_fahrenheit(celsius):
    ''' Convert celsius to fahrenheit '''
    return 9.0 / 5.0 * celsius + 32


def to_celsius(fahrenheit):
    ''' Convert fahrenheit to celsius '''
    return (fahrenheit - 32) * 5.0 / 9.0


def valid_config(config, reference_config):
    ''' Check if a config is valid according to a reference config '''
    for key in reference_config:
        if not isinstance(config.get(key), type(reference_config[key])):
            return False
    return True


def get_location():
    ''' Get the geolocation of the user via a request to IP-API '''
    data = get_ip_location()

    city = data['city']
    zip_code = data['zip']
    region = data['regionName']
    country = data['country']

    city_zip = ' '.join([city, zip_code])

    return {
        'lat': data['lat'],
        'lon': data['lon'],
        'location': ', '.join([city_zip, region, country])
    }


def valid_geopy_location(latitude, longitude):
    ''' Check if a coordinate is a valid geopy geolocation '''
    return bool(GEOCODER.reverse((latitude, longitude)))


def modify_location(config, location=None, latitude=None, longitude=None):
    '''
    Return a config where the location, latitude, and longitude are different
    '''
    modified_config = dict(config)
    if location:
        modified_config['location'] = location
    if latitude:
        modified_config['latitude'] = latitude
    if longitude:
        modified_config['longitude'] = longitude
    return modified_config


class IncompatibleConfigError(Exception):
    """
    Exception raised for errors in the config.

    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message="Config was read but was not compatible."):
        self.message = message
        super().__init__(self.message)


if __name__ == '__main__':
    WeatherBarApp().run()
