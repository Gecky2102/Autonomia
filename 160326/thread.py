from gpiozero import LED, Button
from signal import pause
import threading
import time

class SOSController:
	
	def __init__(self, pin_giallo=17, pin_rosso=27, btn_giallo=22, btn_rosso=23):
		
		self.giallo = LED(pin_giallo)
		self.rosso = LED(pin_rosso)

		# bounce_time evita che il pulsante venga letto più volte per un singolo click
		self.pulsante_giallo = Button(btn_giallo, pull_up=True, bounce_time=0.05)
		self.pulsante_rosso = Button(btn_rosso, pull_up=True, bounce_time=0.05)

		self.thread_sos = None

		# l'evento è la "bandierina" che usiamo per comunicare col thread
		self.stop_event = threading.Event()

		# colleghiamo i pulsanti fisici alle funzioni start e stop
		self.pulsante_giallo.when_pressed = self.start
		self.pulsante_rosso.when_pressed = self.stop

	def _sleep_interrompibile(self, secondi):
		# wait si comporta come sleep, ma si sveglia subito se stop_event viene alzato
		# così non dobbiamo aspettare la fine del timeout per fermare il thread
		self.stop_event.wait(timeout=secondi)

	def _sos_loop(self):
		print("")
		print("SOS - AIUTO!!!")

		while not self.stop_event.is_set():
			
			# S: tre lampi corti (1s acceso, 1s spento) ---
			for _ in range(3):
				if self.stop_event.is_set(): break
				self.rosso.on()
				self._sleep_interrompibile(1)
				self.rosso.off()
				self._sleep_interrompibile(1)

			# O: tre lampi lunghi (2s acceso, 1s spento) ---
			for _ in range(3):
				if self.stop_event.is_set(): break
				self.rosso.on()
				self._sleep_interrompibile(2)
				self.rosso.off()
				self._sleep_interrompibile(1)

			# S: altri tre lampi corti, identici al primo gruppo ---
			for _ in range(3):
				if self.stop_event.is_set(): break
				self.rosso.on()
				self._sleep_interrompibile(1)
				self.rosso.off()
				self._sleep_interrompibile(1)

		# quando il loop finisce ci assicuriamo che il led sia spento
		self.rosso.off()
		print("")
		print("Loop SOS terminato")

	def start(self):
		# se il thread è già in esecuzione non ne avviamo un secondo
		if not self.stop_event.is_set() and self.thread_sos and self.thread_sos.is_alive():
			return

		# resettiamo l'evento prima di ripartire, altrimenti il thread si fermerebbe subito
		self.stop_event.clear()

		# daemon=True fa sì che il thread muoia automaticamente se il programma principale si chiude
		self.thread_sos = threading.Thread(target=self._sos_loop, daemon=True)
		self.thread_sos.start()
		print("Thread SOS avviato")

	def stop(self):
		if not self.thread_sos or not self.thread_sos.is_alive():
			return

		# set() alza la bandierina — il thread se ne accorge al prossimo controllo
		self.stop_event.set()
		# join aspetta che il thread abbia davvero finito prima di andare avanti
		self.thread_sos.join()
		print("Thread fermato")

controller = SOSController()
pause()
