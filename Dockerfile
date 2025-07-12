# ベースとなるPythonの環境を指定
FROM python:3.10-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なライブラリのリストをコンテナにコピー
COPY requirements.txt .

# ライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# BOTのプログラムと設定ファイルをコンテナにコピー
COPY . .

# コンテナが起動したときに実行されるコマンド
CMD ["python", "main.py"]