import os
import pickle
import argparse
import tenseal as ts


def sigmoid_poly(enc_z):
    """一阶多项式近似：0.125*x + 0.5"""
    return enc_z * 0.125 + 0.5


def encrypted_predict_single(enc_w, enc_x):
    """单样本密文预测，enc_w 和 enc_x 必须为 TenSEAL 向量"""
    enc_z = enc_x.dot(enc_w)
    return sigmoid_poly(enc_z)


def encrypted_predict_batch(enc_w, enc_x_list):
    """批量密文预测"""
    return [encrypted_predict_single(enc_w, enc_x) for enc_x in enc_x_list]


def _deserialize_item(item, ctx):
    """将 bytes 转换为 ts.ckks_vector，若不是则原样返回"""
    if isinstance(item, bytes):
        return ts.ckks_vector_from(ctx, item)
    elif hasattr(item, 'dot'):   # 粗略判断是否为 TenSEAL 向量
        return item
    else:
        raise TypeError(f"不支持的查询元素类型：{type(item)}。请提供 bytes 或 TenSEAL 向量。")


def encrypted_predict(
    public_ctx_path,
    model_dir,
    dataset_name,
    query_path=None,
    query_list=None,
    output_dir=None,
    patient_id=None,
    prediction_id=None
):
    # 1. 加载公开上下文（无 SK）
    print(f"加载公开运算上下文：{public_ctx_path}")
    with open(public_ctx_path, 'rb') as f:
        ctx = ts.context_from(f.read())
    
    # 关键修复：必须在创建任何向量之前生成 Galois keys
    # 点积操作需要 Galois keys 支持
    ctx.generate_galois_keys()
    print("Galois keys 生成成功")
    

    # 2. 加载加密模型
    model_path = os.path.join(model_dir, f"{dataset_name}_encrypted_model.bin")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"加密模型不存在：{model_path}")
    with open(model_path, 'rb') as f:
        enc_w = ts.ckks_vector_from(ctx, f.read())
    print(f"已加载加密模型 [{dataset_name}]，权重维度：{enc_w.size()}")

    # 3. 加载查询数据（统一处理为向量列表）
    enc_x_list = []
    if query_list is not None:
        print(f"使用直接传入的查询列表，样本数：{len(query_list)}")
        for item in query_list:
            enc_x_list.append(_deserialize_item(item, ctx))
    elif query_path is not None:
        if not os.path.exists(query_path):
            raise FileNotFoundError(f"查询文件不存在：{query_path}")
        with open(query_path, 'rb') as f:
            data = pickle.load(f)

        # 兼容性：如果文件内是单个 bytes（旧版或意外情况），自动包装为列表
        if isinstance(data, bytes):
            data = [data]
            print("检测到单样本查询文件，已转换为列表。")
        elif not isinstance(data, list):
            raise TypeError(f"查询文件内容应为列表，得到 {type(data)}")

        print(f"已加载查询文件，样本数：{len(data)}")
        for item in data:
            enc_x_list.append(_deserialize_item(item, ctx))
    else:
        raise ValueError("必须提供 query_path 或 query_list")

    # 4. 批量预测
    print(f"开始密文预测，共 {len(enc_x_list)} 条样本...")
    enc_prob_list = encrypted_predict_batch(enc_w, enc_x_list)
    print("密文预测完成（云端无法解密）")

    # 5. 序列化结果
    enc_prob_bytes_list = [ep.serialize() for ep in enc_prob_list]

    result = {
        "dataset_name": dataset_name,
        "num_samples": len(enc_prob_bytes_list),
        "encrypted_results": enc_prob_bytes_list
    }

    # 6. 可选保存
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        if patient_id and prediction_id:
            out_file = os.path.join(output_dir, f"{patient_id}_{prediction_id}_{dataset_name}_encrypted_predictions.pkl")
        else:
            out_file = os.path.join(output_dir, f"{dataset_name}_encrypted_predictions.pkl")
        with open(out_file, 'wb') as f:
            pickle.dump(enc_prob_bytes_list, f)
        print(f"加密预测结果已保存至：{out_file}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="云端密文预测（兼容批量）")
    parser.add_argument("--public_ctx",default="keys/cloud_ckks_context_public.bin", required=True, help="公开上下文路径")
    parser.add_argument("--model_dir", default="encrypted_models", help="模型目录")
    parser.add_argument("--dataset", required=True, help="数据集名称")
    parser.add_argument("--query", default=None, help="查询文件路径 (.pkl)")
    parser.add_argument("--output_dir", default=None, help="保存结果的可选目录")
    args = parser.parse_args()

    result = encrypted_predict(
        public_ctx_path=args.public_ctx,
        model_dir=args.model_dir,
        dataset_name=args.dataset,
        query_path=args.query,
        output_dir=args.output_dir
    )
    print(f"预测完成，样本数：{result['num_samples']}")