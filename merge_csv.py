import os
import pandas as pd

# アーティファクトがダウンロードされたディレクトリ
data_dir = "merged_data"

# すべてのCSVファイルを取得
csv_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith(".csv")]

# CSVをマージ
dfs = [pd.read_csv(f) for f in csv_files]
merged_df = pd.concat(dfs, ignore_index=True)

# 重複を削除（必要なら）
merged_df.drop_duplicates(subset=["URL"], keep="last", inplace=True)

# 統合データを保存
merged_df.to_csv("final_data.csv", index=False, encoding="utf-8-sig")

print(f"統合されたCSVファイルが {len(merged_df)} 件のデータを含んでいます。")