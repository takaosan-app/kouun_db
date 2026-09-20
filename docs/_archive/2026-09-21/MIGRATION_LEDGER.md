# 文書再編の移送台帳

作成日：2026-09-21  
対象：2026-09-21の文書再編（案C＝章ごとに配分）で、どの記述をどこへ移したかの記録。

再編前の原本は同じフォルダに凍結してある。記述の行方を追う場合は原本を grep して、
下表の行き先を確認する。

| 移送元 | 節 | 行き先 | 判断理由 |
|---|---|---|---|
| ANALYZE.md | 0. 本改訂の概要 | （破棄） | 改訂差分の説明。統合後は意味を失う。要点は各編の変更履歴へ |
| ANALYZE.md | 1. 目的 | 03_data_analysis.md 1章 | 作物別分析の目的として基本方針へ統合 |
| ANALYZE.md | 2.1 計算はサーバーで行う | 01_overall.md | 構成上の基本判断 |
| ANALYZE.md | 2.2 四層構造 | 01_overall.md | L0-L3は全体像 |
| ANALYZE.md | 2.3 L2に置く指標 | 03_data_analysis.md | 分析仕様 |
| ANALYZE.md | 2.4 累積和にできないもの | 03_data_analysis.md | 分析仕様 |
| ANALYZE.md | 2.5 差分更新 | 03_data_analysis.md | 分析仕様 |
| ANALYZE.md | 2.6 配置方針 | 01_overall.md | 全体構成 |
| ANALYZE.md | 2.7 データ量の方針 | 02_data_collection.md | 容量・保持年数は収集運用の領域 |
| ANALYZE.md | 3. 気象データソース | 02_data_collection.md | 取得元・費用・制約 |
| ANALYZE.md | 4.1 要素ごとに参照先が異なる | 03_data_analysis.md | 近隣観測所の選定へ統合 |
| ANALYZE.md | 4.2 参照条件の表示 / 4.3 気温オフセット | 06_application.md | 表示仕様 |
| ANALYZE.md | 5. 降水の扱い | 03_data_analysis.md | 判定方針 |
| ANALYZE.md | 6. 圃場単位の状態管理 | 04_cultivation_state.md | CULTIVATION_STATEと重複。統合 |
| ANALYZE.md | 7.1-7.3 日誌を主入力とする | 04_cultivation_state.md | 記録設計の思想 |
| ANALYZE.md | 7.4-7.5 イベント登録・初回入力 | 04_cultivation_state.md | 入力仕様 |
| ANALYZE.md | 8. いちご | 03_data_analysis.md | L3の中核 |
| ANALYZE.md | 9. 水稲 | 03_data_analysis.md | L3の中核 |
| ANALYZE.md | 10. リスク判定の考え方 | 03_data_analysis.md | 10.1欠測の扱いは欠測・品質の章へ |
| ANALYZE.md | 11. 通知設計 | 06_application.md | アプリ仕様 |
| ANALYZE.md | 12. 画面構想 | 06_application.md | アプリ仕様 |
| ANALYZE.md | 13. データモデルの方向性 | 03 と 04 に分割 | L1/L2/risk_ruleは03、farm/field/diaryは04 |
| ANALYZE.md | 14. 根拠資料の扱い | 03_data_analysis.md | 判定根拠の管理 |
| ANALYZE.md | 15. 法規制上の留意点 | BUSINESS.md | 事業判断 |
| ANALYZE.md | 16. 事業性の前提 | BUSINESS.md | 事業判断 |
| ANALYZE.md | 17. 確認中の事項 | BUSINESS.md | 外部窓口への確認。02から参照 |
| ANALYZE.md | 18. 未確定事項 | 各編の保留事項へ分配 |  |
| ANALYZE.md | 19. 次の進め方 | STATUS_PLAN.md | 進捗管理の領域 |
| CULTIVATION_STATE.md | 全1-14章 | 04_cultivation_state.md | 改名。ANALYZE 6・7章を受け入れ |
| plans/01_overall.md | 全1-8章 | docs/plans/01_overall.md | 移動。ANALYZE 2章の一部を受け入れ |
| plans/02_data_collection.md | 全1-11章 | docs/plans/02_data_collection.md | 移動。ANALYZE 2.7・3章を受け入れ |
| plans/03_data_analysis.md | 全1-12章 | docs/plans/03_data_analysis.md | 移動。ANALYZEの分析部分を受け入れ |
| plans/04_application.md | 全1-12章 | docs/plans/06_application.md | 改番。ANALYZE 4.2・11・12章を受け入れ |
| plans/05_data_view.md | 全章 | docs/plans/05_data_view.md | 移動のみ |
| plans/README.md | 目次 | docs/plans/README.md | 目次を6編＋BUSINESSへ更新 |
| AGENTS.md | 全章 | /AGENTS.md | リポジトリ直下へ移動。参照パス修正 |
| STATUS_PLAN.md | 全1-6章 | docs/STATUS_PLAN.md | 据え置き。正本指定と参照パスを修正 |
