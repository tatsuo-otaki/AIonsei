# -*- coding: utf-8 -*-
import os, time, queue, threading, tkinter as tk
from tkinter import ttk, messagebox
import numpy as np

try:
    import sounddevice as sd
    import soundfile as sf
    import simpleaudio as sa
except Exception as e:
    print('必要なパッケージをインストールしてください: pip install sounddevice soundfile numpy simpleaudio')
    raise

SAMPLE_RATE = 22050
CHANNELS = 1
LINES_FILE = 'lines.txt'

def make_session_dirs():
    script = os.path.splitext(os.path.basename(LINES_FILE))[0]
    ts = time.strftime('%Y%m%d_%H%M%S')
    root = os.path.join('output', f'{script}-{ts}')
    wav_dir = os.path.join(root, 'wavs')
    os.makedirs(wav_dir, exist_ok=True)
    return root, wav_dir, os.path.join(root, 'metadata.csv')

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Coqui TTS 録音ツール（end-to-end / quote-safe）')
        self.geometry('800x520')
        self.resizable(False, False)

        self.session_root, self.wav_dir, self.meta_path = make_session_dirs()

        try:
            with open(LINES_FILE, 'r', encoding='utf-8') as f:
                self.lines = [ln.strip() for ln in f if ln.strip()]
        except FileNotFoundError:
            messagebox.showerror('エラー', f'{LINES_FILE} が見つかりません。')
            self.destroy(); raise SystemExit

        if not self.lines:
            messagebox.showerror('エラー', 'lines.txt に有効な文章がありません。')
            self.destroy(); raise SystemExit

        self.idx = 0
        self.recording = False
        self.frames = []
        self.audio_q = queue.Queue()
        self.stream = None
        self.current_audio = None

        self.build_ui()
        self.update_ui()

    def build_ui(self):
        self.lbl_script = ttk.Label(self, text=f'台本: {os.path.abspath(LINES_FILE)}')
        self.lbl_script.pack(pady=(8,2))
        self.lbl_dest = ttk.Label(self, text=f'出力先: {os.path.abspath(self.session_root)}')
        self.lbl_dest.pack(pady=(0,6))
        self.lbl_idx = ttk.Label(self, text='', font=('Helvetica', 14))
        self.lbl_idx.pack(pady=(0,4))
        self.txt = tk.Text(self, height=4, wrap='word', font=('Hiragino Sans', 16))
        self.txt.pack(fill='x', padx=16)
        self.status = ttk.Label(self, text='準備完了（Spaceで録音開始/停止）', foreground='#444')
        self.status.pack(pady=6)
        btns = ttk.Frame(self); btns.pack(pady=8)
        self.btn_rec = ttk.Button(btns, text='● 録音開始', command=self.on_record)
        self.btn_stop = ttk.Button(btns, text='■ 停止', command=self.on_stop, state='disabled')
        self.btn_play = ttk.Button(btns, text='▶ 再生', command=self.on_play, state='disabled')
        self.btn_accept = ttk.Button(btns, text='✔ 確定保存', command=self.on_accept, state='disabled')
        self.btn_retake = ttk.Button(btns, text='↺ 取り直し', command=self.on_retake, state='disabled')
        self.btn_prev = ttk.Button(btns, text='⟵ 前へ', command=self.on_prev)
        self.btn_next = ttk.Button(btns, text='次へ ⟶', command=self.on_next)
        for i, b in enumerate([self.btn_rec, self.btn_stop, self.btn_play, self.btn_accept, self.btn_retake, self.btn_prev, self.btn_next]):
            b.grid(row=0, column=i, padx=6)
        self.progress = ttk.Progressbar(self, length=740, mode='determinate', maximum=len(self.lines))
        self.progress.pack(pady=(6,6))
        self.bind('<space>', lambda e: self.on_record() if not self.recording else self.on_stop())
        self.bind('<Return>', lambda e: self.on_accept())
        self.bind('<BackSpace>', lambda e: self.on_retake())
        self.bind('<Left>', lambda e: self.on_prev())
        self.bind('<Right>', lambda e: self.on_next())

    def update_ui(self):
        self.txt.delete('1.0', 'end')
        self.txt.insert('1.0', self.lines[self.idx])
        self.lbl_idx.config(text=f'{self.idx+1} / {len(self.lines)}')
        self.progress['value'] = self.idx
        self.set_buttons(recording=False, recorded=(self.current_audio is not None))

    def audio_cb(self, indata, frames, tinfo, status):
        self.audio_q.put(indata.copy())

    def on_record(self):
        if self.recording: return
        self.recording = True
        self.current_audio = None
        self.frames = []
        self.audio_q = queue.Queue()
        self.set_buttons(recording=True, recorded=False)
        self.status.config(text='録音中…（Spaceで停止）')
        self.stream = sd.InputStream(channels=CHANNELS, callback=self.audio_cb, samplerate=SAMPLE_RATE, blocksize=2048)
        self.stream.start()
        def collector():
            import queue as _q
            while self.recording:
                try: data = self.audio_q.get(timeout=0.2); self.frames.append(data)
                except _q.Empty: pass
        threading.Thread(target=collector, daemon=True).start()

    def on_stop(self):
        if not self.recording: return
        self.recording = False
        try:
            if self.stream: self.stream.stop(); self.stream.close(); self.stream=None
        except Exception: pass
        if self.frames:
            audio = np.concatenate(self.frames, axis=0)
            peak = float(np.max(np.abs(audio))) if len(audio)>0 else 0.0
            if peak>0: audio = 0.95 * audio / peak
            self.current_audio = audio.astype(np.float32)
            dur = len(self.current_audio)/SAMPLE_RATE
            self.status.config(text=f'録音完了：{dur:.1f} 秒（▶再生→✔保存）')
            self.set_buttons(recording=False, recorded=True)
        else:
            self.status.config(text='音声が記録されませんでした。')
            self.set_buttons(recording=False, recorded=False)

    def on_play(self):
        if self.current_audio is None: return
        wav = (self.current_audio * 32767).astype(np.int16).tobytes()
        try: sa.play_buffer(wav, num_channels=CHANNELS, bytes_per_sample=2, sample_rate=SAMPLE_RATE)
        except Exception as e: messagebox.showerror('再生エラー', str(e))

    def on_accept(self):
        if self.current_audio is None:
            self.status.config(text='保存できる音声がありません。'); return
        fname = f'voice_{self.idx+1:04d}.wav'
        path = os.path.join(self.wav_dir, fname)
        try:
            sf.write(path, self.current_audio, SAMPLE_RATE, subtype='PCM_16')
            row = f"{fname}|{self.lines[self.idx].replace('\n',' ').strip()}\n"
            exists = False
            if os.path.exists(self.meta_path):
                with open(self.meta_path, 'r', encoding='utf-8') as fr:
                    for ln in fr:
                        if ln.strip() == row.strip(): exists = True; break
            if not exists:
                with open(self.meta_path, 'a', encoding='utf-8') as fw: fw.write(row)
        except Exception as e:
            messagebox.showerror('保存エラー', str(e)); return
        self.status.config(text=f'保存しました：{fname}')
        self.current_audio = None
        if self.idx < len(self.lines)-1: self.idx += 1; self.update_ui()
        else:
            messagebox.showinfo('完了', '全ての文の保存が完了しました。')
            self.set_buttons(recording=False, recorded=False)

    def on_retake(self):
        self.current_audio = None; self.frames = []
        self.status.config(text='取り直しできます。録音を開始してください。')
        self.set_buttons(recording=False, recorded=False)

    def on_prev(self):
        if self.idx>0: self.idx -= 1; self.current_audio=None; self.update_ui()

    def on_next(self):
        if self.idx < len(self.lines)-1: self.idx += 1; self.current_audio=None; self.update_ui()

    def set_buttons(self, recording: bool, recorded: bool):
        self.btn_rec.config(state='disabled' if recording else 'normal')
        self.btn_stop.config(state='normal' if recording else 'disabled')
        self.btn_play.config(state='normal' if recorded else 'disabled')
        self.btn_accept.config(state='normal' if recorded else 'disabled')
        self.btn_retake.config(state='normal' if recorded else 'disabled')

if __name__ == '__main__':
    App().mainloop()
