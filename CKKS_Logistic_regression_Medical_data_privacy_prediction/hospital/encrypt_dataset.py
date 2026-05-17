import os
import json
import pickle
import numpy as np
import pandas as pd
import tenseal as ts


def load_and_preprocess_all(file_path):
    """
    加载 CSV，全部数据返回并保存标准化参数。
    返回：
        - X_all: 预处理后的特征矩阵（已标准化 + 偏置）
        - y_all: 标签向量
        - norm_params: dict，包含原始特征的 mean, std 和 feature_names
    """
    df = pd.read_csv(file_path)
    X = df.iloc[:, :-1].values.astype(float)
    y = df.iloc[:, -1].values.astype(float)

    original_means = X.mean(axis=0)
    original_stds = X.std(axis=0) + 1e-8

    X_scaled = (X - original_means) / original_stds
    X_all = np.hstack((np.ones((X_scaled.shape[0], 1)), X_scaled))

    idx = np.random.permutation(len(X_all))
    X_all, y_all = X_all[idx], y[idx]

    norm_params = {
        "mean": original_means.tolist(),
        "std": original_stds.tolist(),
        "feature_names": df.columns[:-1].tolist()
    }

    return X_all, y_all, norm_params


def encrypt_dataset(context_path, data_csv, output_dir):
    """
    加密全部训练数据集，输出文件根据 CSV 文件名自动命名。

    参数：
        context_path: 密钥上下文文件路径（公开或私密均可）
        data_csv: 医院脱敏后 CSV 文件路径
        output_dir: 输出目录，生成的文件格式如下：
            - {csv_basename}_encrypted_X.pkl
            - {csv_basename}_y.pkl
            - {csv_basename}_norm_params.json
    """
    # 1. 提取数据集前缀名
    csv_basename = os.path.splitext(os.path.basename(data_csv))[0]

    # 2. 加载密钥上下文
    print(f"正在加载密钥上下文：{context_path}")
    with open(context_path, "rb") as f:
        context = ts.context_from(f.read())
    print("上下文加载成功。")

    # 3. 数据预处理（全部样本）
    print(f"正在加载并预处理数据：{data_csv}")
    X_all, y_all, norm_params = load_and_preprocess_all(data_csv)
    m, n = X_all.shape
    print(f"全量训练样本数: {m}, 特征数: {n} (含偏置)")

    # 4. 加密所有特征向量
    print("开始加密特征向量...")
    encrypted_X = []
    for i in range(m):
        x = X_all[i].tolist()
        enc_x = ts.ckks_vector(context, x)
        encrypted_X.append(enc_x.serialize())
        if (i + 1) % max(1, m // 10) == 0:
            print(f"  已加密 {i+1}/{m} 条样本")

    # 5. 保存到带前缀命名的文件
    os.makedirs(output_dir, exist_ok=True)

    enc_path = os.path.join(output_dir, f"{csv_basename}_encrypted_X.pkl")
    with open(enc_path, "wb") as f:
        pickle.dump(encrypted_X, f)
    print(f"密文特征向量已保存至：{enc_path}")

    label_path = os.path.join(output_dir, f"{csv_basename}_y.pkl")
    with open(label_path, "wb") as f:
        pickle.dump(y_all.tolist(), f)
    print(f"明文标签已保存至：{label_path}")

    norm_path = os.path.join(output_dir, f"{csv_basename}_norm_params.json")
    with open(norm_path, "w", encoding="utf-8") as f:
        json.dump(norm_params, f, indent=2, ensure_ascii=False)
    print(f"标准化参数已保存至：{norm_path}")

    print(f"\n数据集 [{csv_basename}] 加密完成，可将以下文件上传至云端：")
    print(f"  - {enc_path}")
    print(f"  - {label_path}")
    print(f"标准化参数文件请公开发布，供患者端加密查询时使用。")
    return enc_path, label_path, norm_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="医院端：加密全部训练数据集，输出文件根据 CSV 文件名自动命名")
    parser.add_argument("--context", default="keys/hospital_ckks_context_secret.bin",
                        help="密钥上下文文件路径（默认使用医院私密上下文）")
    parser.add_argument("--data", required=True,
                        help="医院历史病历 CSV 文件路径")
    parser.add_argument("--output", default="encrypted_dataset",
                        help="加密数据输出目录")
    args = parser.parse_args()

    encrypt_dataset("keys/hospital_ckks_context_secret.bin", args.data, "encrypted_dataset")