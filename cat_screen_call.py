
import socket, threading, struct, json, time, secrets, io, queue, re, os, webbrowser, datetime, tkinter as tk, urllib.request, urllib.error
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageGrab

APP_NAME = "Cat Screen Call"
VERSION = "1.0.0"

# GitHub update/event repository
GITHUB_REPO = "Cat67Lisic/Cat-Screen-Call-Updates-events"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
UPDATE_JSON_URL = f"{GITHUB_RAW_BASE}/update.json"
EVENTS_JSON_URL = f"{GITHUB_RAW_BASE}/events.json"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"

def send_packet(sock, obj=None, raw=b""):
    if obj is not None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        head = b"J" + struct.pack("!I", len(data))
        sock.sendall(head + data)
    else:
        head = b"I" + struct.pack("!I", len(raw))
        sock.sendall(head + raw)

def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        part = sock.recv(n-len(data))
        if not part:
            raise ConnectionError("Соединение закрыто")
        data += part
    return data

def recv_packet(sock):
    kind = recv_exact(sock, 1)
    n = struct.unpack("!I", recv_exact(sock, 4))[0]
    data = recv_exact(sock, n)
    if kind == b"J":
        return "json", json.loads(data.decode("utf-8"))
    return "image", data


def version_tuple(value):
    """Convert 1.2.3 / v1.2.3 to a comparable tuple."""
    value = str(value).strip().lstrip("vV")
    parts = []
    for part in value.split("."):
        m = re.match(r"\d+", part)
        if not m:
            break
        parts.append(int(m.group()))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "CatScreenCall/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))

def sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def check_github_update():
    try:
        data = fetch_json(UPDATE_JSON_URL)
        latest = str(data.get("version", "")).lstrip("vV")
        if not latest:
            return {"ok": False, "message": "В update.json не указана версия."}
        return {"ok": True, "latest": latest,
                "url": data.get("release_url", GITHUB_RELEASES_URL),
                "download_url": data.get("download_url", ""),
                "sha256": str(data.get("sha256", "")).lower(),
                "notes": data.get("notes", "")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "message": f"GitHub: HTTP {e.code}. Файл update.json ещё не опубликован."}
    except urllib.error.URLError as e:
        return {"ok": False, "message": f"Нет соединения с GitHub: {e.reason}"}
    except Exception as e:
        return {"ok": False, "message": f"Ошибка проверки: {e}"}

def fetch_events():
    data = fetch_json(EVENTS_JSON_URL)
    return data.get("events", [])

