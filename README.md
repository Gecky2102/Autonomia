# Autonomia

Repository con esercizi/progetti Python per laboratorio su Raspberry Pi e socket TCP.

## Cartelle

- `090326/` esercizi iniziali GPIO
- `160326/` threading + esempio SOS interrompibile
- `130426/` client/server TCP con protocollo binario a 1 byte per controllo LED e giochi di luce

## Test

La suite di test attuale e' nel modulo `130426`.

Da root:

```bash
python3 -m unittest discover -s 130426/tests -v
```
