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
		self.stop_event = threading.Event() 

		self.pulsante_giallo.when_pressed = self.start
		self.pulsante_rosso.when_pressed = self.stop

	def _sleep_interrompibile(self, secondi):
		
		self.stop_event.wait(timeout=secondi)

	def _sos_loop(self):
		print("")
		print("SOS - AIUTO!!!")
		while not self.stop_event.is_set():
			
			for _ in range(3):
				if self.stop_event.is_set(): break
				self.rosso.on()
				self._sleep_interrompibile(1)
				self.rosso.off()
				self._sleep_interrompibile(1)

			for _ in range(3):
				if self.stop_event.is_set(): break
				self.rosso.on()
				self._sleep_interrompibile(2)
				self.rosso.off()
				self._sleep_interrompibile(1)

			for _ in range(3):
				if self.stop_event.is_set(): break
				self.rosso.on()
				self._sleep_interrompibile(1)
				self.rosso.off()
				self._sleep_interrompibile(1)

		self.rosso.off()
		print("")  
		print("Loop SOS terminato")

	def start(self):
		if not self.stop_event.is_set() and self.thread_sos and self.thread_sos.is_alive():
			return  
		self.stop_event.clear()  
		self.thread_sos = threading.Thread(target=self._sos_loop, daemon=True)
		self.thread_sos.start()
		print("Thread SOS avviato")

	def stop(self):
		if not self.thread_sos or not self.thread_sos.is_alive():
			return
		self.stop_event.set()  
		self.thread_sos.join() 
		print("Thread fermato")

controller = SOSController()
pause()
