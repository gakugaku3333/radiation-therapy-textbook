# 放射線治療部門 異動前準備教科書

診断放射線部門から放射線治療部門へ異動する診療放射線技師のための実践的入門テキストです。

## 内容

- **教科書本文**（`放射線治療部門_異動前準備教科書.md`）
  - 第1章 放射線治療とは何か
  - 第2章 診断放射線との違い
  - 第3章 必須専門用語
  - 第4章 業務内容の詳細
  - 第5章 最初に戸惑うポイントとその対処法
  - 第6章 資格・認定制度
  - 第7章 学習ロードマップと推奨リソース
  - 第8章 部位別疾患と放射線治療
  - 第9章 施設導入機器・システム詳細解説
  - 第10章 放射線治療の診療報酬・加算

- **ポッドキャストスクリプト**（`ポッドキャスト/`）
  - 全10エピソード、2人対話（ホスト×専門家）形式

- **音声自動生成スクリプト**（`generate_podcast_audio.py`）
  - Google Gemini TTS APIでスクリプトをWAV音声に変換

## ポッドキャスト音声の生成方法

```bash
pip install google-genai

export GEMINI_API_KEY="your_api_key"  # https://aistudio.google.com/apikey

# 1エピソードだけ試す
python generate_podcast_audio.py --episode 1

# 全エピソード一括生成
python generate_podcast_audio.py --all
```

APIキーはGoogle AI Studioで無料取得できます。生成モデルは `gemini-2.5-flash-preview-tts`（マルチスピーカー対応）を使用しています。
