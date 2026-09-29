# 実行用のサービスアカウントを分ける（2026-09-29）

`docs/260927-ideas.md` の CI/CD の改善の続き。クラウドのセッション（リポジトリの変更）と、ローカルのセッション（GCP の操作）で分担するため、手順と決めたことをここに書く。

## 今の状態（2026-09-29 にローカルのセッションが調べた）

- プロジェクト：`gen-lang-client-0069633622`（番号 `1048841098952`）、リージョン `asia-northeast1`
- 既定のサービスアカウント `1048841098952-compute@developer.gserviceaccount.com`（以下「ビルド用」）が、次のすべてで使われている
  - Cloud Build のビルドとデプロイ
  - Cloud Run のサービス 5 つ（`trail-info`、`trail-info-develop`、`main-build-notifier`、`ga4-send-report`、`awaken-supabase-dev-environment`）
  - Cloud Run のジョブ 6 つ（`trail-info-{main,develop}-{migrate,run-sync,run-blog-sync}`）
  - 例外：`backup-db-main` と `develop-db-backup` は `db-backup@…` で動く
- ビルド用のロール（プロジェクト全体）：`artifactregistry.writer`、`cloudbuild.builds.builder`、`developerconnect.readTokenAccessor`、`iam.serviceAccountUser`、`logging.logWriter`、`run.admin`、`run.developer`、`run.servicesInvoker`、`run.sourceDeveloper`、`secretmanager.secretAccessor`（`roles/editor` はない）

### 問題

アプリ（インターネットからのリクエストを受ける）が、ビルド用と同じアカウントで動いている。アプリが乗っ取られると、コンテナの中からメタデータサーバーでこのアカウントのトークンを取り、次のことができる。

- プロジェクトのシークレットをすべて読む（`secretmanager.secretAccessor`）
- 本番の `trail-info` を別のイメージに差し替える（`run.admin`、`artifactregistry.writer`）
- 任意のサービスアカウントとして動く Cloud Run のサービスやジョブを作り、そのアカウントの権限を使う（`iam.serviceAccountUser` がプロジェクト全体、`run.admin`）

## 方針

インターネットの前に立つ実行用のアカウントには、自分が使うシークレットを読む権限だけを持たせる。ビルド用は、デプロイの権限と、実行用のアカウントを指定してデプロイする権限（`iam.serviceAccountUser` を実行用のアカウントに対してだけ）を持つ。

### 実行用のアカウント

| アカウント | 使うもの | 読めるシークレット |
|---|---|---|
| `trail-info-web-main` | サービス `trail-info`、ジョブ `trail-info-main-migrate` | 本番の `DJANGO_SECRET_KEY`、`DATABASE_URL` |
| `trail-info-web-develop` | サービス `trail-info-develop`、ジョブ `trail-info-develop-migrate` | ステージングの `DJANGO_SECRET_KEY`、`DATABASE_URL` |
| `trail-info-batch-main` | ジョブ `trail-info-main-run-sync`、`trail-info-main-run-blog-sync` | 本番の `DJANGO_SECRET_KEY`、`DATABASE_URL`、`GEMINI_API_KEY`、`LANGSMITH_API_KEY`、`SLACK_WEBHOOK_URL`、`EMAIL_PASSWORD_NOREPLY` |
| `trail-info-batch-develop` | ジョブ `trail-info-develop-run-sync`、`trail-info-develop-run-blog-sync` | ステージングの `DJANGO_SECRET_KEY`、`DATABASE_URL`、`GEMINI_API_KEY`、`LANGSMITH_API_KEY`、`SLACK_WEBHOOK_URL`、`EMAIL_PASSWORD_NOREPLY` |

- シークレットの一覧は `cloudbuild.*.yaml` の `--set-secrets` から取った。run-blog-sync は `GEMINI_API_KEY` と `LANGSMITH_API_KEY` を使わないが、run-sync と同じアカウントにする。
- アプリのコードで GCP の API を使うのは `backup_db`（Cloud Storage）だけで、これは `db-backup@…` で動くため対象外。ログは標準出力に出し、Cloud Run が集めるので、ログ用のロールはいらない。
- `DJANGO_SECRET_KEY` と `DATABASE_URL` のシークレット名は、Cloud Build のトリガーの置き換え変数 `_DJANGO_SECRET_KEY` / `_DATABASE_URL` で渡しており、リポジトリにはない。手順 0 で確かめる。
- ロールはシークレットごとにつける（プロジェクト全体にはつけない）。

## 決めたこと（2026-09-29、オーナー）

1. **アカウントの分け方：案 A（4 つ）にする**
   - 案 A（推奨）：環境 × 役割で 4 つ（上の表）。ステージングが乗っ取られても、本番の `DATABASE_URL` と `DJANGO_SECRET_KEY` は読めない。`cloudbuild` では `trail-info-web-${_BRANCH_NAME}` のように本番とステージングで同じ書き方にできる。
   - 案 B：役割だけで 2 つ（`trail-info-web`、`trail-info-batch`）。ステージングから本番のシークレットが読める。
2. **本番とステージングで共通のシークレットは分けない**：`GEMINI_API_KEY`、`LANGSMITH_API_KEY`、`SLACK_WEBHOOK_URL`、`EMAIL_PASSWORD_NOREPLY` は、本番とステージングで同じシークレットを使っている。案 A でも、ステージングのジョブからこの 4 つは読める。ステージング用に別のキーとシークレットは作らない。

