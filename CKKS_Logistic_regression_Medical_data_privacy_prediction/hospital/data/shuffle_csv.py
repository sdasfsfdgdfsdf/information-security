import argparse
import pandas as pd
import numpy as np

def shuffle_csv(input_path, output_path=None, seed=None, keep_header=True):
    """
    将 CSV 文件的行顺序随机打乱。
    input_path:  输入 CSV 文件路径
    output_path: 输出 CSV 文件路径（若为 None，则覆盖原文件）
    seed:        随机种子（用于复现，可选）
    keep_header: 是否保留表头（默认 True）
    """
    df = pd.read_csv(input_path)
    if seed is not None:
        np.random.seed(seed)
    df_shuffled = df.sample(frac=1).reset_index(drop=True)
    out = output_path if output_path else input_path
    df_shuffled.to_csv(out, index=False)
    print(f"已打乱行顺序，输出至: {out}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="随机打乱 CSV 文件的行顺序")
    parser.add_argument("input", help="输入 CSV 文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出文件路径（默认覆盖输入文件）")
    parser.add_argument("--seed", type=int, default=None, help="随机种子（可选）")
    parser.add_argument("--no-header", action="store_true", help="输入文件无标题行")
    args = parser.parse_args()

    shuffle_csv(args.input, args.output, args.seed, not args.no_header)