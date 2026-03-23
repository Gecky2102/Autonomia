from gpiozero import LED, Button
from signal import pause
import threading
import time

class SOSController:
	
	def __init__(self, pin_giallo=17, pin_rosso=27, btn_giallo=22, btn_rosso=23):
		
		self.giallo = LED(pin_giallo)
		
		self.rosso = LED(pin_rosso)
		self.pulsante_giallo = Button(btn_giallo, pull_up=True, bounce_time=0.05)
		self.pulsante_rosso = Button(btn_rosso, pull_up=True, bounce_time=0.05)

		self.thread_sos = None
		self.sos_attivo = False

		
		self.pulsante_giallo.when_pressed = self.start
		self.pulsante_rosso.when_pressed = self.stop

	def _sos_loop(self):
		print("SOS - AIUTO!!!")
		while self.sos_attivo:
			for i in range(3):
				if not self.sos_attivo:
					break
				self.rosso.on()
				time.sleep(1)
				self.rosso.off()
				time.sleep(1)
			for i in range(3):
				if not self.sos_attivo:
					break
				self.rosso.on()
				time.sleep(2)
				self.rosso.off()
				time.sleep(1)
			for i in range(3):
				if not self.sos_attivo:
					break
				self.rosso.on()
				time.sleep(1)
				self.rosso.off()
				time.sleep(1)

	def start(self):
		if self.sos_attivo:
			return
		self.sos_attivo = True
		self.thread_sos = threading.Thread(target=self._sos_loop, daemon=True)
		self.thread_sos.start()
		print("Thread sos avviato")

	def stop(self):
		if not self.sos_attivo:
			return
		self.sos_attivo = False
		print("Thread fermato")

controller = SOSController()
pause()