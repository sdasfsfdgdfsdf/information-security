import os
import json
import pickle
import argparse
import numpy as np
import tenseal as ts


def load_secret_context(secret_ctx_path):
    """加载医院私密上下文（含 SK）"""
    print(f"正在加载私密上下文：{secret_ctx_path}")
    if not os.path.exists(secret_ctx_path):
        raise FileNotFoundError(f"私密上下文文件不存在: {secret_ctx_path}")
    with open(secret_ctx_path, 'rb') as f:
        ctx = ts.context_from(f.read())
    print("私密上下文加载成功。")
    return ctx


def load_norm_params(norm_json_path):
    """加载标准化参数（可选，用于逆标准化）"""
    if norm_json_path is None:
        return None
    with open(norm_json_path, 'r', encoding='utf-8') as f:
        params = json.load(f)
    return params


def decrypt_query(ctx_secret, encrypted_query_path, norm_params_path=None):
    """
    解密患者加密查询文件，返回每个样本的明文特征向量。
    
    参数：
        ctx_secret: 医院私密上下文（含私钥）
        encrypted_query_path: 患者生成的 .pkl 文件路径
        norm_params_path: 标准化参数文件路径（可选），若提供则还原原始特征值
        
    返回：
        results: 列表，每个元素是一个字典，包含：
            - "encrypted_index": 样本序号
            - "plaintext_with_bias": 解密后的特征（含偏置项）
            - "original_features": 逆标准化后的原始特征（仅当提供norm_params_path时存在）
    """
    # 加载加密查询
    print(f"加载患者加密查询文件：{encrypted_query_path}")
    with open(encrypted_query_path, 'rb') as f:
        data = pickle.load(f)
    
    # 统一为列表
    if isinstance(data, bytes):
        data = [data]
    elif not isinstance(data, list):
        raise TypeError(f"查询文件内容应为列表或bytes，得到 {type(data)}")
    
    num_samples = len(data)
    print(f"共 {num_samples} 条加密样本")
    
    # 可选加载标准化参数
    norm_params = load_norm_params(norm_params_path) if norm_params_path else None
    
    results = []
    for idx, enc_bytes in enumerate(data):
        # 反序列化密文向量
        enc_x = ts.ckks_vector_from(ctx_secret, enc_bytes)
        # 解密 → 明文列表（含偏置项）
        plain_x = enc_x.decrypt()
        # 去除可能的噪声偏差，转换为浮点数列表
        plain_x = [float(x) for x in plain_x]
        
        result_entry = {
            "sample_index": idx,
            "plaintext_with_bias": plain_x
        }
        
        if norm_params is not None:
            # 逆标准化：先去掉偏置项，再逆标准化
            # 注意：加密时的顺序是 [bias, feat1, feat2, ...]
            bias = plain_x[0]
            scaled_features = np.array(plain_x[1:])
            mean = np.array(norm_params["mean"])
            std = np.array(norm_params["std"])
            original_features = scaled_features * std + mean
            result_entry["original_features"] = original_features.tolist()
            result_entry["bias_term"] = bias
            
            # 打印对比
            print(f"\n样本 {idx+1}:")
            print(f"  解密向量（含偏置）: {plain_x}")
            print(f"  逆标准化后原始特征: {original_features.tolist()}")
        else:
            print(f"\n样本 {idx+1}:")
            print(f"  解密向量（含偏置）: {plain_x}")
        
        results.append(result_entry)
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="医院端：用私钥解密患者加密查询（仅用于测试）")
    parser.add_argument("--secret_ctx", default="../keys/cloud_ckks_context_public.bin",
                        help="医院私密上下文文件路径（含 SK）")
    parser.add_argument("--query", default="./test_query.pkl" ,
                        help="患者加密查询文件路径 (.pkl)")
    parser.add_argument("--norm_params", default=None,
                        help="标准化参数 JSON 文件路径（用于还原原始特征，可选）")
    parser.add_argument("--output", default=None,
                        help="输出解密结果 JSON 路径，默认不保存")
    
    args = parser.parse_args()
    
    # 加载私密上下文
    ctx_secret = load_secret_context(args.secret_ctx)
    
    # 解密查询
    results = decrypt_query(ctx_secret, args.query, args.norm_params)
    
    # 可选保存
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n解密结果已保存至: {args.output}")