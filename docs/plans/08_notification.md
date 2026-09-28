# 開発計画書 08：通知編

版：v0.1／更新日：2026-09-28  
状態：version 1は稼働中。version 2は仕様策定済み・未実装  
到達目標：ジョブ、報告、外部の出来事、データの警告を1つの形式で受信側へ届け、
種類を増やしても受信側を直さずに最低限の表示ができるようにする。

本編は管理者向けの運用通知の形式と経路を扱う。通知を出すジョブの構成は
[02_data_collection.md](02_data_collection.md)8章「ジョブ実行と通知」、データ品質の通知の候補は
[05_data_view.md](05_data_view.md)11章を正本とし、本編は通知そのものの仕様の正本とする。

## 1. 位置付けと範囲

### 1.1 扱うものと扱わないもの

| 扱う | 扱わない |
|---|---|
| 管理者（開発者）向けの運用通知。ジョブの開始・終了・失敗、サーバーの定点報告、アプリストアの書き込み、データの異常の知らせ | 利用者（農家）向けのアプリの通知。[06_application.md](06_application.md)6章を正本とする |

### 1.2 送信側と受信側の役割分担

- 送信側はデータを送る。人が読む文章は組み立てない
- 受信側は、受け取った通知を記録し、Slackでの見せ方を決める
- 見せ方を変えるときは受信側だけを直す。送信側を配り直さない

受信側は別リポジトリ（`webhook_ts`、Neon Functions）で開発する。本編は送信側と受信側の共通の約束事とする。

## 2. 全体の構成

### 2.1 送り元

| 送り元 | `source` | 送る通知 |
|---|---|---|
| VPS（本番） | `kouun-vps` | ジョブ（収集、L1・L2、バックアップ）、定点報告 |
| 自宅サーバー（開発） | `kouun-home` | ジョブ（並行運用の間）、定点報告 |
| 将来：L3の日次計算 | 実装時に決める | ジョブ |
| 将来：アプリストアの確認ジョブ | 実装時に決める | レビュー |

`source`の値はホスト名ではなく、各サーバーの`.env.notify`で決める。VPSを作り直しても同じ名前を使い続けるため。

### 2.2 経路

```text
送信スクリプト（deploy/notify/kouun_notify.py など）
  ├→ journald（SYSLOG_IDENTIFIER=kouun-notify）   … 必ず記録する
  └→ Webhook（POST）
        → 受信側（Neon Functions）
             ├→ 受信側のDBへ記録
             └→ Slackへ表示
```

### 2.3 環境の区別

本番と開発は、送り先URLのパス（本番`/kouun_prd`、開発`/kouun_dev`）で分ける。受信側はパスごとに
トークンとSlackの送り先を持ち、表示に【本番】【開発】を付ける。URLの全体は計画書に記載しない。

### 2.4 送信の決まり

| 項目 | 仕様 |
|---|---|
| 方式 | `POST`、`Content-Type: application/json; charset=utf-8` |
| 認証 | `Authorization: Bearer <token>` |
| 送り先の制限 | `https`、またはループバック（`127.0.0.1`、`localhost`、`::1`）の`http`のみ。それ以外は送信せず警告を記録 |
| タイムアウト | 10秒 |
| 成功判定 | 2xx |
| 再送 | 行わない。送信失敗はjournaldへ警告として記録し、送信スクリプトは正常終了する |

## 3. version 2の形式

### 3.1 共通の項目

通知は1件ごとに1つのJSONオブジェクトとする。

| 項目 | 必須 | 型 | 内容 |
|---|---|---|---|
| `version` | 必須 | number | 形式の版。`2` |
| `kind` | 必須 | string | 通知の種類。4章の一覧のいずれか |
| `source` | 必須 | string | 送り元の名前（2.1） |
| `source_id` | 必須 | string | 送り元がその通知に振った番号 |
| `at` | 必須 | string | 出来事の日時。ISO 8601、`+09:00` |
| `level` | 必須 | string | 重要度。`info`、`warning`、`error` |
| `title` | 必須 | string | Slackの1行目に出す短い見出し |
| `details` | 必須 | object | 種類ごとの詳しいデータ（4章） |
| `url` | 任意 | string | 詳しく見る先へのリンク |
| `process_id` | 任意 | string | 1回の実行に付ける番号 |

任意の項目は、値がないときは項目自体を入れない。

### 3.2 項目名の注意

- `source_id`が重なってはいけないのは同じ`source`の中だけとする。受信側は`source`と`source_id`の
  組み合わせで通知を1件に特定し、重複して届いた通知を1件にまとめる。連番でもランダムな文字列でもよい
