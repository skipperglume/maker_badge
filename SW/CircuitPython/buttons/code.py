import time
import board
import touchio


# Maker Badge touch buttons used in project examples:
# BTN1->D5, BTN2->D4, BTN3->D3, BTN4->D2, BTN5->D1
BUTTON_PINS = [board.D5, board.D4, board.D3, board.D2, board.D1]
BUTTON_NAMES = ["BTN1", "BTN2", "BTN3", "BTN4", "BTN5"]
POLL_DELAY_S = 0.03


def read_pressed_state(buttons):
	"""Return a tuple of booleans for current touch state."""
	return tuple(btn.value for btn in buttons)


def state_to_value(state):
	"""Convert pressed tuple into a 5-bit integer value."""
	value = 0
	for index, pressed in enumerate(state):
		if pressed:
			value |= 1 << index
	return value


def state_to_names(state):
	"""Return pressed button names in physical order."""
	names = []
	for index, pressed in enumerate(state):
		if pressed:
			names.append(BUTTON_NAMES[index])
	return names


def main():
	buttons = [touchio.TouchIn(pin) for pin in BUTTON_PINS]

	print("Maker Badge button logger started")
	print("Press touch pads individually or together.")
	print("Output format: names | binary mask | decimal value")
	print("Example: BTN1+BTN3 | 0b00101 | 5")

	previous_state = read_pressed_state(buttons)

	# If anything is touched at startup, print it once.
	if any(previous_state):
		value = state_to_value(previous_state)
		names = "+".join(state_to_names(previous_state))
		print("{} | 0b{:05b} | {}".format(names, value, value))

	while True:
		current_state = read_pressed_state(buttons)

		# Edge-triggered print: only when the combination changes.
		if current_state != previous_state:
			value = state_to_value(current_state)
			if value == 0:
				print("NONE | 0b00000 | 0")
			else:
				names = "+".join(state_to_names(current_state))
				print("{} | 0b{:05b} | {}".format(names, value, value))

			previous_state = current_state

		time.sleep(POLL_DELAY_S)


main()
