<p align="center">
  <img src="docs/logo.png" width="110" alt="Logo Trascrittore">
</p>

<h1 align="center">Trascrittore</h1>

<p align="center">
  Registra e trascrive audio in italiano <b>direttamente sul tuo PC</b>: gratis, privato, senza internet.<br>
  Creato da <b>Error404.ntf</b>
</p>

<p align="center">
  <a href="https://github.com/Error404n0tf0und/trascrittore/releases/latest/download/Trascrittore-Setup.exe"><img src="https://img.shields.io/badge/Scarica-Trascrittore--Setup.exe-5B4FE0?style=for-the-badge&logo=windows&logoColor=white" alt="Scarica Trascrittore-Setup.exe"></a>
  <br><sub>Windows 10/11 · <a href="https://github.com/Error404n0tf0und/trascrittore/releases/latest">note della versione</a></sub>
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
1. Scarica [`Trascrittore-Setup.exe`](https://github.com/Error404n0tf0und/trascrittore/releases/latest/download/Trascrittore-Setup.exe) dall'ultima release.
2. Doppio clic → *Avanti* → *Installa*. Installa da solo Python e i componenti (serve internet, qualche minuto).
3. Avvia **Trascrittore** dal desktop o dal menu Start.

Se Windows mostra *"Windows ha protetto il PC"*: **Ulteriori informazioni → Esegui comunque**
(succede con i programmi senza firma digitale).

Le registrazioni e le trascrizioni vanno in `Documenti\Trascrittore`.
Si disinstalla da *Impostazioni → App*, come un programma normale.

### Versione portatile
1. Copia la cartella `app` dove vuoi.
2. Doppio clic su `INSTALLA.bat` (una volta sola).
3. Avvia dall'icona **Trascrittore** sul desktop.

## Come funziona

### Il percorso dell'audio

```
 microfono ─┐
            ├─► audio 16 kHz mono ─► filtro silenzi ─► Whisper ─► testo a pezzi ─► finestra + file .txt
 file audio ┘     (lettura)            (VAD)          (modello)
```

1. **Acquisizione**
   - *Registrazione*: il microfono viene letto a 16 kHz mono e l'audio viene **scritto su disco mentre registri**,
     a blocchi, in un file `.wav`. Anche una lezione di 3 ore non riempie la memoria, e se il PC si blocca
     la parte già registrata resta salvata.
   - *File esistente*: i `.wav` del programma vengono letti direttamente; tutti gli altri formati (mp3, m4a,
     video…) vengono decodificati con [PyAV](https://github.com/PyAV-Org/PyAV) e convertiti nello stesso formato.
2. **Filtro dei silenzi (VAD)**: un piccolo modello riconosce dove qualcuno sta parlando e salta pause e silenzi.
   La soglia è abbassata rispetto al normale, così non perde il parlato a basso volume (es. il professore lontano dal microfono).
3. **Trascrizione**: [Whisper](https://github.com/openai/whisper), il modello di riconoscimento vocale di OpenAI,
   eseguito con [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (motore CTranslate2), molto più rapido dell'originale.
   Lavora a finestre di circa 30 secondi e, a differenza della dettatura in tempo reale, ascolta ogni pezzo
   per intero prima di scriverlo: per questo non salta parti.
4. **Risultato**: ogni frase compare nella finestra appena è pronta; alla fine il testo completo viene salvato
   come `.txt` con lo stesso nome dell'audio.

### Scheda video o processore

All'avvio il programma controlla se c'è una **scheda video NVIDIA** utilizzabile:

| | Con NVIDIA | Senza NVIDIA |
|---|---|---|
| Dove gira Whisper | scheda video (`float16`) | processore (`int8`, più leggero) |
| Velocità indicativa | 1 ora di audio in pochi minuti | circa quanto la durata dell'audio, o di più |
| Modalità veloce | spenta di default | accesa di default |

Se la scheda video c'è ma qualcosa non va (librerie mancanti), il programma passa da solo al processore.

### Le impostazioni

- **Modello**: `large-v3-turbo` (predefinito, il più preciso), `medium`, `small` (più rapido, meno preciso).
  Si scarica da [Hugging Face](https://huggingface.co) solo la prima volta, nella cartella `modelli`.
- **Modalità veloce**: Whisper valuta una sola ipotesi per frase invece di 5 (*beam search* 1 invece di 5).
  Circa il doppio più rapida, con un piccolo calo di precisione.
- **Lingua**: fissata sull'italiano, così il modello non perde tempo a indovinarla e non "traduce" per errore.
- **Anti-ripetizioni**: ogni pezzo viene trascritto senza farsi condizionare dal precedente, per evitare
  che Whisper si blocchi a ripetere la stessa frase all'infinito.

### Interrompi e salva parziale

- **Salva parziale** scrive in `nome (parziale).txt` il testo prodotto fino a quel momento, senza fermare il lavoro.
- **Interrompi** ferma la trascrizione alla fine del pezzo in corso (pochi secondi) e salva comunque la parte fatta.

### Privacy

Tutto avviene sul tuo PC: l'audio e il testo **non vengono mai inviati da nessuna parte**.
L'unico uso di internet è il download dei componenti durante l'installazione e del modello al primo utilizzo.

### Installazione, dietro le quinte

Il setup (creato con [Inno Setup](https://jrsoftware.org/isinfo.php)) copia il programma nella cartella utente,
quindi non servono permessi di amministratore. Poi lancia `setup_ambiente.bat`, che:
1. trova Python o lo installa con `winget`;
2. installa `faster-whisper` e `sounddevice` con `pip`;
3. se rileva una NVIDIA (`nvidia-smi`), installa anche le librerie CUDA necessarie alla scheda video;
4. prepara l'avvio senza la finestra nera del terminale.

## Creare il setup

Serve [Inno Setup](https://jrsoftware.org/isdl.php) (gratis):
apri `installer/Trascrittore.iss` e premi **Compile**.
Il file `Trascrittore-Setup.exe` compare in `installer/Output`.

## Struttura

```
app/          il programma (trascrittore.py), icone e script di installazione
installer/    script di Inno Setup per creare Trascrittore-Setup.exe
docs/         immagini per questa pagina
LICENSE       licenza MIT
```

## Note

- Al primo utilizzo scarica il modello scelto (`large-v3-turbo` ≈ 1,6 GB) nella cartella `modelli`.
- In caso di problemi, l'errore completo è in `errori.txt` nella cartella del programma.

## Licenza

Distribuito con licenza **MIT**: puoi usarlo, copiarlo, modificarlo e ridistribuirlo liberamente,
anche per scopi commerciali, purché mantieni la nota di copyright di Error404.ntf. Testo completo in [LICENSE](LICENSE).

Si basa su progetti open source con le loro licenze, tra cui
[Whisper](https://github.com/openai/whisper) (MIT), [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT),
[PyAV](https://github.com/PyAV-Org/PyAV) e [sounddevice](https://github.com/spatialaudio/python-sounddevice).

---

<p align="center"><sub>Trascrittore v1.0 · creato da Error404.ntf · licenza MIT</sub></p>