- `process_id`はLinuxのプロセスID（PID）ではない。1回の実行（開始から終了まで）に付ける番号で、
  同じ実行の開始通知と終了通知で同じ値になる。systemdのジョブでは`InvocationID`を入れる
- `details`の項目名と意味は4章で種類ごとに定める。受信側は`details`の中身に頼らなくても、共通の項目だけで
  記録と最低限の表示ができるようにする

### 3.3 levelの使い分け

| level | 使う場面 | Slackでの扱い（受信側の方針） |
|---|---|---|
| `info` | 正常な開始・終了、定点報告 | 通常の表示 |
| `warning` | 処理は終わったが注意が要る（一部の項目が読めない、放置された失敗unitがある等） | 目立たせる |
| `error` | 処理が失敗した | 最も目立たせる |

### 3.4 受信側の既定の表示

受信側が表示の仕方を知らない`kind`が届いた場合は、次のように表示する。

```text
【本番】<title>
<details の1段目の「項目名: 値」を数行>
<url があればリンク>
```

入れ子のオブジェクトや長い配列は省略してよい。見やすく整えたい種類は、受信側に種類ごとの表示を追加する。

## 4. 種類ごとの詳細

| `kind` | 内容 | 状態 |
|---|---|---|
| `job` | ジョブの開始・終了・失敗 | version 1から移す |
| `report` | 定期的な状況の報告 | version 1から移す |
| `review` | アプリストアの書き込み | 将来 |
| `alert` | データの異常の知らせ | 将来 |

種類を追加するときは、この表と該当の節を先に更新する。

### 4.1 job

対象：`collector`（収集）、`layers`（L1・L2更新）、`backup`（バックアップ）。将来はL3の日次計算も含める。

| `details`の項目 | 型 | 内容 |
|---|---|---|
| `job` | string | ジョブの名前 |
| `event` | string | `started`、`finished`、`failed` |
| `unit` | string | systemdのunit名 |
| `service_result` | string | systemdの判定（`success`、`exit-code`、`signal`、`timeout`、`oom-kill`等）。取得できない場合は`unknown`。startedでは項目なし |
| `exit_status` | number／null | 終了コード。startedでは項目なし |
| `summary` | object／null | ジョブのログの最終行がJSONオブジェクトの場合だけ入れる。startedでは項目なし |
| `log_tail` | string[]／null | failedのときログ末尾（最大20行、読めない場合は空の配列）。finishedはnull。startedでは項目なし |

| 共通の項目 | 決め方 |
|---|---|
| `level` | started・finishedは`info`、failedは`error` |
| `title` | ジョブの日本語名＋出来事。例：「収集 開始」「L1・L2更新 正常終了」「バックアップ 失敗」 |
| `process_id` | systemdの`InvocationID` |
| `source_id` | `<job>-<event>-<InvocationID>`。同じ通知を送り直しても同じ値になるようにする |

ジョブの日本語名：`collector`＝収集、`layers`＝L1・L2更新、`backup`＝バックアップ。

### 4.2 report

対象：`health`（サーバーの定点報告）。

| `details`の項目 | 型 | 内容 |
|---|---|---|
| `report` | string | 報告の名前。`health` |
| `status` | string | `succeeded`、または一部の項目が読めなかった場合`partial` |
| `memory` | object／null | 全体・使用中・利用可能・スワップ（MB） |
| `disk` | object／null | `/`の全体・使用・空き（GB）と使用率 |
| `database_bytes` | number／null | DBの大きさ |
| `raw_bytes` | number／null | `runtime/raw`の大きさ |
| `load` | object／null | 負荷の平均（1分、5分、15分） |
| `uptime_hours` | number／null | 稼働時間 |
| `containers` | object[]／null | コンテナごとのCPU・メモリ |
| `failed_units` | string[]／null | 失敗したまま残っているsystemdのunit |
| `errors` | string[] | 読めなかった項目と理由 |

読めなかった項目は0ではなく`null`とし、理由を`errors`に書く。

| 共通の項目 | 決め方 |
|---|---|
| `level` | 通常は`info`。`status`が`partial`、または`failed_units`が空でない場合は`warning` |
| `title` | 「定点報告」 |
| `process_id` | なし |
| `source_id` | `health-<日時>`（例：`health-20260929T0800`） |

### 4.3 review（将来）

アプリストアの書き込みを知らせる。ストア側に通知の仕組みがない場合は、確認用のジョブが定期的に
ストアのAPIを確認し、新しい書き込みを送る。`details`の項目は実装時に決める。`url`には返信できる画面を入れる。

### 4.4 alert（将来）

データの異常を知らせる。候補は[05_data_view.md](05_data_view.md)11.2のとおり。`details`の項目は実装時に
決める。`url`にはViewerの該当ページを入れる。

