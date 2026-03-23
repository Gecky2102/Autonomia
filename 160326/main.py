from gpiozero import LED, Button
from signal import pause

giallo = LED(17)
rosso = LED(27)
pulsante_giallo = Button(22, pull_up=True)
pulsate_rosso = Button(23, pull_up=True)


giallo.on()
# pulsante_giallo.when_pressed = giallo.on
# pulsante_giallo.when_released =  giallo.off


# pulsate_rosso.when_pressed = rosso.toggle

pause()