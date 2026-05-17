import os
import argparse
import pandas as pd
import numpy as np

def split_single(csv_path, test_ratio=0.2, random_seed=42, train_dir="train_data", test_dir="test_data"):
    """
    处理单个 CSV 文件：
        - 训练集保存至 train_dir，文件名与原文件相同（不带前缀）
        - 测试集特征保存至 test_dir/{basename}_test_X.csv
        - 测试集标签保存至 test_dir/{basename}_test_y.csv
    """
    df = pd.read_csv(csv_path)
    total = len(df)
    print(f"处理: {csv_path} ({total} 条)")

    # 随机打乱
    df_shuffled = df.sample(frac=1, random_state=random_seed).reset_index(drop=True)

    # 划分
    split_idx = int(total * (1 - test_ratio))
    train_df = df_shuffled.iloc[:split_idx]
    test_df = df_shuffled.iloc[split_idx:]

    # 测试集分离标签
    label_col = df.columns[-1]
    test_X = test_df.drop(columns=[label_col])
    test_y = test_df[label_col]

    # 创建输出目录
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)

    base = os.path.basename(csv_path)  # 包含扩展名，如 heart.csv
    # 训练集：直接以原文件名保存
    train_path = os.path.join(train_dir, base)
    train_df.to_csv(train_path, index=False)

    # 测试集
    stem = os.path.splitext(base)[0]  # heart
    test_X_path = os.path.join(test_dir, f"{stem}.csv")
    test_y_path = os.path.join(test_dir, f"{stem}_y.csv")

    test_X.to_csv(test_X_path, index=False)
    test_y.to_csv(test_y_path, index=False, header=True)

    print(f"  训练集 -> {train_path} ({len(train_df)} 条)")
    print(f"  测试特征 -> {test_X_path} ({len(test_X)} 条)")
    print(f"  测试标签 -> {test_y_path} ({len(test_y)} 条)")

    return train_path, test_X_path, test_y_path

def main():
    parser = argparse.ArgumentParser(description="批量划分 data 文件夹下所有 CSV 文件")
    parser.add_argument("--data_dir", default=".", help="原始 CSV 所在目录 (默认 data)")
    parser.add_argument("--train_dir", default="train_data", help="训练集输出目录 (默认 train_data)")
    parser.add_argument("--test_dir", default="test_data", help="测试集输出目录 (默认 test_data)")
    parser.add_argument("--test_ratio", type=float, default=0.2, help="测试集比例 (默认 0.2)")
    parser.add_argument("--seed", type=int, default=42, help="随机种子 (默认 42)")
    args = parser.parse_args()

    csv_files = [f for f in os.listdir(args.data_dir) if f.endswith('.csv')]
    if not csv_files:
        print(f"在 '{args.data_dir}' 中未找到任何 CSV 文件。")
        return

    print(f"找到 {len(csv_files)} 个 CSV 文件：{csv_files}\n")

    for file in csv_files:
        full_path = os.path.join(args.data_dir, file)
        split_single(full_path, args.test_ratio, args.seed, args.train_dir, args.test_dir)
        print("-" * 50)

    print("全部完成。")

if __name__ == "__main__":
    main()