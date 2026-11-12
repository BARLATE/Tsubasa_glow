---
name: youtube-summary
description: YouTube動画の文字起こし(字幕)を取得して要約する。ユーザーがYouTubeのURLや動画IDを渡して「要約して」「まとめて」「何を言ってる?」「文字起こしして」と頼んだとき、または動画の内容について質問したときに使う。Fetches a YouTube video's transcript and summarizes it — use whenever a youtube.com / youtu.be link appears with a request to summarize, explain, or transcribe it.
---

# YouTube 文字起こし要約

## 手順

1. **文字起こしを取得する**(必ずスクリプトを使う。動画の内容を推測で書かない):

   ```bash
   python3 .claude/skills/youtube-summary/scripts/fetch_transcript.py "<URL または動画ID>" --lang ja,en > /tmp/transcript.txt
   ```

   - 初回は依存パッケージが必要: `pip install youtube-transcript-api yt-dlp`(クラウド環境などで YouTube に弾かれた場合は自動で yt-dlp に切り替わる)
   - `--lang` は優先順。指定言語がなければ利用可能な字幕(自動生成含む)を使う。
   - 出力は `[mm:ss] テキスト` 形式。先頭行に動画ID・言語・自動生成かどうかが入る。
   - 字幕が無い/取得できない場合は、その旨をユーザーに伝えて終了する(内容をでっち上げない)。

2. **長さを確認する**: `wc -c /tmp/transcript.txt`。
   約 40,000 文字を超える場合は、`[mm:ss]` の区切りで数ブロックに分け、ブロックごとに要点を抜き出してから全体をまとめる。

3. **要約を書く**。ユーザーが別の形式を指定しない限り、下のテンプレートで、ユーザーの言語(既定は日本語)で出力する。

## 出力テンプレート

```markdown
## 📺 要約(3行)
- ...
- ...
- ...

## 🗂 章ごとのポイント
- **[00:00] 導入** — ...
- **[03:12] 〇〇について** — ...

## 💡 重要な主張・数字
- ...

## ✅ 結論 / 次のアクション
- ...
```

## ガイドライン

- タイムスタンプは文字起こし中の実際の値を使う(ユーザーが該当箇所へ飛べるように)。
- 自動生成字幕は誤認識が多い。固有名詞が怪しい場合は「(字幕より・要確認)」と添える。
- 話者の意見と事実を区別する。「〜と話者は主張」のように書く。
- ユーザーが「全文」「文字起こしだけ」と言った場合は要約せず、整形した文字起こしを渡す。
- 特定の質問(「〜について何と言ってる?」)には、該当箇所のタイムスタンプ付きで答える。
