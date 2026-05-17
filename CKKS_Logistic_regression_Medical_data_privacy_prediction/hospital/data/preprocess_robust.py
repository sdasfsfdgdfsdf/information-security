import pandas as pd
import numpy as np
from sklearn.preprocessing import RobustScaler
import argparse
import json
import os

def robust_scale_csv(input_csv, output_csv, params_path=None):
    """
    对 CSV 文件的特征列进行 RobustScaler 缩放，标签列保持不变。
    生成缩放后的 CSV 文件以及缩放参数 JSON (center/scale)。
    """
    df = pd.read_csv(input_csv)
    X = df.iloc[:, :-1].values.astype(float)
    y = df.iloc[:, -1]
    feature_names = df.columns[:-1].tolist()
    label_name = df.columns[-1]

    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    # 构建缩放后的 DataFrame
    df_scaled = pd.DataFrame(X_scaled, columns=feature_names)
    df_scaled[label_name] = y.values

    # 保存缩放后的 CSV
    df_scaled.to_csv(output_csv, index=False)
    print(f"缩放后的数据已保存至: {output_csv}")

    # 保存缩放参数
    if params_path is None:
        base = os.path.splitext(output_csv)[0]
        params_path = base + "_robust_params.json"
    params = {
        "center": scaler.center_.tolist(),
        "scale": scaler.scale_.tolist(),
        "feature_names": feature_names
    }
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2, ensure_ascii=False)
    print(f"缩放参数已保存至: {params_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="先行处理：对 Gallstone 数据集进行 RobustScaler 缩放"
    )
    parser.add_argument("input", help="输入 CSV 文件（如 GallstoneDataset_selected.csv）")
    parser.add_argument("-o", "--output", default=None,
                        help="输出 CSV 文件路径，默认在原文件名后加 _robust")
    parser.add_argument("--params", default=None,
                        help="缩放参数 JSON 路径，默认自动生成")
    args = parser.parse_args()

    if args.output is None:
        base, ext = os.path.splitext(args.input)
        args.output = base + "_robust" + ext

    robust_scale_csv(args.input, args.output, args.params)