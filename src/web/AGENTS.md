# フロントエンド (src/web)

React + Vite ベースのSPAです。Vercelでデプロイされています。

## 実装手順

1. 実装計画を立てる。セッション内ですでにプランニングが終わっている場合は不要
2. コードを実装する
3. `pnpm install` で依存関係を更新する
4. web-test-creatorスキルを使ってテストコードを実装する
5. `pnpm check` を実行し、lint/format/typecheck/knipが通ることを確認する
6. `pnpm test`でテストを実行する
7. ドキュメント(AGENTS.md, README.md)を更新する
8. コミットする

## 実装の指針

- バックエンドAPIを呼び出す必要が出たときはsrc/apiを参照して仕様を確認する。
- パッケージを追加するときはadd-npm-packageスキルを利用すること

## コマンド

**注意**: 以下のコマンドは `src/web` ディレクトリで実行する必要があります。

```bash
# 開発サーバーの起動
pnpm dev

# ビルド
pnpm build

# 型チェック、リンティング、フォーマット、依存関係チェック
pnpm check

# テスト実行
# （web-test-creatorスキルを使用することを推奨）

# プレビュー（ビルド後）
pnpm preview
```

**環境変数:**

- `VITE_API_URL`: バックエンドAPIのベースURL
  - ローカル: `http://localhost:8000`
  - `.env.local`で設定

## 技術スタック

- **Vite 6 + React 19 + TypeScript**: コア技術
- **React Router 7**: ルーティング
- **Tailwind CSS 4 + shadcn/ui**: スタイリング
- **SWR**: データフェッチング
- **Zustand**: グローバル状態管理（認証のみ）
- **Recharts**: グラフ描画
- **React Hook Form + Zod**: フォーム管理

## ディレクトリ構造

```
src/web/src/
├── main.tsx                    # エントリーポイント
├── App.tsx                     # ルーター設定
├── routes/                     # ページコンポーネント
├── components/                 # UIコンポーネント
│   ├── layout/                 # レイアウト（サイドバー、ナビなど）
│   ├── dashboard/              # ダッシュボード関連
│   └── ui/                     # shadcn/uiコンポーネント
└── lib/
    ├── api/                    # APIクライアント
    ├── stores/                 # Zustandストア
    └── format.ts               # フォーマット関数
```

## ルーティング

| パス | ページ | 説明 |
|------|--------|------|
| `/` | ダッシュボード | サマリーカード、資産推移、月次取引、月次配当 |
| `/holdings` | 保有状況 | 銘柄別保有状況テーブル |
| `/holdings/:symbol` | 銘柄詳細 | 保有サマリ、株価グラフ（投資信託除く）、取引履歴、配当履歴 |
| `/login` | ログイン | ログインページ |
