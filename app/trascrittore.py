"""
Trascrittore - registra e trascrive audio in locale con Whisper.
Autore: Error404.ntf
Avvio: icona "Trascrittore" sul desktop (creata da INSTALLA.bat)
       oppure doppio clic su avvia.bat
"""
import os
import sys
import queue
import threading
import time
import wave
import datetime
import traceback
import tkinter as tk

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "errori.txt")

# Avviato con pythonw (senza finestra nera) non esiste dove scrivere:
# le barre di download dei modelli andrebbero in errore. Le mandiamo in un file.
if sys.stdout is None or sys.stderr is None:
    _log = open(LOG, "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or _log
    sys.stderr = sys.stderr or _log

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def abilita_dll_nvidia():
    """Sui PC con scheda NVIDIA, INSTALLA.bat scarica le librerie CUDA come pacchetti
    Python: qui le rendiamo visibili a Whisper, cosi' non serve installare CUDA a parte."""
    if os.name != "nt":
        return
    import site
    import glob
    cartelle = []
    radici = list(site.getsitepackages())
    try:
        radici.append(site.getusersitepackages())
    except Exception:
        pass
    for sp in radici:
        cartelle += glob.glob(os.path.join(sp, "nvidia", "*", "bin"))
    for d in cartelle:
        try:
            os.add_dll_directory(d)
        except OSError:
            pass
    if cartelle:
        os.environ["PATH"] = os.pathsep.join(cartelle) + os.pathsep + os.environ.get("PATH", "")


def gpu_disponibile():
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


abilita_dll_nvidia()
from tkinter import ttk, filedialog, messagebox

import numpy as np
import sounddevice as sd

def cartella_registrazioni():
    """Installato con Trascrittore-Setup.exe il programma sta in AppData (cartella nascosta):
    allora le registrazioni vanno in Documenti\\Trascrittore. Altrimenti accanto al programma."""
    if os.name == "nt" and "\\AppData\\" in BASE:
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)  # 5 = Documenti
            documenti = buf.value
        except Exception:
            documenti = ""
        if not documenti:
            documenti = os.path.join(os.path.expanduser("~"), "Documents")
        return os.path.join(documenti, "Trascrittore")
    return os.path.join(BASE, "registrazioni")


CARTELLA = cartella_registrazioni()
MODELLI_DIR = os.path.join(BASE, "modelli")
os.makedirs(CARTELLA, exist_ok=True)
SR = 16000  # 16 kHz mono: e' quello che usa Whisper, file piu' leggeri

AUTORE = "Error404.ntf"
VERSIONE = "1.0"

MODELLI = ["small", "medium", "large-v3-turbo"]
MODELLO_DEFAULT = "large-v3-turbo"

# ---------------- COLORI ----------------
C = {
    "sfondo": "#F4F5F9",
    "card": "#FFFFFF",
    "testo": "#1F2333",
    "grigio": "#6B7084",
    "bordo": "#E2E4EC",
    "accento": "#5B4FE0",
    "accento_h": "#4A3FCB",
    "rosso": "#E5484D",
    "rosso_h": "#CC3B40",
    "verde": "#30A46C",
    "traccia": "#E8E9F1",
    "spento": "#C9CAD6",
}
PLACEHOLDER = "La trascrizione comparirà qui, man mano che procede."


def carica_audio(path):
    """Legge un file audio e lo restituisce come 16 kHz mono float32 (formato di Whisper).
    Non usa la lettura interna di faster-whisper, che si rompe con alcune versioni di PyAV."""
    # WAV a 16 kHz mono 16 bit (quelli registrati da questo programma): lettura diretta
    try:
        with wave.open(path, "rb") as w:
            if w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2:
                dati = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
                return dati.astype(np.float32) / 32768.0
    except (wave.Error, EOFError):
        pass  # non e' un WAV semplice: lo decodifica PyAV qui sotto

    # Tutti gli altri formati (mp3, m4a, ogg, video…)
    import av
    resampler = av.AudioResampler(format="s16", layout="mono", rate=SR)
    pezzi = []

    def aggiungi(frames):
        if frames is None:
            return
        if not isinstance(frames, (list, tuple)):
            frames = [frames]
        for f in frames:
            pezzi.append(f.to_ndarray().reshape(-1))

    with av.open(path) as contenitore:
        for frame in contenitore.decode(audio=0):
            frame.pts = None
            aggiungi(resampler.resample(frame))
        aggiungi(resampler.resample(None))  # svuota il buffer finale

    if not pezzi:
        raise ValueError("Nel file non ho trovato audio.")
    return np.concatenate(pezzi).astype(np.float32) / 32768.0


