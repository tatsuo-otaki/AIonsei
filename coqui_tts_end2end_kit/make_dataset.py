# -*- coding: utf-8 -*-
import os, shutil, sys

def main():
    if len(sys.argv) < 2:
        print('使い方: python make_dataset.py output/lines-YYYYmmdd_HHMMSS')
        sys.exit(1)
    session = sys.argv[1]
    wav_dir = os.path.join(session, 'wavs')
    meta_src = os.path.join(session, 'metadata.csv')
    if not os.path.isdir(wav_dir) or not os.path.isfile(meta_src):
        print('指定フォルダに wavs/ または metadata.csv が見つかりません。')
        sys.exit(1)

    dst_root = os.path.join('datasets', 'myvoice')
    dst_wavs = os.path.join(dst_root, 'wavs')
    os.makedirs(dst_wavs, exist_ok=True)

    # 既存の metadata を保持しながら追記
    meta_dst = os.path.join(dst_root, 'metadata.csv')
    # 既存ファイル名集合
    existing = set()
    if os.path.isfile(meta_dst):
        with open(meta_dst, 'r', encoding='utf-8') as f:
            for ln in f:
                name = ln.split('|',1)[0].strip()
                if name: existing.add(name)

    # コピー & メタ追記（重複回避）
    appended = 0
    with open(meta_dst, 'a', encoding='utf-8') as out, open(meta_src, 'r', encoding='utf-8') as src:
        for ln in src:
            ln = ln.strip()
            if not ln: continue
            name = ln.split('|',1)[0].strip()
            if name in existing: 
                continue
            src_path = os.path.join(wav_dir, name)
            if not os.path.isfile(src_path):
                continue
            shutil.copy2(src_path, os.path.join(dst_wavs, name))
            out.write(ln + '\n')
            existing.add(name); appended += 1

    print('コピー先:', os.path.abspath(dst_root))
    print('追記した行数:', appended)

if __name__ == '__main__':
    main()
