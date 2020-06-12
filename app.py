''' DrinkMore is a MacOS menu bar app to remind you to drink more water '''

import datetime
import os
import webbrowser
import ssl
import logging

import rumps
import requests
import geopy
from geopy.geocoders import Nominatim

from error import LocationNotFoundError
from climacell import ClimaCell, APIKeyError
from ip_api import get_ip_location
from config import Config, valid_config

ssl._create_default_https_context = ssl._create_unverified_context

APP_NAME = 'WeatherBar'
GEOCODER = Nominatim(user_agent=APP_NAME)
INTERVAL_SECONDS = 300
CONFIG_NAME = 'config.json'
APP_SUPPORT_DIR = rumps.application_support(APP_NAME)
CONFIG = Config(APP_SUPPORT_DIR, CONFIG_NAME)

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
        self.logger = self.logger_init()
        self.logger.info('Initialising application...')

        self.template = True

        self.menu_items = {
            'last_updated_menu':
            rumps.MenuItem(title=''),
            'display_units':
            rumps.MenuItem(
                title='',
                callback=self.change_units,
            ),
            'change_location':
            rumps.MenuItem(
                title='Change Location',
                callback=self.settings,
            ),
            "live_location":
            rumps.MenuItem(
                title='Live Location',
                callback=self.live_location,
            ),
        }

        # App Menu ----------------------------------------------

        self.menu.add(self.menu_items['last_updated_menu'])

        self.menu.add(rumps.separator)  # -----------------------

        self.menu.add(self.menu_items['display_units'])
        self.menu.add(self.menu_items['live_location'])
        self.menu.add(self.menu_items['change_location'])

        self.menu.add(rumps.separator)  # -----------------------

        self.menu.add(rumps.MenuItem(title='About', callback=self.about))

        # -------------------------------------------------------

        self.default_config = {
            'location': '175 5th Avenue NYC',
            'latitude': 40.7410861,
            'longitude': -73.9896297241625,
            'unit_system': 'si',
            'apikey': '',
            'live_location': False,
        }
        self.config = self.default_config

        self.weather = None
        self.temp = 0

        self.timer = rumps.Timer(self.update_weather_timer, INTERVAL_SECONDS)

        self.climacell = ClimaCell()

        self.start()

    def start(self):
        ''' Restoring the config and start the timer '''
        self.logger.info('Running start script')
        detect_location = False

        try:
            self.logger.info('Trying to read config')
            config = CONFIG.read()
            if not valid_config(config, self.default_config):
                raise IncompatibleConfigError()
            self.config = config
        except FileNotFoundError:
            # First time running app
            self.logger.info('Config file not found')
            detect_location = True
        except:
            self.logger.info('Config file was incompatible')
            rumps.alert(title='Something went wrong whilst loading settings',
                        message='Default settings have been applied')
            detect_location = True

        if not self.config['apikey']:
            self.logger.error('ClimaCell API key is misising')
            self.handle_missing_apikey()

        if detect_location:
            try:
                self.logger.info('Tying to load local config')
                local_config = self.local_config()
            except LocationNotFoundError:
                self.logger.error(
                    'LocationNotFoundError: Coud not get current location')
            except requests.ConnectionError:
                self.logger.error(
                    'ConnectionError: Coud not get current location')
            except:
                self.logger.exception(
                    'Something went wrong whilst loading local config')

            if not self.confirm_location(local_config['location']):
                self.prefs(local_config['location'])
                return
            self.config = local_config

        self.climacell.set_location(self.config['latitude'],
                                    self.config['longitude'])
        self.climacell.set_unit_system(self.config['unit_system'])
        self.climacell.set_apikey(self.config['apikey'])

        self.menu_items['live_location'].state = self.config['live_location']

        CONFIG.save(self.config)

        self.update_display_units()

        # Call to verify connection
        self.update_weather(silent=False)

        self.logger.info('Starting timer')
        self.timer.start()

    def handle_missing_apikey(self):
        ''' Open window to alert user of missing api key '''

        self.logger.info('Opening \'API Key is required\' window')

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
            self.logger.info('Quiting application')
            rumps.quit_application()

        if response == 1:  # Register
            self.logger.info('Opening register link')
            webbrowser.open(self.climacell.signup_link)

        if not self.set_apikey():  # Cancelled enter api key window
            self.handle_missing_apikey()  # Reopen api required alert

    def set_apikey(self):
        ''' Open window to set api key '''
        self.logger.info('Opening \'set_apikey\' window')
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
            self.logger.info('Cancelled \'set_apikey\' window')
            return False

        apikey = response.text.strip()

        if not apikey:
            self.logger.info('API Key was not entered')
            rumps.alert(title='You did not enter an API Key',
                        message='Try again')
            return self.set_apikey()

        self.logger.info('Setting API Key')
        self.config['apikey'] = apikey
        self.climacell.set_apikey(apikey)
        CONFIG.save(self.config)

        return True

    def update_weather_timer(self, _):
        ''' Function to call update_weather from timer '''
        self.logger.info('Calling update_weather function from timer')
        self.update_weather()

    def update_weather(self, silent=True):
        ''' Update the weather '''
        self.logger.info(f'Updating weather ~ silent = {silent}')

        location = self.config['location']

        if self.config['live_location']:
            self.logger.info('Trying to load local config')
            try:
                local_config = self.local_config()
            except:
                pass
            self.logger.info('Changing ClimaCell location to local')
            self.climacell.set_location(local_config['latitude'],
                                        local_config['longitude'])
            location = local_config['location']

        try:
            self.logger.info('Trying to get weather')
            self.weather = self.climacell.get_weather()

            self.logger.info(f'Obtained weather at {location}')
            self.temp = int(round(self.weather['temp']['value'], 0))
            self.update_time()
            self.update_title()
        except APIKeyError:
            self.logger.error('API Key is not valid')
            rumps.alert(title='ClimaCell API Key is not valid',
                        message='Please make sure it is correct.')
            if not self.set_apikey():
                self.handle_missing_apikey()
            self.update_weather()
        except LocationNotFoundError:
            self.logger.error(
                'LocationNotFoundError: Could not load local config')
            rumps.alert(title='Location data not found',
                        message='Please enter another location.')
            self.prefs()
        except requests.ConnectionError:
            self.logger.error('ConnectionError: Could not get weather')
            self.handle_connection_error(silent=silent, change_icon=not silent)

    def update_title(self):
        ''' Update the app title in the menu bar'''
        self.logger.info('Updating title')
        self.icon = None
        emoji = get_icon(self.weather['weather_code']['value'])
        temp = int(round(self.temp, 0))
        self.title = f'{emoji} {temp}°'

    def update_time(self, time=None):
        ''' Update the last updated time in the app menu '''
        self.logger.info('Updating time')

        if time:
            self.logger.info('Using time from param')
            self.menu_items['last_updated_menu'].title = time
            return

        now = datetime.datetime.now()
        formatted = now.strftime("%b %d %H:%M:%S")
        self.menu_items['last_updated_menu'].title = formatted

    def update_display_units(self):
        ''' Update the units displayed in the app menu '''
        self.logger.info('Updating display units')
        if self.config['unit_system'] == 'si':
            self.logger.info('Updating to metric units')
            self.menu_items['display_units'].title = 'Metric Units (C)'
        else:
            self.logger.info('Updating to imperial units')
            self.menu_items['display_units'].title = 'Imperial Units (F)'

    def change_units(self, _):
        ''' Toggle between metric and imperial units '''
        self.logger.info('Changing units')
        self.logger.debug(self.temp)
        if self.config['unit_system'] == 'si':
            self.logger.info('Changing to imperial units')
            self.config['unit_system'] = 'us'
            self.temp = to_fahrenheit(self.temp)
        else:
            self.logger.info('Changing to metric units')
            self.config['unit_system'] = 'si'
            self.temp = to_celsius(self.temp)

        self.logger.info('Changing climacell unit system')
        self.climacell.set_unit_system(self.config['unit_system'])

        if not self.icon:  # No network alert
            self.update_title()

        self.update_display_units()
        CONFIG.save(self.config)

    def settings(self, _):
        ''' Open the settings window '''
        self.logger.info(
            'Calling prefs from settings (Change Location button)')
        self.prefs()

    def live_location(self, _):
        self.logger.info('Changing live location value in config')
        self.config['live_location'] = not self.config['live_location']

        self.logger.info('Changing state of live location button')
        self.menu_items['live_location'].state = self.config['live_location']

        if self.config['live_location']:
            self.config['live_location'] = True
            self.menu_items['change_location'].set_callback(None)
        else:
            self.config['live_location'] = False
            self.menu_items['change_location'].set_callback(self.settings)

            self.logger.info('Reverting climacell location to config')
            self.climacell.set_location(self.config['latitude'],
                                        self.config['longitude'])

        CONFIG.save(self.config)

        self.update_weather()

    def prefs(self, current_location=None):
        ''' Settings window '''
        self.logger.info('Opened settings window')

        if not current_location:
            self.logger.info('Using config location as placeholder')
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
            self.logger.info('Cancelled settings window')
            return

        # Use current location
        if response.clicked == 2:
            self.logger.info('Clicked \'Use current location\'')
            try:
                self.logger.info('Trying to load local config')
                local_config = self.local_config()

            except LocationNotFoundError:
                self.logger.error(
                    'LocationNotFoundError: Could not load local config')
                rumps.alert(title='Location not found',
                            message='Could not obtain your current location')
                self.prefs(current_location)
                return
            except requests.ConnectionError:
                self.logger.error(
                    'ConnectionError: Could not load local config')
                self.handle_connection_error()
                self.prefs(current_location)
                return
            except:
                self.logger.exception(
                    'Something went wrong whilst loading local config')
                rumps.alert(title='Something went wrong',
                            message='Quitting application')
                rumps.quit_application()

            if not self.confirm_location(local_config['location']):
                self.prefs(local_config['location'])
                return

            self.config = local_config
            self.climacell.set_location(self.config['latitude'],
                                        self.config['longitude'])
            location = self.config['location']
            self.logger.info(f'Successfully changed location to {location}')

            CONFIG.save(self.config)

            rumps.alert(
                title='Success!',
                message=f'Your location has been changed to {location}.')

            self.update_weather()
            return

        if not response.text:
            self.logger.info('Empty location input')
            rumps.alert(title='Location cannot be empty', message='Try again')
            self.prefs(current_location)
            return

        location = response.text

        try:
            self.logger.info(f'Trying to geocode \'{location}\'')
            geolocation = GEOCODER.geocode(location)
        except geopy.exc.GeocoderServiceError:
            self.logger.error(
                f'GeocoderServiceError: Could not geocode \'{location}\'')
            self.handle_connection_error()
            self.prefs(current_location)
            return
        except:
            self.logger.exception('Something went wrong with geopy')
            rumps.alert(title='Soemthing went wrong with geopy',
                        message='Quitting application')
            rumps.quit_application()

        if geolocation is None:
            self.logger.info('Location not found')
            rumps.alert(title='Could not find your location',
                        message='Try again')
            self.prefs(location)
            return

        if not self.confirm_location(geolocation):
            self.prefs(geolocation)
            return

        latitude = geolocation.latitude
        longitude = geolocation.longitude

        self.logger.info('Updating config')
        self.config = modify_location(self.config, location, latitude,
                                      longitude)

        CONFIG.save(self.config)

        self.logger.info('Updating ClimaCell location')
        self.climacell.set_location(latitude, longitude)

        self.logger.info(f'Successfully changed location to {location}')
        rumps.alert(title='Success!',
                    message=f'Your location has been changed to {location}.')

        self.update_weather()

    def local_config(self):
        '''
        Return a version of the current config where the location values are
        set to the current location of the user
        '''
        self.logger.info('Obtaining location from IP-API')
        location = get_location()

        try:
            self.logger.info('Trying to validate location as geopy location')
            is_valid = valid_geopy_location(location['lat'], location['lon'])
        except geopy.exc.GeocoderServiceError:
            raise requests.ConnectionError()

        if not is_valid:
            self.logger.error('Location is not a valid geopy location')
            raise LocationNotFoundError

        return modify_location(self.config, location['location'],
                               location['lat'], location['lon'])

    def confirm_location(self, location):
        '''
        Create an alert window to ask if the location is correct.
        If incorrect, open the settings window.
        '''
        self.logger.info('Opened location confirmation window')
        is_correct = rumps.alert(title='Is this your location?',
                                 message=location,
                                 ok='Yes',
                                 cancel='No')
        self.logger.info(
            f'Location is {"correct" if is_correct else "incorrect"}')
        return is_correct

    def handle_connection_error(self, silent=False, change_icon=False):
        ''' Handle connection error '''

        if silent:  # Do nothing
            self.logger.info('Handling connection error silently')
            return

        if change_icon:
            self.logger.info('Changing icon and time')
            self.icon = 'menubar_alert_icon.ico'
            self.update_time('No Connection')

        self.logger.info('Sending connection error alert')
        rumps.alert(title='Unable to get weather data',
                    message='Please check your internet connection.')

    def about(self, _):
        ''' Send alert window displaying application information '''
        self.logger.info('Opening \'About\' window')
        rumps.alert(
            title='About',
            message=(
                'Developed by Wai Lam Fergus Yip.\n'
                'Weather information provided by ClimaCell API\n'
                'Geocoding provided by GeoPy Contributors and IP-API\n'
                'Icon by Catalin Fertu, reused under the CC BY License.\n\n'
                'https://github.com/FergusYip/WeatherBarApp'))

    def logger_init(self):
        ''' Initialise logger '''
        logger = logging.getLogger('WeatherBar')
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')

        steam_handler = logging.StreamHandler()
        steam_handler.setFormatter(formatter)
        logger.addHandler(steam_handler)

        filename = 'WeatherBar.log'
        filepath = os.path.join(APP_SUPPORT_DIR, filename)

        file_handler = logging.FileHandler(filepath, mode='w')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger


def to_fahrenheit(celsius):
    ''' Convert celsius to fahrenheit '''
    return 9.0 / 5.0 * celsius + 32


def to_celsius(fahrenheit):
    ''' Convert fahrenheit to celsius '''
    return (fahrenheit - 32) * 5.0 / 9.0


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
