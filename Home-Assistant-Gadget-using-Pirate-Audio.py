from PIL import Image, ImageDraw, ImageFont
from ST7789 import ST7789
import os
import RPi.GPIO as GPIO
import time
#from flask import Flask, jsonify, make_response
from requests import get


#Set up screen
SPI_SPEED_MHZ = 80
screen = ST7789(
    rotation=90,  # Needed to display the right way up on Pirate Audio
    port=0,       # SPI port
    cs=1,         # SPI port Chip-select channel
    dc=9,         # BCM pin used for data/command
    backlight=13,
    spi_speed_hz=SPI_SPEED_MHZ * 1000 * 1000
)
# screen size details
width = screen.width
height = screen.height

# Create a few blank images.
image = [None] * 4
draw = [None] * 4
for i in range(4):
	image[i] = Image.new("RGB", (240, 240), (0, 0, 0))
	draw[i] = ImageDraw.Draw(image[i])

# Splash Screen
image[1] = Image.open("home-assistant-logo.png")
screen.display(image[1])

def wipe_screen(screen_number):
	image[screen_number] = Image.new("RGB", (240, 240), (0, 0, 0))
	draw[screen_number] = ImageDraw.Draw(image[screen_number])

# Set up Fonts
mdifont60 = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/materialdesignicons-webfont.ttf", 45)
font30 = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/arial.ttf", 30)
font20 = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/arial.ttf", 20)


# Set up the basics for buttons. The buttons on Pirate Audio are connected to pins 5, 6, 16 and 20
BUTTONS = [5, 6, 16, 20]

# These correspond to buttons A, B, X and Y respectively
LABELS = ['A', 'B', 'X', 'Y']

# Set up RPi.GPIO with the "BCM" numbering scheme
GPIO.setmode(GPIO.BCM)

# Buttons connect to ground when pressed, so we should set them up
# with a "PULL UP", which weakly pulls the input signal to 3.3V.
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# Set up the button handler
def handle_button(pin):
	label = LABELS[BUTTONS.index(pin)]
	print("Button press detected on pin: {} label: {}".format(pin, label))

	if label=='A':
		os.system("play -v 1.5 sample-mp3-alert-sound.mp3 2>/dev/null && play -v 2.75 test-mp3-message.mp3 2>/dev/null")

	if label=='X':
		# button X - show the colour image, and pause for a second
		screen.display(image[0])
		draw_grid(2)
		screen.display(image[2])
		time.sleep(60)
		screen.display(image[3])

	if label=='B':
		# button B - show the logo image, and pause for a second
		screen.display(image[1])
		time.sleep(2)
		screen.display(image[3])

	if label=='Y':
		# button Y - show the blank image, and exit
		screen.display(image[0])
		GPIO.cleanup()
		exit()

for pin in BUTTONS:
    GPIO.add_event_detect(pin, GPIO.FALLING, handle_button, bouncetime=400)

HASS_IP = "http://xxx.xxx.xxx.xxx:8123/api/states/" # Replace xxx with your Home Assistant IP
AUTH_TOKEN = " HA Auth Token " # Replace text with Auth Token from Home Assitant, surround with quotes as per example


def get_ha_info(entity_id):
	#if entity_id[0-2] == "bin":

	url = HASS_IP + entity_id
	headers = {
    "Authorization": "Bearer " + AUTH_TOKEN,
    "content-type": "application/json",
	}

	response = get(url, headers=headers)
	ha_state = response.json()['state']
	ha_units = response.json()['attributes']['unit_of_measurement']

	if ha_state in ["unavailable", "unknown"]: ha_state = "???"
	if ha_units in ["unavailable", "unknown"]: ha_units = "???"

	singulars = ["seconds", "minutes", "hours", "times"]
	if ha_units in singulars and ha_state == "1": ha_units = ha_units[:-1]

	if ha_units == "%": ha_state = str(int(float(ha_state)))

	return(ha_state, ha_units)


def draw_sensor_panel(draw, grid_ref, entity, icon_choice, **kwargs): # **kwargs -  low_value, high_value:

	state_ha, unit_ha = get_ha_info(entity)

	threshold_colour = "limegreen" # Colour for normal value range. For colour choices see - https://drafts.csswg.org/css-color-4/#named-colors
	if kwargs and state_ha != "???":
		for key, value in kwargs.iteritems():
			if key == "low_value":
				if float(state_ha) <= value:
					threshold_colour = "cyan"
			elif key == "high_value":
				if float(state_ha) >= value:
					threshold_colour = "orangered"

	pos_x, pos_y, font = grid_position("icon", grid_ref, icon_choice)
	draw.text((pos_x, pos_y), icon_choice, font=font, fill=threshold_colour)

	pos_x, pos_y, font = grid_position("state", grid_ref, state_ha)
	draw.text((pos_x, pos_y), state_ha, font=font, fill="white")

	pos_x, pos_y, font = grid_position("units", grid_ref, unit_ha)
	draw.text((pos_x, pos_y), unit_ha, font=font, fill="white")


def grid_position(type, grid_ref, displayed_text):

	if type == "icon":
		font = mdifont60
	elif type == "state":
		font = font30
	else:
		font = font20

	size_x, size_y = font.getsize(displayed_text)

	if grid_ref in [1, 4]:
		text_x = 40 - ( size_x / 2)
	elif grid_ref in [2, 5]:
		text_x = 120 - ( size_x / 2)
	else:
		text_x = 200 - ( size_x / 2)

	if grid_ref in [1, 2, 3]:
		if type == "icon":
			text_y = 50
		elif type == "state":
			text_y = 85
		else:
			text_y = 110

	if grid_ref in [4, 5, 6]:
		if type == "icon":
			text_y = 170
		elif type == "state":
			text_y = 210
		else:
			text_y = 235

	text_y = text_y - size_y
	return(text_x, text_y, font)


def draw_grid(screen_number, line_width, colour):
	draw = ImageDraw.Draw(image[screen_number])
# Horizontal
	draw.line((5, 120, 235, 120), fill=colour, width=line_width)
# Vertical
	draw.line((80, 5, 80, 235), fill=colour, width=line_width)
	draw.line((160, 5, 160, 235), fill=colour, width=line_width)

## image 2 - SENSORS

def sensor_display():

	draw_sensor_panel(draw[2], 1, "sensor.bonsai_garage_temp", u"\uF510", low_value = 3, high_value = 23)
	draw_sensor_panel(draw[2], 2, "sensor.dark_sky_precip_probability_1h", u"\uF596", high_value = 75)
	draw_sensor_panel(draw[2], 3, "sensor.met_ie_dunsany_wind_speed_kph", u"\uF59D", high_value = 62)
	draw_sensor_panel(draw[2], 4, "sensor.co2_levels", u"\uF7E3", high_value = 600)
	draw_sensor_panel(draw[2], 5, "sensor.voc_levels", u"\uF096", high_value = 200)
	draw_sensor_panel(draw[2], 6, "sensor.kitchen_motion_detected_times", u"\uF25C")

	draw_grid(2, 3, "grey")

while True:
	sensor_display()
	screen.display(image[2])
	time.sleep(20)
	wipe_screen(2)
