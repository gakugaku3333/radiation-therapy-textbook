#!/usr/bin/env python3
"""
Podcast Audio Generator - Gemini TTS Multi-Speaker
放射線治療入門ポッドキャスト → 音声ファイル（WAV）変換スクリプト

使い方:
  # 1エピソードだけ試す
  python generate_podcast_audio.py --episode 1

  # 全エピソードを一括変換
  python generate_podcast_audio.py --all

  # APIキーを直接指定
  python generate_podcast_audio.py --all --api-key YOUR_KEY

  # 声を変えたい場合
  python generate_podcast_audio.py --all --voice-takashi Puck --voice-satoko Kore
"""

import os
import re
import time
import wave
import struct
import argparse
from pathlib import Path

# --- 声のリスト（30種類）参考 ---
# 男性系: Puck, Fenrir, Enceladus, Iapetus, Umbriel, Rasalgethi, Sadachbia
# 女性系: Kore, Aoede, Leda, Zephyr, Callirrhoe, Despina, Sulafat, Vindemiatrix
# 中性系: Charon, Algieba, Algenib

VOICE_TAKASHI = "Puck"   # ホスト・タカシ（明るい男性）
VOICE_SATOKO  = "Kore"   # ゲスト・サトコ（落ち着いた女性）

SCRIPTS_DIR = Path("/Users/oishifamily/Projects/治療勉強/ポッドキャスト")
OUTPUT_DIR  = Path("/Users/oishifamily/Projects/治療勉強/ポッドキャスト音声")

# 1回のAPI呼び出し上限（文字数）。長いエピソードは分割して結合する
CHUNK_MAX_CHARS = 3000


def parse_script(script_path: Path) -> list[tuple[str, str]]:
    """
    スクリプトMDを解析してセリフリストを返す。
    戻り値: [("タカシ", "セリフ"), ("サトコ", "セリフ"), ...]
    """
    content = script_path.read_text(encoding="utf-8")
    turns = []

    for line in content.splitlines():
        # **タカシ**: または **サトコ**: を抽出
        m = re.match(r'\*\*(タカシ|サトコ)\*\*[:：]\s*(.*)', line)
        if m:
            speaker = m.group(1)
            text = m.group(2).strip()
            # 括弧の中の演技指定（笑）などはそのまま残す（TTSが自然に処理）
            if text:
                turns.append((speaker, text))

    return turns


def turns_to_text(turns: list[tuple[str, str]]) -> str:
    """セリフリストをGemini TTS用テキストに変換。"""
    return "\n".join(f"{speaker}: {text}" for speaker, text in turns)


def chunk_turns(turns: list[tuple[str, str]], max_chars: int) -> list[list[tuple[str, str]]]:
    """長いスクリプトを max_chars 文字以下のチャンクに分割。"""
    chunks = []
    current = []
    current_len = 0

    for turn in turns:
        line = f"{turn[0]}: {turn[1]}"
        if current_len + len(line) > max_chars and current:
            chunks.append(current)
            current = [turn]
            current_len = len(line)
        else:
            current.append(turn)
            current_len += len(line)

    if current:
        chunks.append(current)

    return chunks


def generate_chunk_audio(client, text: str, voice_takashi: str, voice_satoko: str) -> bytes:
    """1チャンク分の音声データ（PCM bytes）を生成して返す。"""
    from google.genai import types

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=[
                        types.SpeakerVoiceConfig(
                            speaker="タカシ",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_takashi
                                )
                            )
                        ),
                        types.SpeakerVoiceConfig(
                            speaker="サトコ",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_satoko
                                )
                            )
                        )
                    ]
                )
            )
        )
    )
    return response.candidates[0].content.parts[0].inline_data.data


def save_wav(pcm_data: bytes, output_path: Path, sample_rate: int = 24000):
    """PCMバイト列をWAVファイルとして保存。"""
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)   # モノラル
        wf.setsampwidth(2)   # 16bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)


def generate_episode(script_path: Path, output_dir: Path, api_key: str,
                     voice_takashi: str, voice_satoko: str):
    """1エピソード分の音声を生成してWAVに保存。"""
    from google import genai

    client = genai.Client(api_key=api_key)

    print(f"\n{'='*50}")
    print(f"処理中: {script_path.name}")

    turns = parse_script(script_path)
    if not turns:
        print("  → セリフが見つかりませんでした。スキップ。")
        return

    total_chars = sum(len(t[1]) for t in turns)
    print(f"  セリフ数: {len(turns)}件 / 合計: {total_chars}文字")

    chunks = chunk_turns(turns, CHUNK_MAX_CHARS)
    print(f"  チャンク分割: {len(chunks)}個")

    # 各チャンクのPCMを収集（レートリミット対策: チャンク間4秒待機）
    all_pcm = b""
    for i, chunk in enumerate(chunks, 1):
        text = turns_to_text(chunk)
        print(f"  チャンク {i}/{len(chunks)} 生成中... ({len(text)}文字)")
        pcm = generate_chunk_audio(client, text, voice_takashi, voice_satoko)
        all_pcm += pcm
        if i < len(chunks):
            time.sleep(4)

    # WAV保存
    output_path = output_dir / f"{script_path.stem}.wav"
    save_wav(all_pcm, output_path)
    size_mb = len(all_pcm) / 1_000_000
    print(f"  → 保存完了: {output_path.name} ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Podcast TTS Generator")
    parser.add_argument("--api-key", help="Gemini API key（未指定時は環境変数 GEMINI_API_KEY）")
    parser.add_argument("--episode", type=int, help="特定エピソード番号のみ生成（例: 1）")
    parser.add_argument("--all", action="store_true", help="全エピソードを一括生成")
    parser.add_argument("--voice-takashi", default=VOICE_TAKASHI, help=f"タカシの声（デフォルト: {VOICE_TAKASHI}）")
    parser.add_argument("--voice-satoko",  default=VOICE_SATOKO,  help=f"サトコの声（デフォルト: {VOICE_SATOKO}）")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: APIキーが必要です。")
        print("  方法1: export GEMINI_API_KEY=your_key")
        print("  方法2: --api-key your_key で指定")
        print("  取得先: https://aistudio.google.com/apikey")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 対象スクリプトを決定
    if args.episode:
        pattern = f"ep{args.episode:02d}_*.md"
        script_files = sorted(SCRIPTS_DIR.glob(pattern))
    elif args.all:
        script_files = sorted(SCRIPTS_DIR.glob("ep*.md"))
    else:
        parser.print_help()
        print("\n例: python generate_podcast_audio.py --episode 1")
        return

    if not script_files:
        print(f"スクリプトファイルが見つかりませんでした: {SCRIPTS_DIR}")
        return

    print(f"対象: {len(script_files)}ファイル")
    print(f"タカシの声: {args.voice_takashi} / サトコの声: {args.voice_satoko}")
    print(f"出力先: {OUTPUT_DIR}")

    for script_path in script_files:
        generate_episode(
            script_path, OUTPUT_DIR, api_key,
            args.voice_takashi, args.voice_satoko
        )

    print(f"\n✓ 完了！ 音声ファイルは {OUTPUT_DIR} にあります。")


if __name__ == "__main__":
    main()
