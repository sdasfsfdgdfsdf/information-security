import pandas as pd
import numpy as np
import argparse
from sklearn.feature_selection import mutual_info_classif

def select_top_features(input_csv, output_csv, top_k=15, seed=42):
    """
    基于互信息选择 top_k 个特征，保存精简后的 CSV。
    """
    df = pd.read_csv(input_csv)
    # 假设最后一列为标签
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]

    # 计算互信息（离散特征需要设置 discrete_features 参数？continuous 自动处理）
    mi_scores = mutual_info_classif(X, y, random_state=seed)
    mi_series = pd.Series(mi_scores, index=X.columns).sort_values(ascending=False)

    print("=== 特征互信息得分（从高到低） ===")
    for feat, score in mi_series.items():
        print(f"  {feat}: {score:.6f}")

    # 选取前 top_k 特征
    selected_features = mi_series.head(top_k).index.tolist()
    print(f"\n选取的 {top_k} 个特征：{selected_features}")

    # 构建新 DataFrame（只保留选中特征 + 标签）
    new_df = df[selected_features + [df.columns[-1]]]
    new_df.to_csv(output_csv, index=False)
    print(f"精简后数据已保存至: {output_csv}")
    return selected_features, mi_series

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="基于互信息的特征选择，精简 CSV 文件")
    parser.add_argument("input", help="输入 CSV 文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出 CSV 文件路径（默认：输入名_selected.csv）")
    parser.add_argument("-k", type=int, default=15, help="保留的特征数量 (默认 15)")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    args = parser.parse_args()

    if args.output is None:
        base = args.input.rsplit('.', 1)[0]
        args.output = f"{base}_selected.csv"

    select_top_features(args.input, args.output, top_k=args.k, seed=args.seed)