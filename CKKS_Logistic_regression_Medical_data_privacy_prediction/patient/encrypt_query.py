import os
import json
import pickle
import argparse
import numpy as np
import pandas as pd
import tenseal as ts


def load_public_context(context_path):
    """加载公开运算上下文（仅 PK, evk, gk）"""
    print(f"正在加载公开密钥上下文：{context_path}")
    with open(context_path, "rb") as f:
        ctx = ts.context_from(f.read())
    print("公开上下文加载成功。")
    return ctx


def load_norm_params(norm_json_path):
    """加载标准化参数"""
    with open(norm_json_path, "r", encoding="utf-8") as f:
        params = json.load(f)
    print(f"标准化参数已加载，涵盖特征：{params['feature_names']}")
    return params


def preprocess_and_encrypt(raw_features, norm_params, context):
    """
    对原始特征进行标准化 → 加偏置 → 公钥加密
    返回序列化密文字节串
    """
    x_raw = np.array(raw_features, dtype=float)
    mean = np.array(norm_params["mean"])
    std = np.array(norm_params["std"])

    x_scaled = (x_raw - mean) / std
    x_with_bias = np.insert(x_scaled, 0, 1.0)  # 插入偏置项

    enc_x = ts.ckks_vector(context, x_with_bias.tolist())
    return enc_x.serialize()


def main():
    parser = argparse.ArgumentParser(
        description="患者端：加密个人健康数据（支持单条交互、命令行单条、CSV批量）"
    )
    parser.add_argument("--public_ctx", default="keys/patient_ckks_context_public.bin",
                        help="公开密钥上下文文件路径")
    parser.add_argument("--norm_params", required=True,
                        help="对应数据集的标准化参数 JSON（如 diabetes_norm_params.json）")
    parser.add_argument("--features", nargs="+", type=float, default=None,
                        help="原始特征值（命令行输入），按顺序，例如：5.1 3.5 1.4 0.2")
    parser.add_argument("--csv", default=None,
                        help="包含多条患者原始数据的 CSV 文件（列顺序需与 norm_params 一致）")
    parser.add_argument("--output", default=None,
                        help="保存密文的输出文件路径，默认自动生成")

    args = parser.parse_args()

    # ---- 加载参数和上下文 ----
    norm = load_norm_params(args.norm_params)
    ctx = load_public_context(args.public_ctx)
    feature_names = norm["feature_names"]
    n_features = len(feature_names)

    # ---- 收集原始数据 ----
    raw_samples = []  # 每一项是 list of float

    if args.csv:
        # 从 CSV 批量读取
        print(f"正在从 CSV 文件批量读取：{args.csv}")
        df = pd.read_csv(args.csv)
        # 假设 CSV 列与 feature_names 顺序一致，且仅包含特征列
        if df.shape[1] != n_features:
            raise ValueError(f"CSV 特征列数 ({df.shape[1]}) 与标准化参数中的特征数 ({n_features}) 不匹配")
        raw_samples = df.values.tolist()
        print(f"已读取 {len(raw_samples)} 条样本")
    elif args.features:
        # 命令行直接传入单条特征
        if len(args.features) != n_features:
            raise ValueError(f"输入特征值数量 ({len(args.features)}) 与标准化参数中特征数 ({n_features}) 不匹配")
        raw_samples.append(args.features)
    else:
        # 交互式输入单条
        print(f"请输入 {n_features} 个特征值，对应特征：{feature_names}")
        raw = []
        for name in feature_names:
            val = float(input(f"{name}: "))
            raw.append(val)
        raw_samples.append(raw)

    # ---- 批量加密 ----
    enc_bytes_list = []
    for i, raw in enumerate(raw_samples):
        enc_bytes = preprocess_and_encrypt(raw, norm, ctx)
        enc_bytes_list.append(enc_bytes)
        if len(raw_samples) > 1 and (i+1) % max(1, len(raw_samples)//10) == 0:
            print(f"  已加密 {i+1}/{len(raw_samples)} 条")

    # ---- 保存为列表（与云端预测模块完全兼容） ----
    if args.output:
        out_path = args.output
    else:
        # 自动生成文件名：基于数据集前缀 + 样本数
        base = os.path.splitext(os.path.basename(args.norm_params))[0]
        out_path = f"encrypted_query_{base}_{len(enc_bytes_list)}samples.pkl"

    with open(out_path, "wb") as f:
        pickle.dump(enc_bytes_list, f)

    print(f"密文查询列表已保存至：{out_path}（共 {len(enc_bytes_list)} 条）")
    print("可将该文件上传至云端预测服务，获得加密预测结果。")


if __name__ == "__main__":
    main()