<p align="center">
  <img src="docs/logo.png" width="110" alt="Logo Trascrittore">
</p>

<h1 align="center">Trascrittore</h1>

<p align="center">
  Registra e trascrive audio in italiano <b>direttamente sul tuo PC</b>: gratis, privato, senza internet.<br>
  Creato da <b>Error404.ntf</b>
</p>

---

## Cos'è

Un'applicazione Windows semplicissima per trasformare in testo le registrazioni delle lezioni (o qualsiasi audio).
Usa [Whisper](https://github.com/openai/whisper) tramite [faster-whisper](https://github.com/SYSTRAN/faster-whisper):
a differenza della dettatura di Word lavora sul file intero, quindi **non salta pezzi**.

- **● Registra / ■ Stop**: registra dal microfono, con indicatore del volume
- **Trascrivi un file…**: mp3, m4a, wav, ogg, flac, video…
- **Interrompi** e **Salva parziale**: per fermarsi o salvare a metà senza perdere il lavoro
- Testo salvato in automatico come `.txt` accanto all'audio
- Barra di avanzamento con percentuale e tempo rimanente
- Usa da sola la **scheda video NVIDIA** se c'è (molto più veloce), altrimenti il processore
- **Modalità veloce** per i PC meno potenti

## Installazione

### Con il setup (consigliato)
1. Scarica `Trascrittore-Setup.exe` (vedi sotto come crearlo).
2. Doppio clic → *Avanti* → *Installa*. Installa da solo Python e i componenti (serve internet, qualche minuto).
3. Avvia **Trascrittore** dal desktop o dal menu Start.

Le registrazioni e le trascrizioni vanno in `Documenti\Trascrittore`.
Si disinstalla da *Impostazioni → App*, come un programma normale.

### Versione portatile
1. Copia la cartella `app` dove vuoi.
2. Doppio clic su `INSTALLA.bat` (una volta sola).
3. Avvia dall'icona **Trascrittore** sul desktop.

## Creare il setup

Serve [Inno Setup](https://jrsoftware.org/isdl.php) (gratis):
apri `installer/Trascrittore.iss` e premi **Compile**.
Il file `Trascrittore-Setup.exe` compare in `installer/Output`.

## Struttura

```
app/          il programma (trascrittore.py), icone e script di installazione
installer/    script di Inno Setup per creare Trascrittore-Setup.exe
docs/         immagini per questa pagina
```

## Note

- Al primo utilizzo scarica il modello scelto (`large-v3-turbo` ≈ 1,6 GB) nella cartella `modelli`.
- In caso di problemi, l'errore completo è in `errori.txt` nella cartella del programma.

---

<p align="center"><sub>Trascrittore v1.0 · creato da Error404.ntf</sub></p>
