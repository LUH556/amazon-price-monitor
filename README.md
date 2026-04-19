# Amazon Price Monitor — セットアップマニュアル

---

## 全体の流れ

```
1. GitHubアカウント作成・リポジトリ作成
2. ファイル一式をアップロード
3. GitHub Pages を有効化（ダッシュボード公開）
4. Gmailアプリパスワード取得
5. GitHub Secrets に認証情報を登録
6. 監視商品を products.json に登録
7. 動作確認（手動実行）
```

---

## STEP 1：GitHubアカウント・リポジトリ作成

### 1-1. GitHubアカウント（未作成の場合）

1. https://github.com にアクセス
2. 「Sign up」からアカウントを作成
3. 無料プランで問題なし

### 1-2. リポジトリ作成

1. ログイン後、右上の「+」→「New repository」
2. 設定内容：

| 項目 | 設定値 |
|------|--------|
| Repository name | `amazon-price-monitor`（任意） |
| Visibility | **Public**（GitHub Pages無料枠の条件） |
| Add a README | チェックしない |

3. 「Create repository」をクリック

---

## STEP 2：ファイルのアップロード

リポジトリの画面で「uploading an existing file」をクリックし、  
以下の構成になるようにファイルをアップロードします。

```
amazon-price-monitor/
├── .github/
│   └── workflows/
│       └── check_prices.yml
├── docs/
│   ├── index.html
│   └── data/
│       ├── products.json
│       └── price_history.json
└── scripts/
    └── check_prices.py
```

> **注意**：`.github/workflows/` フォルダは隠しフォルダのため、  
> GitHubのWebUIではフォルダごとドラッグ＆ドロップで作成します。

### コマンドラインが使える場合（より確実）

```bash
git clone https://github.com/あなたのユーザー名/amazon-price-monitor.git
cd amazon-price-monitor
# ファイルを配置してから
git add .
git commit -m "initial setup"
git push
```

---

## STEP 3：GitHub Pages の有効化

1. リポジトリの「Settings」タブ
2. 左サイドバー「Pages」
3. Source セクション：

| 項目 | 設定値 |
|------|--------|
| Source | **Deploy from a branch** |
| Branch | **main** |
| Folder | **/ docs** |

4. 「Save」をクリック
5. 数分後、`https://あなたのユーザー名.github.io/amazon-price-monitor/` でアクセス可能になる

---

## STEP 4：Gmail アプリパスワードの取得

> 通常のGmailパスワードではなく、アプリ専用のパスワードが必要です。

### 前提：Googleアカウントの2段階認証が有効であること

1. https://myaccount.google.com にアクセス
2. 「セキュリティ」→「2段階認証プロセス」が「オン」になっているか確認  
   （オフの場合は有効化してください）

### アプリパスワードの発行

1. https://myaccount.google.com/apppasswords にアクセス
2. 「アプリを選択」→「その他（名前を入力）」
3. 名前：`amazon-price-monitor`（任意）
4. 「生成」をクリック
5. 表示された **16桁のパスワード**（スペース4つで区切られた形式）をコピー

   > 例：`abcd efgh ijkl mnop`  
   > → スペースを除いた `abcdefghijklmnop` をそのまま使用します

6. このパスワードは**この画面でしか表示されない**ためメモしておく

---

## STEP 5：GitHub Secrets への登録

1. リポジトリの「Settings」→「Secrets and variables」→「Actions」
2. 「New repository secret」で以下の3つを登録：

| Secret名 | 値 |
|---|---|
| `GMAIL_USER` | Gmailアドレス（例：yourname@gmail.com） |
| `GMAIL_APP_PASSWORD` | STEP 4 で取得した16桁パスワード（スペースなし） |
| `NOTIFY_EMAIL` | 通知の送付先メールアドレス（同じGmailでも可） |

---

## STEP 6：監視商品の登録

`docs/data/products.json` を編集して商品を追加します。

### ASINの調べ方

AmazonのURLに含まれる10桁の英数字がASINです。

```
https://www.amazon.co.jp/dp/B0XXXXXXXX/
                              ^^^^^^^^^^
                              これがASIN
```

### products.json の書き方

