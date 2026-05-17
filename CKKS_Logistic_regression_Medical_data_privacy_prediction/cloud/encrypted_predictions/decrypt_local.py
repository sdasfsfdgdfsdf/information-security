import os
import pickle
import sys
import tenseal as ts
import numpy as np
from datetime import datetime

# ======================== 配置 ========================
SECRET_CTX_PATH = "../keys/cloud_ckks_context_public.bin"   # 私密上下文路径，请根据实际修改

def main():
    if not os.path.exists(SECRET_CTX_PATH):
        print(f"错误：私密上下文文件不存在: {SECRET_CTX_PATH}")
        return

    with open(SECRET_CTX_PATH, 'rb') as f:
        ctx_secret = ts.context_from(f.read())

    pkl_files = [f for f in os.listdir('.') if f.endswith('.pkl')]
    if not pkl_files:
        print("当前目录下没有找到 .pkl 文件。")
        return

    all_probs = []  # 存放所有解密出的概率值

    for pkl_file in pkl_files:
        print(f"正在处理: {pkl_file}")
        with open(pkl_file, 'rb') as f:
            data = pickle.load(f)

        # 兼容单条 bytes → 包装为列表
        if isinstance(data, bytes):
            data = [data]
        elif not isinstance(data, list):
            print(f"  文件内容格式错误：{type(data)}，跳过")
            continue

        # 解密每条概率
        file_probs = []
        for idx, enc_bytes in enumerate(data):
            try:
                enc_prob = ts.ckks_vector_from(ctx_secret, enc_bytes)
                prob = enc_prob.decrypt()[0]
                prob = max(0.0, min(1.0, float(prob)))
                file_probs.append(prob)
            except Exception as e:
                print(f"  样本 {idx+1} 解密失败: {e}")
                file_probs.append(None)

        all_probs.extend(file_probs)
        print(f"  已解密 {len(file_probs)} 条概率")

    if all_probs:
        probs_array = np.array(all_probs)
        print("\n" + "=" * 60)
        print("解密完成！所有预测概率数组：")
        print(probs_array)
        print(f"形状: {probs_array.shape}, 总数: {len(all_probs)}")

        # 可选保存为 .npy 或 .csv
        out_npy = f"decrypted_probs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npy"
        np.save(out_npy, probs_array)
        print(f"概率数组已保存至: {out_npy}")
    else:
        print("未成功解密任何概率。")

if __name__ == "__main__":
    main()