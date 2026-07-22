# テストガイド（フロントエンド）

AI がテストコードを実装するときに読む最小限のガイド。何をどこまでテストするかの方針はリポジトリルートの `AGENTS.md`「テスト方針」を参照。ここにはフロントエンド固有の実装情報だけを書く。

## テスト環境

- Vitest（`globals` 有効、happy-dom）+ @testing-library/react + @testing-library/user-event
- jest-dom のマッチャーは `src/test/setup.ts` で読み込み済み
- 実行は `src/web` で `pnpm test`

## テストの書き方

- テストファイルはテスト対象と同じディレクトリに `*.test.ts` / `*.test.tsx` として置く
- テストデータは `src/test/factories.ts` のファクトリ（`createHolding` など）を使い、必要なフィールドだけ overrides で上書きする
- コンポーネントはデータを props で渡して render する（API 呼び出しのモックはしない設計）
- ルーティングに依存するコンポーネントは `MemoryRouter` で包んで render する

## テストを書かない対象

- `lib/api/client.ts`: 外部 API 呼び出しが中心でほぼモックになるため価値が薄い
- `components/ui/` の shadcn/ui コンポーネント: ライブラリ側でテスト済み
- Recharts のグラフ描画そのもの: データ加工ロジック（`filterDataByTimeFrame` など）のテストでカバーする
