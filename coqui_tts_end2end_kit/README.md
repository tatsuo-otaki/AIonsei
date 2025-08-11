
# Coqui TTS End-to-End Kit（録音 → データセット作成）

このキットは、台本の録音から LJSpeech 互換の `datasets/myvoice/` を作るところまでを一式で行えます。
- 録音GUI: `recorder_gui.py`（起動ごとに一意のセッションフォルダを作成）
- 台本: `lines.txt`（日常＋AI専門用語、三連クオート問題なし）
- 変換: `make_dataset.py`（セッション出力を `datasets/myvoice/` にコピー）

## 0) 依存ライブラリ（仮想環境内で）
```bash
pip install sounddevice soundfile numpy simpleaudio
```

## 1) 録音する
```bash
python recorder_gui.py
```
- 出力は `output/lines-YYYYmmdd_HHMMSS/` に作成されます。
- 中に `wavs/voice_XXXX.wav` と `metadata.csv` が保存されます。

## 2) データセットへコピー
録音が終わったら、セッションフォルダを指定して `datasets/myvoice/` に反映します。

```bash
python make_dataset.py output/lines-YYYYmmdd_HHMMSS
```
- `datasets/myvoice/wavs/` に音声をコピー、`datasets/myvoice/metadata.csv` に追記します。
- 既存の同名ファイルは重複コピーしません（メタも重複追記しません）。

## 3) Coqui TTS の学習に使う
`datasets/myvoice/` ができたら、TTS のトレーニング設定にそのパスを指定してください。
（VITS系の日本語モデルに対する転移学習が推奨）

---

### ヒント
- 録音は **3〜8秒/文**、合計 **10〜20分以上**が目安です。
- 同じマイク・同じ環境で収録するほど品質が安定します。
- エラーメッセージが出たら、そのスクショや文面を貼ってください。すぐ直せます。
