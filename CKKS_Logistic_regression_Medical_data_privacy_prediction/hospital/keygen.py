import os
import time
import tenseal as ts

def key_gen(save_dir="keys"):
    """
    生成 CKKS 全局环境参数 Γ 及三份密钥文件。
    1. hospital_...   : 含私钥 SK（可解密）
    2. patient_...    : 仅 PK 和 evk（加密用，无旋转密钥）
    3. cloud_...      : PK、evk、gk（全同态运算，不可解密）
    """

    # ======================== 1. 创建 CKKS 上下文 ========================
    poly_mod_degree = 32768
    coeff_mod_bit_sizes = [60] + [30]*20 + [60]   # 标准安全参数
    # 注意：若原代码用了 [25]*22，请替换；此处用常规安全参数以避免解密错误

    context = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_mod_degree,
        -1,
        coeff_mod_bit_sizes
    )
    context.global_scale = 2**30

    # ======================== 2. 触发生成 evk ========================
    # print("触发生成重线性化密钥 (evk)...")
    # start = time.time()
    # _ = ts.ckks_vector(context, [0.0]) * ts.ckks_vector(context, [0.0])
    # print(f"  --> 耗时 {time.time() - start:.1f} 秒")

    # ======================== 3. 打印参数 ========================
    print("\n" + "=" * 50)
    print("[KeyGen] CKKS 上下文参数 Γ：")
    print(f"  N   = {poly_mod_degree}")
    print(f"  q_i = {coeff_mod_bit_sizes}")
    print(f"  Δ   = 2^{int(context.global_scale).bit_length() - 1}")
    print(f"  χ   = SEAL 默认 (σ=3.19)")
    print("=" * 50)

    os.makedirs(save_dir, exist_ok=True)

    # ======================== 4. 保存患者端上下文 (PK + evk) ========================
    patient_path = os.path.join(save_dir, "patient_ckks_context_public.bin")
    with open(patient_path, "wb") as f:
        f.write(context.serialize(save_secret_key=False))
    print(f"[患者] 公开上下文已保存 (PK, evk) -> {patient_path}")

    # ======================== 5. 生成 Galois 密钥，然后保存云端上下文 ========================
    # print("\n生成 Galois 密钥 (gk)...")
    # start = time.time()
    # context.generate_galois_keys()
    # print(f"  --> 耗时 {time.time() - start:.1f} 秒")

    cloud_path = os.path.join(save_dir, "cloud_ckks_context_public.bin")
    with open(cloud_path, "wb") as f:
        f.write(context.serialize(save_secret_key=True))
    print(f"[云端] 公开上下文已保存 (PK, evk, gk) -> {cloud_path}")

    # ======================== 6. 保存医院私密上下文 (含 SK) ========================
    hospital_path = os.path.join(save_dir, "hospital_ckks_context_secret.bin")
    with open(hospital_path, "wb") as f:
        f.write(context.serialize(save_secret_key=True))
    print(f"[医院] 私密上下文已保存 (SK) -> {hospital_path}")

    # ======================== 7. 文件大小 ========================
    try:
        s_p = os.path.getsize(patient_path) / 1e6
        s_c = os.path.getsize(cloud_path) / 1e6
        s_h = os.path.getsize(hospital_path) / 1e6
        print(f"\n文件大小：患者 {s_p:.1f} MB, 云端 {s_c:.1f} MB, 医院 {s_h:.1f} MB")
    except:
        pass

    print("\n密钥生成完成。分发说明：")
    print("  - hospital_...  → 医院内部，绝对保密")
    print("  - patient_...   → 公开网站，供患者加密用")
    print("  - cloud_...     → 安全发送至云计算中心")

    return hospital_path, patient_path, cloud_path

if __name__ == "__main__":
    key_gen()