## 手順

| # | 内容 | 誰が |
|---|---|---|
| 0 | トリガーの置き換え変数を確かめる | ローカル |
| 1 | 実行用のアカウントを作る | ローカル（オーナーの確認のあと） |
| 2 | シークレットごとに読み取りをつける | ローカル（オーナーの確認のあと） |
| 3 | ビルド用に、実行用のアカウントへの `iam.serviceAccountUser` をつける | ローカル（オーナーの確認のあと） |
| 4 | `cloudbuild.*.yaml` に `--service-account` を足す（PR） | クラウド |
| 5 | ステージングで試す（`develop` に push、ジョブを手動で実行） | クラウド・オーナー |
| 6 | マージして本番にリリースする | オーナー |
| 7 | 後片づけ（別の作業） | 未定 |

### 0. トリガーの置き換え変数を確かめる（読むだけ）

```bash
gcloud builds triggers list --region=asia-northeast1 \
  --format="table(name, substitutions)"
gcloud secrets list --format="value(name)"
```

本番とステージングのトリガーそれぞれについて、`_SERVICE_NAME`、`_DJANGO_SECRET_KEY`、`_DATABASE_URL`（と本番の `_BRANCH_NAME`）の値を、この文書の「確かめた結果」に書く。値はシークレットの名前であり中身ではないが、リポジトリは公開なので、書いてよいかはオーナーに確認する。

### 1〜3. アカウントを作り、権限をつける

```bash
PROJECT=gen-lang-client-0069633622
BUILD_SA=1048841098952-compute@developer.gserviceaccount.com

for env in main develop; do
  for role in web batch; do
    gcloud iam service-accounts create "trail-info-${role}-${env}" \
      --project="$PROJECT" --display-name="trail-info ${role} (${env})"
  done
done

# 2. シークレットごとに読み取りをつける（<...> は手順 0 で確かめた名前）
grant() {  # grant <シークレット名> <アカウント名>
  gcloud secrets add-iam-policy-binding "$1" --project="$PROJECT" \
    --member="serviceAccount:$2@${PROJECT}.iam.gserviceaccount.com" \
    --role=roles/secretmanager.secretAccessor
}
for sa in trail-info-web-main trail-info-batch-main; do
  grant <本番の DJANGO_SECRET_KEY> "$sa"
  grant <本番の DATABASE_URL> "$sa"
done
for sa in trail-info-web-develop trail-info-batch-develop; do
  grant <ステージングの DJANGO_SECRET_KEY> "$sa"
  grant <ステージングの DATABASE_URL> "$sa"
done
for sa in trail-info-batch-main trail-info-batch-develop; do
  for s in GEMINI_API_KEY LANGSMITH_API_KEY SLACK_WEBHOOK_URL EMAIL_PASSWORD_NOREPLY; do
    grant "$s" "$sa"
  done
done

# 3. ビルド用が、実行用のアカウントを指定してデプロイできるようにする
for env in main develop; do
  for role in web batch; do
    gcloud iam service-accounts add-iam-policy-binding \
      "trail-info-${role}-${env}@${PROJECT}.iam.gserviceaccount.com" \
      --project="$PROJECT" \
      --member="serviceAccount:${BUILD_SA}" --role=roles/iam.serviceAccountUser
  done
done
```

- 手順 3 は、ビルド用がプロジェクト全体の `iam.serviceAccountUser` を持っている今は、なくても動く。手順 7 でプロジェクト全体のものを外すときのために、先につけておく。
- 手順 1〜3 だけでは、動いているサービスとジョブは何も変わらない（まだビルド用で動いている）。

### 4. `cloudbuild` の変更

- サービス（`deploy-service`）と migrate ジョブ：`--service-account=trail-info-web-<env>@$PROJECT_ID.iam.gserviceaccount.com`
- run-sync / run-blog-sync ジョブ：`--service-account=trail-info-batch-<env>@$PROJECT_ID.iam.gserviceaccount.com`
- `<env>` は、本番が `$_BRANCH_NAME`、ステージングが `$BRANCH_NAME`（イメージ名と同じ）。手順 0 で本番の `_BRANCH_NAME` が `main` であることを確かめる。

### 5. ステージングで確かめること

- ビルドとデプロイが成功し、`check-service` が 200 を確かめる（サービスがシークレットを読めている）
- ジョブ `trail-info-develop-run-sync` と `trail-info-develop-run-blog-sync` を手動で実行し、成功する
- `gcloud run services describe trail-info-develop --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)"` が `trail-info-web-develop@…` になっている（ジョブも同じように確かめる）

### 戻し方

`--service-account` を消して再デプロイしても、Cloud Run は前のアカウントのままになる。戻すときは、`--service-account=1048841098952-compute@developer.gserviceaccount.com` を指定してデプロイする。

### 7. 後片づけ（別の作業として決める）

- ビルド用のプロジェクト全体の `iam.serviceAccountUser` を外し、必要なアカウントにだけつけ直す。ビルド用は `main-build-notifier` などほかのサービスの実行にも使われているため、ビルド用自身への `iam.serviceAccountUser` が要るかを含めて調べる。
- ビルド用の `run.developer` は `run.admin` に含まれるため外せる。
- ビルド用のプロジェクト全体の `secretmanager.secretAccessor` は、ほかのサービスが使うシークレットを調べてから、シークレットごとに置き換える。

## 確かめた結果

（手順 0 以降の結果をここに書く）