class Interrotto(Exception):
    """Trascrizione fermata dall'utente."""


def durata_txt(s):
    s = int(max(0, s))
    if s >= 3600:
        return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"
    return f"{s // 60:02d}:{s % 60:02d}"


def imposta_stile(root):
    st = ttk.Style(root)
    st.theme_use("clam")
    st.configure(".", background=C["sfondo"], foreground=C["testo"], font=("Segoe UI", 10))
    st.configure("TFrame", background=C["sfondo"])
    st.configure("Card.TFrame", background=C["card"])
    st.configure("Titolo.TLabel", font=("Segoe UI Semibold", 17))
    st.configure("Sotto.TLabel", foreground=C["grigio"])
    st.configure("Badge.TLabel", background=C["traccia"], foreground=C["grigio"],
                 font=("Segoe UI", 9), padding=(10, 4))
    st.configure("Stato.TLabel", background=C["card"], font=("Segoe UI Semibold", 10))
    st.configure("Pct.TLabel", background=C["card"], foreground=C["accento"],
                 font=("Segoe UI Semibold", 11))
    st.configure("Info.TLabel", background=C["card"], foreground=C["grigio"], font=("Segoe UI", 9))

    # pulsanti pieni colorati
    for nome, col, hover in (("Rec", C["rosso"], C["rosso_h"]), ("Acc", C["accento"], C["accento_h"])):
        st.configure(f"{nome}.TButton", background=col, foreground="white", borderwidth=0,
                     bordercolor=col, lightcolor=col, darkcolor=col, focuscolor=col,
                     padding=(18, 10), font=("Segoe UI Semibold", 10))
        st.map(f"{nome}.TButton",
               background=[("disabled", C["spento"]), ("active", hover)],
               lightcolor=[("disabled", C["spento"]), ("active", hover)],
               darkcolor=[("disabled", C["spento"]), ("active", hover)],
               bordercolor=[("disabled", C["spento"]), ("active", hover)],
               foreground=[("disabled", "#F4F5F9")])
    # pulsanti secondari
    st.configure("Sec.TButton", background=C["card"], foreground=C["testo"], bordercolor=C["bordo"],
                 lightcolor=C["card"], darkcolor=C["card"], focuscolor=C["card"], padding=(12, 6))
    st.map("Sec.TButton", background=[("active", "#EEEFF5")],
           lightcolor=[("active", "#EEEFF5")], darkcolor=[("active", "#EEEFF5")])

    for nome, col in (("Barra", C["accento"]), ("Livello", C["verde"])):
        st.configure(f"{nome}.Horizontal.TProgressbar", troughcolor=C["traccia"], background=col,
                     bordercolor=C["traccia"], lightcolor=col, darkcolor=col, thickness=10)

    st.configure("TCheckbutton", background=C["sfondo"])
    st.map("TCheckbutton", background=[("active", C["sfondo"])])
    st.configure("TCombobox", padding=5, arrowsize=14)
    st.map("TCombobox", fieldbackground=[("readonly", "white")],
           selectbackground=[("readonly", "white")], selectforeground=[("readonly", C["testo"])])


