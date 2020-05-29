''' DrinkMore is a MacOS menu bar app to remind you to drink more water '''

import datetime
import json
import os
import webbrowser
import ssl

import rumps
import requests
from geopy.geocoders import Nominatim

ssl._create_default_https_context = ssl._create_unverified_context

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

        self.config_filename = 'config.json'
        self.default_config = {
            'location': '175 5th Avenue NYC',
            'latitude': 40.7410861,
            'longitude': -73.9896297241625,
            'unit_system': 'si',
            'apikey': ''
        }
        self.config = self.read_config()

        if not self.config['apikey']:
            print('ERROR: API Key is missing')
            self.handle_missing_apikey()

        self.weather = None

        self.temp = None

        rumps.Timer(self.update_weather_timer, 300).start()

    def handle_missing_apikey(self):
        ''' Open window to alert user of missing api key '''

        print('Opening \'API Key is required\' window')

        get_apikey = 'https://developer.climacell.co/sign-up'

        response = rumps.alert(
            title='ClimaCell API Key is required',
            message=(
                'Click \"Register\" or go to the following url:\n'
                f'{get_apikey}\n\n'
                'Note: This application is not affiliated with ClimaCell'),
            ok='Register',
            cancel='Quit',
            other='I have one')

        if response == 0:  # Quit
            rumps.quit_application()

        if response == 1:  # Register
            webbrowser.open(get_apikey)

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

        if not response.text:
            print('ERROR: API Key is not entered')
            rumps.alert(title='You did not enter an API Key',
                        message='Try again')
            return self.set_apikey()

        self.config['apikey'] = response.text

        self.save_config()

        return True

    def update_weather_timer(self, _):
        ''' Function to call update_weather from timer '''
        self.update_weather()

    def update_weather(self):
        ''' Update the weather '''
        print('Updating weather')

        url = 'https://api.climacell.co/v3/weather/realtime'
        querystring = {
            'lat': self.config['latitude'],
            'lon': self.config['longitude'],
            'unit_system': self.config['unit_system'],
            'apikey': self.config['apikey'],
            'fields': ['temp', 'weather_code']
        }
        response = requests.get(url, params=querystring)
        try:
            response.raise_for_status()
            weather_info = response.json()
            self.weather = weather_info
            self.temp = int(self.weather['temp']['value'])
            self.update_time()
            self.update_title()
            self.update_display_units()
        except requests.HTTPError:
            status_code = response.status_code
            if status_code == 403:
                print('ERROR: API Key is not valid')
                rumps.alert(title='ClimaCell API Key is not valid',
                            message='Please make sure it is correct.')
                if not self.set_apikey():
                    self.handle_missing_apikey()
                self.update_weather()
                return
            elif status_code == 404:
                print('ERROR: Data for this location is not found')
                rumps.alert(title='Location data not found',
                            message='Please enter another location.')
                self.prefs()

    def update_title(self):
        ''' Update the app title in the menu bar'''
        emoji = get_icon(self.weather['weather_code']['value'])
        temp = int(self.temp)
        self.title = f'{emoji} {temp}°'

    def update_time(self):
        ''' Update the last updated time in the app menu '''
        now = datetime.datetime.now()
        formatted = now.strftime("%b %d %H:%M:%S")
        self.last_updated_menu.title = formatted

    def update_display_units(self):
        ''' Update the units displayed in the app menu '''
        if self.config['unit_system'] == 'si':
            self.display_units.title = 'Metric Units (C)'
        else:
            self.display_units.title = 'Imperial Units (F)'

    def change_units(self, _):
        ''' Toggle between metric and imperial units '''
        if self.config['unit_system'] == 'si':
            self.config['unit_system'] = 'us'
            self.temp = to_fahrenheit(self.temp)
        else:
            self.config['unit_system'] = 'si'
            self.temp = to_celsius(self.temp)

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
            message='Right click to paste',
            title='Enter your location:',
            default_text=f'{current_location}',
            ok='Apply',
            cancel='Cancel',
            dimensions=(250, 20),
        )
        response = settings_window.run()

        if response.clicked != 1:
            return

        if not response.text:
            print('ERROR: Empty location input')
            rumps.alert(title='Location cannot be empty', message='Try again')
            self.prefs()
            return

        location = response.text

        geolocation = Nominatim(user_agent='WeatherBar').geocode(location)

        if geolocation is None:
            print('ERROR: Location not found')
            rumps.alert(title='Could not find your location',
                        message='Try again')
            self.prefs()
            return

        is_correct = rumps.alert(title='Is this your location?',
                                 message=geolocation,
                                 ok='Yes',
                                 cancel='No')

        if not is_correct:
            self.prefs(location)
            return

        self.config['location'] = location
        self.config['latitude'] = geolocation.latitude
        self.config['longitude'] = geolocation.longitude

        print(f'Successfully changed location to {location}')

        self.save_config()

        rumps.alert(title='Success!',
                    message=f'Your location has been changed to {location}.')

        self.update_weather()

    def save_config(self):
        ''' Save the config to a JSON file in the application support folder '''
        filename = self.config_filename
        filepath = os.path.join(rumps.application_support(self.name), filename)
        with open(filepath, mode='w') as config_file:
            print('Saving config')
            json.dump(self.config, config_file)

    def read_config(self):
        ''' Load the config to a JSON file in the application support folder '''
        filename = self.config_filename
        filepath = os.path.join(rumps.application_support(self.name), filename)
        try:
            with open(filepath, mode='r') as config_file:
                print('Loading USER config')
                config = json.load(config_file)

                if dict_types(config) != dict_types(self.default_config):
                    rumps.alert(title='Error when loading config',
                                message='Default settings have been applied')
                    return self.default_config

                return config
        except:
            print('Loading DEFAULT config')
            return self.default_config

    @rumps.clicked('About')
    def about(self, _):
        ''' Send alert window displaying application information '''
        rumps.alert(
            title='About',
            message=(
                'Developed by Wai Lam Fergus Yip.\n'
                'Weather information provided by ClimaCell API\n'
                'Geocoding provided by GeoPy Contributors\n'
                'Icon by Catalin Fertu, reused under the CC BY License.\n\n'
                'https://github.com/FergusYip/WeatherBarApp'))


def to_fahrenheit(celsius):
    ''' Convert celsius to fahrenheit '''
    return 9.0 / 5.0 * celsius + 32


def to_celsius(fahrenheit):
    ''' Convert fahrenheit to celsius '''
    return (fahrenheit - 32) * 5.0 / 9.0


def dict_types(dictionary):
    ''' Return a new dictionary where the values are changed to their types '''
    type_dict = {}

    for key, value in dictionary.items():
        type_dict[key] = type(value)

    return type_dict


if __name__ == '__main__':
    WeatherBarApp().run()
