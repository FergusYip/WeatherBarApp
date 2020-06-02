# WeatherBar

WeatherBar is a Python 3 app for Mac that displays the current weather and temperature in the menu bar. It utilises the ClimaCell weather API to get weather information and supports both metric and imperial unit systems.

<div align="center">
  <table>
    <tr>
      <td>
        <img
          src="https://raw.githubusercontent.com/FergusYip/WeatherBarApp/master/images/sunny.png"
          width="400"
        />
        <br />
        <img
          src="https://raw.githubusercontent.com/FergusYip/WeatherBarApp/master/images/celsius.png"
          width="400"
        />
      </td>
      <td>
        <img
          src="https://raw.githubusercontent.com/FergusYip/WeatherBarApp/master/images/rain.png"
          width="400"
        />
        <br />
        <img
          src="https://raw.githubusercontent.com/FergusYip/WeatherBarApp/master/images/fahrenheit.png"
          width="400"
        />
      </td>
    </tr>
  </table>
</div>

# Running the app

## Precompiled

Download the latest precompiled version of the app - [here](https://github.com/FergusYip/DrinkMoreApp/releases)

## Compile it yourself

Install requirements

`pip3 install -r requirements.txt`

Build app

`python setup.py py2app`

The compiled app will be found in the `dist` folder

## Run without compiling

Install requirements

`pip3 install -r requirements.txt`

Run the app

`python3 app.py`

Note that the settings window will not display the app icon as it is the python interpreter that is running the application.

# Service Dependencies

[ClimaCellAPI](https://www.climacell.co/) for Weather Data

[ip-api](https://ip-api.com/) for IP Geolocation data

# Package Dependencies

[rumps](https://pypi.org/project/rumps/) by Jared Suttles and Dan Palmer

[py2app](https://pypi.org/project/py2app/) by Bob Ippolito and Ronald Oussoren

[geopy](https://pypi.org/project/geopy/) by GeoPy Contributors

# Credits

Developed by Fergus Yip, 2020

[Sun, day, weather, symbol Free Icon](https://icon-icons.com/icon/droplet-of-water/83794) by [Catalin Fertu](http://catalinfertu.com/), reused under the [CC BY License](https://creativecommons.org/licenses/by/4.0/). Modifications to the color and the addition of an outline and drop shadow have been made.