class App:
    def __init__(self, root):
        self.root = root
        root.title("Trascrittore")
        root.configure(bg=C["sfondo"])
        scala = float(root.tk.call("tk", "scaling")) / (96 / 72)
        # finestra comoda ma mai piu' grande dello schermo (portatili piccoli)
        larg = min(int(880 * scala), root.winfo_screenwidth() - 40)
        alt = min(int(660 * scala), root.winfo_screenheight() - 90)
        root.geometry(f"{larg}x{alt}")
        root.minsize(min(int(640 * scala), larg), min(int(460 * scala), alt))
        self.imposta_icona()
        imposta_stile(root)

        self.ui = queue.Queue()        # messaggi dai thread verso la finestra
        self.audio_q = queue.Queue()   # blocchi audio dal microfono
        self.stream = None
        self.writer_thread = None
        self.registrando = False
        self.occupato = False
        self.modello = None
        self.nome_modello = None
        self.dev = "CPU"
        self.gpu = gpu_disponibile()
        self.livello = 0.0
        self.pct = 0.0
        self.t_inizio = None
        self.t_totale = 0.0
        self.in_attesa = False
        self.placeholder = True
        self.stop_evt = threading.Event()
        self.info_fissa_fino = 0.0

        outer = ttk.Frame(root, padding=(20, 16))
        outer.pack(fill="both", expand=True)

        # ---- intestazione ----
        head = ttk.Frame(outer)
        head.pack(fill="x")
        try:
            self.logo = tk.PhotoImage(file=os.path.join(BASE, "logo.png"))
            tk.Label(head, image=self.logo, bg=C["sfondo"]).pack(side="left", padx=(0, 12))
        except Exception:
            pass
        tit = ttk.Frame(head)
        tit.pack(side="left")
        ttk.Label(tit, text="Trascrittore", style="Titolo.TLabel").pack(anchor="w")
        ttk.Label(tit, text="Registra e trascrivi le tue lezioni, tutto sul tuo PC",
                  style="Sotto.TLabel").pack(anchor="w")
        ttk.Label(head, style="Badge.TLabel",
                  text="⚡ Scheda video NVIDIA" if self.gpu else "Processore (CPU)").pack(side="right")

        # ---- azioni ----
        az = ttk.Frame(outer)
        az.pack(fill="x", pady=(18, 12))
        self.btn_rec = ttk.Button(az, text="●  Registra", style="Rec.TButton", command=self.toggle_rec)
        self.btn_rec.pack(side="left")
        self.btn_apri = ttk.Button(az, text="Trascrivi un file…", style="Acc.TButton", command=self.apri)
        self.btn_apri.pack(side="left", padx=10)

        self.veloce = tk.BooleanVar(value=not self.gpu)
        self.chk = ttk.Checkbutton(az, text="Modalità veloce", variable=self.veloce)
        self.chk.pack(side="right")
        self.cmb = ttk.Combobox(az, values=MODELLI, width=15, state="readonly")
        self.cmb.set(MODELLO_DEFAULT)
        self.cmb.pack(side="right", padx=(6, 16))
        ttk.Label(az, text="Modello", foreground=C["grigio"]).pack(side="right")

        # ---- avanzamento ----
        card = tk.Frame(outer, bg=C["card"], highlightthickness=1, highlightbackground=C["bordo"])
        card.pack(fill="x")
        dentro = ttk.Frame(card, style="Card.TFrame", padding=(16, 12))
        dentro.pack(fill="x")
        riga = ttk.Frame(dentro, style="Card.TFrame")
        riga.pack(fill="x")
        self.stato = tk.StringVar(value="Pronto")
        self.pct_txt = tk.StringVar(value="")
        ttk.Label(riga, textvariable=self.stato, style="Stato.TLabel").pack(side="left")
        ttk.Label(riga, textvariable=self.pct_txt, style="Pct.TLabel").pack(side="right")
        self.prog = ttk.Progressbar(dentro, style="Barra.Horizontal.TProgressbar",
                                    mode="determinate", maximum=100)
        self.prog.pack(fill="x", pady=(8, 6))
        self.info = tk.StringVar(value="Premi Registra per una nuova lezione, oppure scegli un file audio.")
        ttk.Label(dentro, textvariable=self.info, style="Info.TLabel").pack(anchor="w")

        # pulsanti in basso e firma vengono fissati in fondo per primi:
        # cosi' restano sempre visibili e la casella del testo si adatta allo spazio rimasto
        # ---- autore ----
        ttk.Label(outer, text=f"Trascrittore v{VERSIONE}  ·  creato da {AUTORE}",
                  foreground="#A3A6B8", font=("Segoe UI", 8)).pack(side="bottom", anchor="e", pady=(10, 0))

        # ---- in basso ----
        bot = ttk.Frame(outer)
        bot.pack(side="bottom", fill="x", pady=(12, 0))
        ttk.Button(bot, text="Copia testo", style="Sec.TButton", command=self.copia).pack(side="left")
        ttk.Button(bot, text="Salva come…", style="Sec.TButton", command=self.salva).pack(side="left", padx=8)
        self.btn_parziale = ttk.Button(bot, text="Salva parziale", style="Sec.TButton",
                                       command=self.salva_parziale, state="disabled")
        self.btn_parziale.pack(side="left")
        ttk.Button(bot, text="Apri cartella registrazioni", style="Sec.TButton",
                   command=lambda: self.apri_cartella(CARTELLA)).pack(side="right")

        # ---- testo ----
        tcard = tk.Frame(outer, bg=C["card"], highlightthickness=1, highlightbackground=C["bordo"])
        tcard.pack(fill="both", expand=True, pady=(12, 0))
        sb = ttk.Scrollbar(tcard, orient="vertical")
        sb.pack(side="right", fill="y")
        self.testo = tk.Text(tcard, wrap="word", height=6, font=("Segoe UI", 11), bg=C["card"], fg=C["testo"],
                             relief="flat", borderwidth=0, padx=16, pady=14, spacing1=2, spacing3=6,
                             insertbackground=C["testo"], selectbackground="#D9D6FB",
                             selectforeground=C["testo"], yscrollcommand=sb.set)
        self.testo.pack(fill="both", expand=True)
        sb.config(command=self.testo.yview)
        self.testo.tag_configure("ph", foreground="#A3A6B8")
        self.mostra_placeholder()

        root.protocol("WM_DELETE_WINDOW", self.chiudi)
        root.after(100, self.pompa_ui)
        root.after(250, self.tick)

    # ---------------- ASPETTO ----------------
    def imposta_icona(self):
        try:
            if os.name == "nt":
                self.root.iconbitmap(default=os.path.join(BASE, "app.ico"))
        except Exception:
            pass
        try:
            self._icona = tk.PhotoImage(file=os.path.join(BASE, "app.png"))
            self.root.iconphoto(True, self._icona)
        except Exception:
            pass

    def mostra_placeholder(self):
        self.testo.delete("1.0", "end")
        self.testo.insert("1.0", PLACEHOLDER, "ph")
        self.placeholder = True

    def svuota_testo(self):
        self.testo.delete("1.0", "end")
        self.placeholder = False

    def barra_attesa(self, msg):
        """Barra animata: per le fasi di cui non si conosce la durata."""
        self.stato.set(msg)
        self.pct_txt.set("")
        self.prog.config(style="Barra.Horizontal.TProgressbar")
        if not self.in_attesa:
            self.prog.config(mode="indeterminate")
            self.prog.start(15)
            self.in_attesa = True

    def barra_valore(self, valore, stile="Barra.Horizontal.TProgressbar"):
        if self.in_attesa:
            self.prog.stop()
            self.prog.config(mode="determinate")
            self.in_attesa = False
        self.prog.config(style=stile)
        self.prog["value"] = valore

    def comandi(self, attivi):
        stato = "normal" if attivi else "disabled"
        self.btn_rec.config(state=stato)
        self.btn_apri.config(state=stato)
        self.chk.config(state=stato)
        self.cmb.config(state="readonly" if attivi else "disabled")

    # ---------------- REGISTRAZIONE ----------------
    def toggle_rec(self):
        if self.registrando:
            self.stop_rec()
        else:
            self.start_rec()

    def _callback_mic(self, dati, n, t, s):
        self.audio_q.put(dati.copy())
        rms = float(np.sqrt(np.mean(dati.astype(np.float32) ** 2))) / 32768.0
        db = 20 * np.log10(rms + 1e-9)          # da -60 dB (silenzio) a 0 dB (massimo)
        self.livello = max(0.0, min(100.0, (db + 60) / 60 * 100))

    def start_rec(self):
        if self.occupato:
            return
        nome = datetime.datetime.now().strftime("lezione_%Y-%m-%d_%H-%M.wav")
        self.file_rec = os.path.join(CARTELLA, nome)
        self.audio_q = queue.Queue()
        try:
            self.stream = sd.InputStream(samplerate=SR, channels=1, dtype="int16",
                                         callback=self._callback_mic)
            self.stream.start()
        except Exception as e:
            messagebox.showerror("Microfono", f"Non riesco a usare il microfono:\n{e}")
            return
        self.registrando = True
        self.t0 = time.time()
        # scrive su disco mentre registra: niente memoria piena con lezioni lunghe
        self.writer_thread = threading.Thread(target=self.scrivi_wav, daemon=True)
        self.writer_thread.start()
        self.btn_rec.config(text="■  Stop")
        self.btn_apri.config(state="disabled")
        self.cmb.config(state="disabled")
        self.chk.config(state="disabled")
        self.stato.set("● Registrazione in corso")
        self.info.set("La barra verde mostra il volume del microfono: se resta quasi vuota mentre parli, avvicinalo.")
        self.barra_valore(0, "Livello.Horizontal.TProgressbar")

    def scrivi_wav(self):
        with wave.open(self.file_rec, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            while self.registrando or not self.audio_q.empty():
                try:
                    w.writeframes(self.audio_q.get(timeout=0.5).tobytes())
                except queue.Empty:
                    pass

    def stop_rec(self, chiedi=True):
        self.stream.stop()
        self.stream.close()
        self.stream = None
        self.registrando = False
        self.writer_thread.join()
        durata = time.time() - self.t0
        self.btn_rec.config(text="●  Registra")
        self.comandi(True)
        self.barra_valore(0)
        self.pct_txt.set("")
        self.stato.set(f"Registrazione salvata ({durata_txt(durata)})")
        self.info.set(self.file_rec)
        if chiedi and messagebox.askyesno("Registrazione salvata", "La trascrivo adesso?"):
            self.trascrivi(self.file_rec)

    # ---------------- TRASCRIZIONE ----------------
    def apri(self):
        f = filedialog.askopenfilename(
            title="Scegli un file audio",
            initialdir=CARTELLA,
            filetypes=[("Audio/Video", "*.mp3 *.m4a *.wav *.ogg *.flac *.aac *.wma *.opus *.mp4 *.webm"),
                       ("Tutti i file", "*.*")],
        )
        if f:
            self.trascrivi(f)

    def trascrivi(self, path):
        if self.occupato:
            return
        self.occupato = True
        self.stop_evt.clear()
        self.comandi(False)
        self.btn_apri.config(text="■  Interrompi", style="Rec.TButton", state="normal",
                             command=self.interrompi)
        self.svuota_testo()
        self.pct = 0.0
        self.t_inizio = self.t_totale = time.time()
        self.file_corrente = os.path.basename(path)
        self.path_corrente = path
        self.btn_parziale.config(state="normal")
        self.beam = 1 if self.veloce.get() else 5
        self.barra_attesa("Preparo la trascrizione…")
        self.info.set(self.file_corrente)
        threading.Thread(target=self.lavora, args=(path, self.cmb.get()), daemon=True).start()

    def carica_modello(self, nome):
        if self.modello is not None and self.nome_modello == nome:
            return
        from faster_whisper import WhisperModel
        gia_scaricato = os.path.isdir(MODELLI_DIR) and any(nome in d for d in os.listdir(MODELLI_DIR))
        self.ui.put(("attesa", f"Carico il modello {nome}…" if gia_scaricato
                     else f"Scarico il modello {nome} (solo la prima volta, qualche minuto)…"))
        if self.gpu:
            try:
                self.modello = WhisperModel(nome, device="cuda", compute_type="float16",
                                            download_root=MODELLI_DIR)
                self.nome_modello, self.dev = nome, "GPU"
                return
            except Exception:
                pass
        self.modello = WhisperModel(nome, device="cpu", compute_type="int8", download_root=MODELLI_DIR)
        self.nome_modello, self.dev = nome, "CPU"

    def lavora(self, path, nome):
        try:
            self.carica_modello(nome)
            try:
                righe = self._trascrivi(path)
            except Interrotto:
                raise
            except Exception:
                if self.dev != "GPU":
                    raise
                # GPU presente ma librerie CUDA mancanti: ripiega sulla CPU
                from faster_whisper import WhisperModel
                self.ui.put(("pulisci", None))
                self.ui.put(("attesa", "Scheda video non utilizzabile, passo al processore…"))
                self.modello = WhisperModel(nome, device="cpu", compute_type="int8",
                                            download_root=MODELLI_DIR)
                self.dev = "CPU"
                righe = self._trascrivi(path)
            if self.stop_evt.is_set():
                raise Interrotto(righe)
            out = os.path.splitext(path)[0] + ".txt"
            with open(out, "w", encoding="utf-8") as f:
                f.write("\n".join(righe))
            self.ui.put(("fine", out))
        except Interrotto as e:
            righe = e.args[0] if e.args else []
            out = None
            if righe:   # salva quello che c'e' gia', con un nome che dice che e' incompleto
                out = os.path.splitext(path)[0] + " (parziale).txt"
                with open(out, "w", encoding="utf-8") as f:
                    f.write("\n".join(righe))
            self.ui.put(("interrotta", out))
        except Exception as e:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.datetime.now():%Y-%m-%d %H:%M} ---\n")
                f.write(traceback.format_exc())
            self.ui.put(("errore", f"{type(e).__name__}: {e}\n\nDettagli completi in: {LOG}"))

    def _trascrivi(self, path):
        self.controlla_stop()
        self.ui.put(("attesa", "Leggo il file audio…"))
        audio = carica_audio(path)
        self.controlla_stop()
        self.ui.put(("attesa", "Cerco le parti parlate…"))
        segmenti, info = self.modello.transcribe(
            audio,
            language="it",
            beam_size=self.beam,                  # 1 = veloce, 5 = piu' accurato
            vad_filter=True,                       # salta i silenzi
            vad_parameters={"threshold": 0.35},    # piu' sensibile: non perde il parlato a basso volume
            condition_on_previous_text=False,      # evita ripetizioni a loop
        )
        durata = info.duration or 1
        self.ui.put(("attesa", f"Trascrivo ({self.dev} · {self.nome_modello}"
                               f"{' · veloce' if self.beam == 1 else ''})…"))
        self.t_inizio = time.time()   # il tempo stimato parte da qui
        righe = []
        self.controlla_stop()
        for s in segmenti:
            if self.stop_evt.is_set():
                break   # il resto del file non viene elaborato
            riga = s.text.strip()
            if not riga:
                continue
            righe.append(riga)
            self.ui.put(("riga", riga))
            self.ui.put(("prog", min(100.0, s.end / durata * 100)))
        return righe

    def controlla_stop(self):
        if self.stop_evt.is_set():
            raise Interrotto([])

    def interrompi(self):
        self.stop_evt.set()
        self.btn_apri.config(state="disabled")
        self.stato.set("Interrompo… finisco il pezzo in corso")

    def ripristina_apri(self):
        self.btn_apri.config(text="Trascrivi un file…", style="Acc.TButton", command=self.apri)

    # ---------------- AGGIORNAMENTO FINESTRA ----------------
    def pompa_ui(self):
        try:
            while True:
                tipo, v = self.ui.get_nowait()
                if tipo == "riga":
                    if self.placeholder:
                        self.svuota_testo()
                    self.testo.insert("end", v + "\n")
                    self.testo.see("end")
                elif tipo == "prog":
                    self.pct = v
                    self.barra_valore(v)
                    self.pct_txt.set(f"{v:.0f}%")
                elif tipo == "attesa":
                    self.barra_attesa(v)
                elif tipo == "pulisci":
                    self.svuota_testo()
                    self.pct = 0.0
                elif tipo in ("fine", "errore", "interrotta"):
                    self.occupato = False
                    self.btn_parziale.config(state="disabled")
                    self.ripristina_apri()
                    self.comandi(True)
                    totale = time.time() - self.t_totale
                    self.t_inizio = None
                    if tipo == "interrotta":
                        self.barra_valore(self.pct)
                        self.stato.set(f"Interrotta al {self.pct:.0f}% (dopo {durata_txt(totale)})")
                        self.info.set(f"Testo parziale salvato in: {v}" if v
                                      else "Interrotta prima che ci fosse testo: niente da salvare.")
                    elif tipo == "fine":
                        self.barra_valore(100)
                        self.pct_txt.set("100%")
                        self.stato.set(f"✓ Fatto in {durata_txt(totale)}")
                        self.info.set(f"Testo salvato in: {v}")
                    else:
                        self.barra_valore(0)
                        self.pct_txt.set("")
                        self.stato.set("Errore")
                        self.info.set("Qualcosa è andato storto: i dettagli sono in errori.txt")
                        messagebox.showerror("Errore", v)
        except queue.Empty:
            pass
        self.root.after(100, self.pompa_ui)

    def tick(self):
        """Ogni mezzo secondo: timer della registrazione e tempo rimanente."""
        if self.registrando:
            self.pct_txt.set(durata_txt(time.time() - self.t0))
            self.prog["value"] = self.livello
        elif self.occupato and self.t_inizio and time.time() > self.info_fissa_fino:
            trascorso = time.time() - self.t_inizio
            if self.pct >= 1:
                rimane = trascorso * (100 - self.pct) / self.pct
                self.info.set(f"{self.file_corrente}  ·  trascorso {durata_txt(trascorso)}"
                              f"  ·  mancano circa {durata_txt(rimane)}")
            else:
                self.info.set(f"{self.file_corrente}  ·  trascorso {durata_txt(trascorso)}")
        self.root.after(500, self.tick)

    # ---------------- VARIE ----------------
    def testo_attuale(self):
        return "" if self.placeholder else self.testo.get("1.0", "end").strip()

    def copia(self):
        t = self.testo_attuale()
        if t:
            self.root.clipboard_clear()
            self.root.clipboard_append(t)
            self.info.set("Testo copiato: ora puoi incollarlo dove vuoi.")

    def salva(self):
        t = self.testo_attuale()
        if not t:
            return
        f = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Testo", "*.txt")])
        if f:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(t)
            self.info.set(f"Salvato in: {f}")

    def salva_parziale(self):
        """Salva il testo trascritto finora, senza fermare la trascrizione."""
        t = self.testo_attuale()
        if not t:
            self.info.set("Ancora niente da salvare: aspetta che compaia il primo pezzo di testo.")
            return
        out = os.path.splitext(self.path_corrente)[0] + " (parziale).txt"
        with open(out, "w", encoding="utf-8") as f:
            f.write(t)
        self.info.set(f"✓ Salvato fino al {self.pct:.0f}% in: {out}  (la trascrizione continua)")
        self.info_fissa_fino = time.time() + 5   # il messaggio resta visibile qualche secondo

    def apri_cartella(self, cartella):
        try:
            os.startfile(cartella)
        except Exception:
            messagebox.showinfo("Cartella", cartella)

    def chiudi(self):
        if self.registrando:
            if not messagebox.askyesno("Esci", "Registrazione in corso: la fermo, la salvo ed esco?"):
                return
            self.stop_rec(chiedi=False)
        if self.occupato and not messagebox.askyesno("Esci", "Trascrizione in corso: uscire comunque?"):
            return
        self.root.destroy()


if __name__ == "__main__":
    if os.name == "nt":
        try:
            import ctypes
            # icona giusta nella barra delle applicazioni (non quella di Python)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("trascrittore.app")
            # testo nitido sugli schermi ad alta risoluzione
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()
