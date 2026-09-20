# 開発計画書の目次

版：v0.5／2026-09-14

1. [全体編](01_overall.md)
2. [前半・データ収集編](02_data_collection.md)
3. [中盤・データ分析編](03_data_analysis.md)
4. [後半・アプリ構築編](04_application.md)

この４編が現時点の設計基準です。全体編とデータ収集編はv0.5、その他の編はv0.3です。計画上の暫定仕様と、ユーザーが指定した条件を区別してください。

## フォルダ構成
kouun_db/
├── compose.yaml
├── .env.example
├── .gitignore
├── docker/
│   └── python/
├── db/
│   └── migrations/
├── src/
│   ├── collector/
│   └── analyzer/
├── tests/
└── runtime/
    ├── postgres/
    ├── raw/
    └── logs/
