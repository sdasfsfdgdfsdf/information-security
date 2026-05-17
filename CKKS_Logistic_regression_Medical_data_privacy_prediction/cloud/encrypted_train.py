import os
import pickle
import time
import numpy as np
import tenseal as ts


def sigmoid_poly(enc_z):
    """一阶近似：0.125*x + 0.5"""
    return enc_z * 0.125 + 0.5


def train_from_encrypted_data(
    context_pub_path,   # 公开运算上下文（.bin）
    dataset_name,       # 数据集名称，如 "heart_disease"
    data_dir,           # 存放加密数据和标签的目录
    model_dir,          # 模型保存目录
    lr=0.1,
    gamma=0.9,
    n_iters=3
):
    """
    云端密文训练：仅依赖密文特征和明文标签，完全不需要标准化参数。
    """

    # ---- 1. 加载公开上下文 ----
    print(f"正在加载公开运算上下文：{context_pub_path}")
    with open(context_pub_path, 'rb') as f:
        ctx_pub = ts.context_from(f.read())
    ctx_pub.generate_galois_keys()
    print("公开上下文加载成功。")

    # ---- 2. 读取加密特征及明文标签 ----
    enc_X_path = os.path.join(data_dir, f"{dataset_name}_encrypted_X.pkl")
    y_path     = os.path.join(data_dir, f"{dataset_name}_y.pkl")

    with open(enc_X_path, 'rb') as f:
        encrypted_X_bytes_list = pickle.load(f)
    with open(y_path, 'rb') as f:
        y_list = pickle.load(f)

    m = len(encrypted_X_bytes_list)
    print(f"数据集 [{dataset_name}]：样本数 = {m}")

    # ---- 3. 反序列化密文向量，并自动获取特征维度 ----
    print("正在反序列化密文特征向量...")
    enc_X = []
    for idx, b in enumerate(encrypted_X_bytes_list):
        enc_x = ts.ckks_vector_from(ctx_pub, b)
        enc_X.append(enc_x)
        if (idx + 1) % max(1, m // 10) == 0:
            print(f"  已加载 {idx + 1}/{m}")

    # 特征数 n 直接从密文获取（每个密文向量的长度，即槽内数据长度）
    n = enc_X[0].size()
    print(f"特征数（含偏置） = {n}")

    # ---- 4. 初始化权重和动量 ----
    enc_w = ts.ckks_vector(ctx_pub, [0.0] * n)
    enc_v = ts.ckks_vector(ctx_pub, [0.0] * n)

    print(f"开始训练：lr={lr}, gamma={gamma}, 迭代轮数={n_iters}")
    t_start = time.time()

    # ---- 5. 分块 Nesterov 训练 ----
    for epoch in range(n_iters):
        indices = np.random.permutation(m)
        block_size = int(np.ceil(m / n_iters))
        start = epoch * block_size
        end = min((epoch + 1) * block_size, m)
        batch_indices = indices[start:end]
        actual_bs = len(batch_indices)

        # 前瞻点
        enc_w_tilde = enc_w - enc_v * gamma

        # 累加梯度
        enc_grad = ts.ckks_vector(ctx_pub, [0.0] * n)
        for i in batch_indices:
            enc_x_i = enc_X[i]
            enc_z = enc_x_i.dot(enc_w_tilde)
            enc_h = sigmoid_poly(enc_z)
            enc_err = enc_h - y_list[i]
            enc_grad += enc_err * enc_x_i

        # 更新
        enc_v = enc_v * gamma + enc_grad * (lr / actual_bs)
        enc_w = enc_w - enc_v

        print(f"Epoch {epoch+1}/{n_iters} 完成（本块 {actual_bs} 样本）")

    train_time = time.time() - t_start
    print(f"训练完成，总耗时：{train_time:.2f} 秒")

    # ---- 6. 保存加密模型 ----
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, f"{dataset_name}_encrypted_model.bin")
    with open(model_path, 'wb') as f:
        f.write(enc_w.serialize())
    print(f"加密模型已保存至：{model_path}")

    return model_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="云计算中心：密文训练逻辑回归模型")
    parser.add_argument("--context",default="keys/cloud_ckks_context_public.bin", required=True, help="公开运算上下文路径")
    parser.add_argument("--dataset", required=True, help="数据集名称")
    parser.add_argument("--data_dir", default="encrypted_dataset", help="加密数据目录")
    parser.add_argument("--model_dir", default="encrypted_models", help="模型保存目录")
    parser.add_argument("--lr", type=float, default=0.1)
    parser.add_argument("--gamma", type=float, default=0.9)
    parser.add_argument("--iters", type=int, default=3)
    args = parser.parse_args()

    train_from_encrypted_data(
        context_pub_path=args.context,
        dataset_name=args.dataset,
        data_dir=args.data_dir,
        model_dir=args.model_dir,
        lr=args.lr,
        gamma=args.gamma,
        n_iters=args.iters
    )