## 5. version 1からの移行

### 5.1 version 1の形式（現行）

2026-09-27から稼働している形式。ジョブの開始・終了・失敗だけを表す。

| 項目 | 型 | started | finished | failed |
|---|---|---|---|---|
| `version` | number | `1` | `1` | `1` |
| `event` | string | `started` | `finished` | `failed` |
| `job` | string | ○ | ○ | ○ |
| `unit` | string | ○ | ○ | ○ |
| `host` | string | ○ | ○ | ○ |
| `at` | string（ISO 8601、+09:00） | ○ | ○ | ○ |
| `invocation_id` | string／null | ○ | ○ | ○ |
| `service_result` | string | 項目なし | `success` | `success`以外 |
| `exit_status` | number／null | 項目なし | ○ | ○ |
| `summary` | object／null | 項目なし | ジョブの結果JSON | 結果JSONまたはnull |
| `log_tail` | string[]／null | 項目なし | null | ログ末尾（最大20行） |

定点報告は、version 2までの暫定として`job: "health"`、`event: "finished"`で送っている。

### 5.2 移行の手順

1. 受信側：version 1と2の両方を受け付ける。version 2は`source`と`source_id`で重複を見分ける
2. 自宅サーバー（開発）：`.env.notify`でversion 2へ切り替え、開発用のSlackで表示を確かめる
3. VPS（本番）：問題がなければversion 2へ切り替える
4. 両方がversion 2になった後、受信側のversion 1の受け付けを止める。時期は別に決める

### 5.3 .env.notifyの設定項目

`.env.notify`はgit管理外（権限600）とし、書き方は`deploy/notify/env.notify.example`に置く。

| 項目 | 内容 |
|---|---|
| `KOUUN_WEBHOOK_URL` | 送り先URL。空の場合はjournaldへの記録だけを行う |
| `KOUUN_WEBHOOK_TOKEN` | Bearerトークン |
| `KOUUN_NOTIFY_SOURCE` | `source`の値（`kouun-vps`、`kouun-home`）。version 2で追加 |
| `KOUUN_NOTIFY_VERSION` | 送る形式の版（`1`または`2`）。未設定は`1`。version 2で追加 |

## 6. 運用

### 6.1 確認のコマンド

```bash
journalctl -t kouun-notify --since today      # 通知の一覧
journalctl -t kouun-notify -p err             # エラー終了のみ
journalctl -t kouun-notify -p warning         # エラー終了とWebhook送信失敗
```

VPSでは`masuday`が`systemd-journal`グループに入っていないため、`sudo`を付ける。

### 6.2 送信に失敗したとき

- 再送しない。journaldの記録は残るので、必要なら`journalctl`で確認する
- 受信側が止まっている間に失われた通知は、受信側から見て「開始はあるが終了がない」状態になりうる。
  受信側は、この状態でも誤動作しないようにする

### 6.3 通知が来ないときの確認の順序

1. `systemctl list-timers 'kouun-*'`で、timerが有効で次の起動時刻があるか
2. `journalctl -t kouun-notify`で、送信側が通知を出したか。`webhook ...`の警告がないか
3. `.env.notify`のURLのパスに誤り（二重のスラッシュ等）がないか。404はパスの誤りを示す
4. 受信側のログと記録

### 6.4 送信側の実装上の注意

- `OnSuccess=`と`OnFailure=`に同じunitを書くと、systemdは`MONITOR_*`環境変数を渡さない
  （systemd 257で確認）。そのため通知処理は`systemctl show`でジョブのunitの
  `Result`・`InvocationID`・`ExecMainStatus`を直接読む
- ジョブのunitのログは`_SYSTEMD_INVOCATION_ID`で今回の実行分だけを取り出す。通知自身の行は
  `SYSLOG_IDENTIFIER=kouun-notify`で除外する
- 開始通知の失敗で本体が止まらないよう、`ExecStartPre`は先頭に`-`を付ける

## 7. 保留事項

| 項目 | 当面の扱い |
|---|---|
| version 1の受け付けを止める時期 | 両サーバーがversion 2へ移った後に決める |
| `review`・`alert`の`details`の項目 | 実装時に決め、4章を更新する |
| 送り元ごとのトークンの分離 | 当面は環境（本番・開発）ごとに1つ。送り元が増えた時点で検討する |
| 受信側でのlevelごとのSlackの送り先・メンション | 受信側の開発で決める |

## 8. 変更履歴

| 日付 | 版 | 内容 |
|---|---|---|
| 2026-09-28 | v0.1 | 新規作成。version 2の形式（共通の項目、種類、job・reportの詳細）と移行手順を定め、version 1の仕様とWebhook送信の決まりを02編から移した |