```json
[
  {
    "asin": "B0XXXXXXXX",
    "name": "エナジードリンク 24本入",
    "target_price": 3500,
    "memo": "定期購入より安い時に買う"
  },
  {
    "asin": "B0YYYYYYYY",
    "name": "コーヒー豆 1kg",
    "target_price": 2800,
    "memo": ""
  }
]
```

| フィールド | 必須 | 説明 |
|---|---|---|
| `asin` | ✅ | Amazon商品ID |
| `name` | ✅ | 管理用の商品名 |
| `target_price` | ✅ | この金額以下になったらメール通知（送料込み合計） |
| `memo` | 任意 | 自分用メモ |

> **送料について**  
> `target_price` は **送料込み合計**で判定されます。  
> たとえば本体¥3,600＋送料¥350＝合計¥3,950のとき、  
> `target_price: 4000` なら通知が送られます。

### 商品の削除

該当の `{ ... }` ブロックをまるごと削除するだけです。  
price_history.json のデータはそのまま残ります（不要なら手動削除）。

---

## STEP 7：動作確認（手動実行）

1. リポジトリの「Actions」タブ
2. 左サイドバー「Amazon Price Monitor」
3. 「Run workflow」→「Run workflow」

数分後：

- 「Actions」画面でジョブが緑色（✅）になれば成功
- `docs/data/price_history.json` が更新されていることを確認
- 目標価格以下の商品があればメールが届く

---

## 定期実行のスケジュール

デフォルト設定では **毎日JST 10:00** に自動実行されます。  
変更したい場合は `.github/workflows/check_prices.yml` の以下の行を編集：

```yaml
- cron: "0 1 * * *"   # UTC 01:00 = JST 10:00
```

### cron の書き方（UTC基準）

| JST | UTC cron |
|-----|----------|
| 毎日 7:00 | `0 22 * * *` |
| 毎日 10:00 | `0 1 * * *` |
| 毎日 20:00 | `0 11 * * *` |
| 毎日2回（9:00と21:00） | `0 0,12 * * *` |

---

## ダッシュボードの見方

```
┌─────────────────────────────────────────┐
│ PRICE/MONITOR          LAST CHECK: date │
├──────────┬──────────┬──────────┬────────┤
│ MONITOR  │ ALERTS   │ AVG DISC │ POINTS │
│ 5        │ 1        │ -8%      │ 42     │
├──────────────────────────────────────────┤
│ 商品名                        [→ AMAZON]│
│ ASIN: XXXXXXXXXX                        │
├──────────┬──────────┬──────────┬────────┤
│ 現在価格  │ 過去最安  │ 過去最高 │ 目標  │
│ ¥3,500   │ ¥3,200   │ ¥4,200  │¥3,800 │
├──────────────────────────────────────────┤
│ [価格推移グラフ]                         │
└──────────────────────────────────────────┘
```

- **⚠ ALERT** バッジ：現在価格が目標価格以下の商品に表示
- **→ AMAZON** ボタン：Amazonの商品ページをブラウザで開く
- **過去最安**：記録開始以降の最安値

---

## 注意事項

### プライバシー
- `docs/data/` 以下のファイルはGitHub Pagesを通じて**全世界に公開**されます
- ASINや購入検討商品が外部から閲覧可能であることを認識したうえで使用してください
- プライベートリポジトリ＋GitHub Pages（Pro以上）にすれば非公開にできます

### 価格取得について
- Amazonのページ構造変更により、価格が取得できなくなる場合があります
- Actionsのログで `[WARN] Price element not found` と表示される場合は  
  `scripts/check_prices.py` のセレクタを調整してください

### GitHub Actions の無料枠
- 無料プランでは月2,000分のActions実行時間が付与されます
- 1回の実行で商品5件程度なら約2〜3分、10件でも5分以内に収まります
- 毎日1回実行の場合：月30回×3分 = 90分 → 無料枠内に十分収まります

---

## トラブルシューティング

| 症状 | 確認事項 |
|------|---------|
| Actions が失敗する | Secretsの設定名にタイポがないか確認 |
| 価格が取得できない | Actionsログを確認、セレクタの更新が必要な可能性 |
| メールが届かない | アプリパスワードのスペース除去、2段階認証の確認 |
| ダッシュボードが空 | GitHub Pagesの設定でdocsフォルダが選択されているか確認 |
| グラフが出ない | 記録2日分以上蓄積されてから表示されます |

---

*最終更新: 2026-04*
