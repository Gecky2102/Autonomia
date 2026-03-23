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
		self.stop_event = threading.Event()  # ← aggiunto

		self.pulsante_giallo.when_pressed = self.start
		self.pulsante_rosso.when_pressed = self.stop

	def _sleep_interrompibile(self, secondi):
		"""Aspetta X secondi, ma si ferma subito se arriva lo stop."""
		self.stop_event.wait(timeout=secondi)

	def _sos_loop(self):
		print("SOS - AIUTO!!!")
		while not self.stop_event.is_set():
			# Tre lampi corti (S)
			for _ in range(3):
				if self.stop_event.is_set(): break
				self.rosso.on()
				self._sleep_interrompibile(1)
				self.rosso.off()
				self._sleep_interrompibile(1)

			# Tre lampi lunghi (O)
			for _ in range(3):
				if self.stop_event.is_set(): break
				self.rosso.on()
				self._sleep_interrompibile(2)
				self.rosso.off()
				self._sleep_interrompibile(1)

			# Tre lampi corti (S)
			for _ in range(3):
				if self.stop_event.is_set(): break
				self.rosso.on()
				self._sleep_interrompibile(1)
				self.rosso.off()
				self._sleep_interrompibile(1)

		self.rosso.off()  # Assicura che il LED si spenga
		print("Loop SOS terminato")

	def start(self):
		if not self.stop_event.is_set() and self.thread_sos and self.thread_sos.is_alive():
			return  # Già in esecuzione
		self.stop_event.clear()  # Resetta l'evento
		self.thread_sos = threading.Thread(target=self._sos_loop, daemon=True)
		self.thread_sos.start()
		print("Thread SOS avviato")

	def stop(self):
		if not self.thread_sos or not self.thread_sos.is_alive():
			return
		self.stop_event.set()  # ← manda il segnale di stop
		self.thread_sos.join() # ← aspetta che il thread finisca davvero
		print("Thread fermato")

controller = SOSController()
pause()