def download_file(url, destination, expected_sha256=""):
    req = urllib.request.Request(url, headers={"User-Agent": "CatScreenCall/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response, open(destination, "wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    if expected_sha256:
        actual = sha256_file(destination)
        if actual.lower() != expected_sha256.lower():
            try: os.remove(destination)
            except OSError: pass
            raise ValueError("SHA-256 не совпадает с указанным в update.json/events.json")
    return destination


class CatScreenCall(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("980x680")
        self.minsize(820, 560)
        self.configure(bg="#0b0f16")
        self.sock = None
        self.server = None
        self.stop_event = threading.Event()
        self.connected = False
        self.allow_control = False
        self.photo = None
        self.code = secrets.token_hex(3).upper()
        self._build()

    def _build(self):
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except: pass
        style.configure("TButton", padding=9, font=("Segoe UI", 10))
        style.configure("TLabel", background="#0b0f16", foreground="#e8eef7", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 23, "bold"))
        style.configure("Card.TFrame", background="#111824")

        top = ttk.Frame(self, style="Card.TFrame")
        top.pack(fill="x", padx=18, pady=18)
        ttk.Label(top, text="🐱 Cat Screen Call", style="Title.TLabel").pack(side="left", padx=16, pady=13)
        ttk.Label(top, text="Безопасная удалённая помощь", background="#111824",
                  foreground="#9fb0c6").pack(side="left", padx=8)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=18, pady=(0,18))

        left = ttk.Frame(body, style="Card.TFrame")
        left.pack(side="left", fill="y", padx=(0,12))
        ttk.Label(left, text="Подключение", font=("Segoe UI",14,"bold"),
                  background="#111824", foreground="#fff").pack(padx=16,pady=(18,8))

        self.code_label = ttk.Label(left, text=f"Код: {self.code}",
                                    background="#111824", foreground="#4d96ff",
                                    font=("Consolas",18,"bold"))
        self.code_label.pack(padx=16,pady=8)

        ttk.Button(left,text="Создать комнату",command=self.host).pack(fill="x",padx=16,pady=5)
        ttk.Button(left,text="Подключиться",command=self.connect_dialog).pack(fill="x",padx=16,pady=5)
        ttk.Button(left,text="Отключиться",command=self.disconnect).pack(fill="x",padx=16,pady=5)
        ttk.Button(left,text="Проверить обновление",command=self.check_update).pack(fill="x",padx=16,pady=5)
        ttk.Button(left,text="Событийные обновления",command=self.check_events).pack(fill="x",padx=16,pady=5)

        ttk.Separator(left).pack(fill="x",padx=16,pady=15)
        ttk.Label(left,text="Разрешения",font=("Segoe UI",12,"bold"),
                  background="#111824",foreground="#fff").pack(padx=16,pady=5)
        self.control_var = tk.BooleanVar(value=False)
        cb = tk.Checkbutton(left,text="Разрешить управление",
                            variable=self.control_var, command=self.toggle_control,
                            bg="#111824",fg="#e8eef7",selectcolor="#111824",
                            activebackground="#111824",activeforeground="#fff")
        cb.pack(anchor="w",padx=16,pady=5)
        ttk.Label(left,text="Изменение действует только после\nявного согласия владельца ПК.",
                  background="#111824",foreground="#8fa0b5").pack(padx=16,pady=4)

        right = ttk.Frame(body, style="Card.TFrame")
        right.pack(side="left", fill="both", expand=True)

        self.screen = tk.Label(right,text="Экран удалённого компьютера\n\nНет подключения",
                               bg="#070a10",fg="#7e8ca0",font=("Segoe UI",14))
        self.screen.pack(fill="both",expand=True,padx=12,pady=12)

        chat = ttk.Frame(self, style="Card.TFrame")
        chat.pack(fill="x", padx=18, pady=(0,18))
        self.chat = tk.Text(chat,height=7,bg="#070a10",fg="#dce6f4",
                            insertbackground="white",relief="flat")
        self.chat.pack(side="left",fill="both",expand=True,padx=10,pady=10)
        sendbox = ttk.Frame(chat)
        sendbox.pack(side="right",fill="y",padx=10,pady=10)
        self.msg = ttk.Entry(sendbox,width=25)
        self.msg.pack(pady=(0,6))
        ttk.Button(sendbox,text="Отправить",command=self.send_chat).pack(fill="x")
        self.status = ttk.Label(self,text="Статус: не подключено",foreground="#9fb0c6")
        self.status.pack(anchor="w",padx=22,pady=(0,12))

        self.protocol("WM_DELETE_WINDOW", self.close)

    def warn(self):
        return messagebox.askokcancel(
            "Правила Cat Screen Call",
            "Cat Screen Call предназначен только для удалённой помощи с разрешения владельца компьютера.\n\n"
            "Запрещено использовать программу для мошенничества, обмана, скрытого наблюдения "
            "или доступа к чужому компьютеру без разрешения.\n\n"
            "Нажимая «Продолжить», вы подтверждаете, что используете соединение законно "
            "и согласованно с владельцем устройства."
        )

    def host(self):
        if not self.warn(): return
        if self.server: return
        self.code = secrets.token_hex(3).upper()
        self.code_label.config(text=f"Код: {self.code}")
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.server.bind(("0.0.0.0",0))
        self.server.listen(1)
        self.port = self.server.getsockname()[1]
        self.status.config(text=f"Статус: ожидание подключения • порт {self.port}")
        threading.Thread(target=self.accept_loop,daemon=True).start()

    def accept_loop(self):
        try:
            sock, addr = self.server.accept()
            # The code is a session password; it must be sent first.
            kind, obj = recv_packet(sock)
            if kind != "json" or obj.get("type") != "hello" or obj.get("code") != self.code:
                sock.close(); return
            if not messagebox.askyesno("Запрос удалённого доступа",
                    f"Компьютер {addr[0]} хочет подключиться.\n\nРазрешить просмотр экрана и чат?"):
                sock.close(); return
            self.sock=sock; self.connected=True
            send_packet(sock, {"type":"accepted","control":False})
            self.status.config(text=f"Статус: подключено • {addr[0]}")
            threading.Thread(target=self.receiver,daemon=True).start()
            threading.Thread(target=self.screen_sender,daemon=True).start()
        except Exception as e:
            self.after(0,lambda: self.status.config(text=f"Ошибка: {e}"))

    def connect_dialog(self):
        if not self.warn(): return
        win=tk.Toplevel(self); win.title("Подключиться"); win.geometry("360x220")
        win.configure(bg="#0b0f16")
        tk.Label(win,text="IP-адрес",bg="#0b0f16",fg="white").pack(pady=(20,4))
        ip=tk.Entry(win); ip.pack()
        tk.Label(win,text="Код комнаты",bg="#0b0f16",fg="white").pack(pady=4)
        code=tk.Entry(win); code.pack()
        tk.Label(win,text="Порт (показывается владельцу ПК)",bg="#0b0f16",fg="#9fb0c6").pack(pady=4)
        port=tk.Entry(win); port.insert(0,"5000"); port.pack()
        def go():
            try:
                self.sock=socket.create_connection((ip.get().strip(),int(port.get())),timeout=8)
                send_packet(self.sock,{"type":"hello","code":code.get().strip().upper()})
                threading.Thread(target=self.receiver,daemon=True).start()
                self.connected=True
                self.status.config(text="Статус: запрос отправлен")
                win.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка подключения",str(e))
        ttk.Button(win,text="Отправить запрос",command=go).pack(pady=14)

    def receiver(self):
        try:
            while not self.stop_event.is_set() and self.sock:
                kind,data=recv_packet(self.sock)
                if kind=="image":
                    try:
                        im=Image.open(io.BytesIO(data))
                        im.thumbnail((760,470))
                        self.photo=ImageTk.PhotoImage(im)
                        self.after(0,lambda p=self.photo: self.screen.config(image=p,text=""))
                    except: pass
                elif data.get("type")=="chat":
                    self.after(0,lambda m=data.get("message",""): self.add_chat("Удалённый",m))
                elif data.get("type")=="accepted":
                    self.after(0,lambda:self.status.config(text="Статус: подключено"))
        except Exception:
            self.after(0,lambda:self.status.config(text="Статус: соединение завершено"))

    def screen_sender(self):
        while self.connected and not self.stop_event.is_set():
            try:
                img=ImageGrab.grab()
                img.thumbnail((900,600))
                buf=io.BytesIO()
                img.save(buf,format="JPEG",quality=55)
                send_packet(self.sock,raw=buf.getvalue())
                time.sleep(.25)
            except: break

    def send_chat(self):
        m=self.msg.get().strip()
        if not m or not self.sock: return
        try:
            send_packet(self.sock,{"type":"chat","message":m})
            self.add_chat("Вы",m); self.msg.delete(0,"end")
        except Exception as e: messagebox.showerror("Чат",str(e))

    def add_chat(self,who,msg):
        self.chat.insert("end",f"{who}: {msg}\n")
        self.chat.see("end")

    def toggle_control(self):
        # This first release deliberately keeps control disabled; screen sharing/chat
        # are implemented, while control requires an additional audited input layer.
        if self.control_var.get():
            self.control_var.set(False)
            messagebox.showinfo("Безопасность",
                "Управление мышью и клавиатурой пока отключено в этой версии. "
                "Просмотр экрана и чат работают без удалённого управления.")

    def check_update(self):
        self.status.config(text="Статус: проверка обновления через GitHub…")
        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def _check_update_worker(self):
        result = check_github_update()
        def show_result():
            if not result.get("ok"):
                self.status.config(text="Статус: проверка обновления не выполнена")
                messagebox.showwarning("Проверка обновления", result.get("message", "Не удалось проверить обновление."))
                return
            latest = result["latest"]
            if version_tuple(latest) > version_tuple(VERSION):
                self.status.config(text=f"Статус: доступна новая версия {latest}")
                if messagebox.askyesno("Доступно обновление", f"Установлена: {VERSION}\nНовая версия: {latest}\n\nСкачать обновление?"):
                    threading.Thread(target=self._download_update, args=(result,), daemon=True).start()
            else:
                self.status.config(text=f"Статус: установлена последняя версия {VERSION}")
                messagebox.showinfo("Обновление", f"Cat Screen Call {VERSION} — актуальная версия.")
        self.after(0, show_result)

    def _download_update(self, result):
        url = result.get("download_url")
        if not url:
            self.after(0, lambda: webbrowser.open(result.get("url", GITHUB_RELEASES_URL)))
            return
        os.makedirs("updates", exist_ok=True)
        path = os.path.join("updates", f"CatScreenCall-{result['latest']}.zip")
        try:
            self.after(0, lambda: self.status.config(text="Статус: скачивание обновления…"))
            download_file(url, path, result.get("sha256", ""))
            self.after(0, lambda: (self.status.config(text="Статус: обновление скачано"),
                                   messagebox.showinfo("Обновление", f"Файл скачан в:\n{os.path.abspath(path)}\n\nЗакройте программу и установите новую версию.")))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Обновление", f"Не удалось скачать обновление:\n{e}"))

    def check_events(self):
        self.status.config(text="Статус: проверка событий через GitHub…")
        threading.Thread(target=self._events_worker, daemon=True).start()

    def _events_worker(self):
        try:
            events = fetch_events()
            today = datetime.date.today()
            active = []
            for event in events:
                try:
                    start = datetime.date.fromisoformat(event["start_date"])
                    end = datetime.date.fromisoformat(event["end_date"])
                    if start <= today <= end:
                        active.append(event)
                except (KeyError, ValueError):
                    continue
            def show():
                if not active:
                    self.status.config(text="Статус: активных событий нет")
                    messagebox.showinfo("Событийные обновления", "Сейчас активных праздничных обновлений нет.")
                    return
                lines = []
                for e in active:
                    lines.append(f"{e.get('title','Event')}\n{e.get('description','')}\n")
                if messagebox.askyesno("Событийные обновления", "\n".join(lines) + "\nСкачать доступные события?"):
                    for e in active:
                        if e.get("download_url"):
                            threading.Thread(target=self._download_event, args=(e,), daemon=True).start()
            self.after(0, show)
        except urllib.error.HTTPError as e:
            self.after(0, lambda: messagebox.showwarning("События", f"GitHub: HTTP {e.code}. events.json ещё не опубликован."))
        except Exception as e:
            self.after(0, lambda: messagebox.showwarning("События", f"Не удалось получить события: {e}"))

    def _download_event(self, event):
        os.makedirs("events", exist_ok=True)
        name = re.sub(r"[^a-zA-Z0-9._-]+", "_", event.get("id", event.get("title", "event")))
        path = os.path.join("events", name + ".zip")
        try:
            download_file(event["download_url"], path, event.get("sha256", ""))
            self.after(0, lambda: self.status.config(text=f"Статус: событие скачано — {event.get('title','Event')}"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Событийное обновление", str(e)))

    def disconnect(self):
        self.connected=False
        try:
            if self.sock:self.sock.close()
        except:pass
        self.sock=None
        self.status.config(text="Статус: не подключено")
        self.screen.config(image="",text="Экран удалённого компьютера\n\nНет подключения")

    def close(self):
        self.stop_event.set()
        self.disconnect()
        try:
            if self.server:self.server.close()
        except:pass
        self.destroy()

if __name__=="__main__":
    CatScreenCall().mainloop()
