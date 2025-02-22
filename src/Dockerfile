# 公式のPostgreSQLイメージを使用
FROM postgres:15-alpine

# 環境変数を設定
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=hogehoge
ENV POSTGRES_DB=investlogix

# 永続化ボリュームのマウントポイントを指定
VOLUME ["/var/lib/postgresql/data"]

# PostgreSQLのデフォルトポートを公開
EXPOSE 5432

# コンテナ起動時にPostgreSQLサーバーを開始
CMD ["postgres"]