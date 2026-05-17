import os
import json
import pickle
import argparse
import tenseal as ts
from datetime import datetime


# ======================== 审计日志 ========================
def write_audit_log(log_dir, log_entry):
    """将单次解密操作记录到审计日志中（JSON 行格式）"""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "decrypt_audit.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


# ======================== 单样本解密（内部使用） ========================
def _decrypt_single(ctx_secret, enc_result_bytes):
    """解密单个加密概率，返回明文概率"""
    enc_prob = ts.ckks_vector_from(ctx_secret, enc_result_bytes)
    prob = enc_prob.decrypt()[0]          # CKKS 第一个元素
    prob = max(0.0, min(1.0, float(prob))) # 裁剪到 [0,1]
    return prob


# ======================== 诊断建议生成 ========================
def _generate_diagnosis(prob):
    if prob >= 0.5:
        diagnosis = "阳性（高风险）"
        suggestion = "建议尽快进行进一步临床检查，结合其他指标综合评估。"
        risk_level = "high"
    else:
        diagnosis = "阴性（低风险）"
        suggestion = "目前预测风险较低，请保持健康生活方式，定期复查。"
        risk_level = "low"
    return risk_level, diagnosis, suggestion


# ======================== 批量解密主函数 ========================
def decrypt_results(
    secret_ctx_path,           # 医院私密上下文路径（含 SK）
    encrypted_results_path=None,  # 加密预测结果文件（.pkl 或 .bin）
    encrypted_results_bytes=None, # 直接传入的 bytes（列表或单个）
    dataset_name=None,
    patient_ids=None,          # 患者 ID 列表（可选，与样本数对应）
    prediction_id=None,
    model_id=None,
    log_dir="audit_logs"
):
    """
    解密云端返回的一个或多个加密预测结果（兼容批量与单样本）。
    
    encrypted_results_path: 文件路径（优先），内容可能是：
        - 单条 bytes（旧格式 .bin）
        - bytes 列表（新格式 .pkl）
    encrypted_results_bytes: 直接传入的 bytes 数据（同上）。
    
    返回：
        list of dict: 每条结果的详细信息（包含明文概率、诊断等）
    """
    # ---- 1. 加载私密上下文 ----
    print(f"[解密] 加载私密上下文：{secret_ctx_path}")
    if not os.path.exists(secret_ctx_path):
        raise FileNotFoundError(f"私密上下文文件不存在：{secret_ctx_path}")
    with open(secret_ctx_path, 'rb') as f:
        ctx_secret = ts.context_from(f.read())
    print("[解密] 私密上下文加载成功，私钥已就绪。")

    # ---- 2. 读取加密数据 ----
    raw_data = None
    if encrypted_results_path is not None:
        if not os.path.exists(encrypted_results_path):
            raise FileNotFoundError(f"加密结果文件不存在：{encrypted_results_path}")
        # 判断文件类型：若扩展名为 .pkl 则按列表读取；否则当作纯 bytes
        if encrypted_results_path.endswith('.pkl'):
            with open(encrypted_results_path, 'rb') as f:
                data = pickle.load(f)
            # 兼容性：若内部是单个 bytes 仍包装为列表
            if isinstance(data, bytes):
                data = [data]
            elif not isinstance(data, list):
                raise TypeError("加密结果文件内容不是 bytes 也不是列表")
            raw_data = data
        else:
            # .bin 或其他文件，按单个密文读取
            with open(encrypted_results_path, 'rb') as f:
                raw_data = [f.read()]
    elif encrypted_results_bytes is not None:
        # 直接使用 bytes 或列表
        if isinstance(encrypted_results_bytes, bytes):
            raw_data = [encrypted_results_bytes]
        elif isinstance(encrypted_results_bytes, list):
            raw_data = encrypted_results_bytes
        else:
            raise TypeError("encrypted_results_bytes 必须是 bytes 或 list")
    else:
        raise ValueError("必须提供 encrypted_results_path 或 encrypted_results_bytes")

    num_samples = len(raw_data)

    # 处理患者 ID 列表
    if patient_ids is None:
        patient_ids = [None] * num_samples
    elif isinstance(patient_ids, str):
        patient_ids = [patient_ids] * num_samples
    elif len(patient_ids) != num_samples:
        raise ValueError("patient_ids 数量与样本数不一致")

    # ---- 3. 逐条解密并生成诊断 ----
    results = []
    for idx, enc_bytes in enumerate(raw_data):
        prob = _decrypt_single(ctx_secret, enc_bytes)
        risk_level, diagnosis, suggestion = _generate_diagnosis(prob)

        patient = patient_ids[idx] or "anonymous"
        print("-" * 50)
        print(f"样本 {idx+1}/{num_samples}")
        print(f"  患者ID：{patient}")
        print(f"  预测概率：{prob:.4f}  ({diagnosis})")
        print(f"  建议：{suggestion}")

        # 构造结果条目
        result_entry = {
            "success": True,
            "patient_id": patient,
            "prediction_id": prediction_id or "N/A",
            "model_id": model_id or "N/A",
            "dataset_name": dataset_name or "N/A",
            "decrypted_probability": float(prob),
            "risk_level": risk_level,
            "diagnosis": diagnosis,
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat()
        }
        results.append(result_entry)

        # 审计日志
        write_audit_log(log_dir, result_entry)

    print("\n" + "=" * 60)
    print(f"批量解密完成，共 {num_samples} 条结果")
    print(f"审计日志记录于 {log_dir}/decrypt_audit.log")
    return results


# ======================== 单样本解密（保持向后兼容） ========================
def decrypt_prediction(
    secret_ctx_path,
    encrypted_result=None,
    dataset_name=None,
    patient_id=None,
    prediction_id=None,
    model_id=None,
    log_dir="audit_logs"
):
    """
    解密单个加密预测结果（向后兼容旧调用）。
    encrypted_result 可以是文件路径或 bytes。
    """
    if isinstance(encrypted_result, str) and os.path.exists(encrypted_result):
        return decrypt_results(
            secret_ctx_path=secret_ctx_path,
            encrypted_results_path=encrypted_result,
            dataset_name=dataset_name,
            patient_ids=[patient_id],
            prediction_id=prediction_id,
            model_id=model_id,
            log_dir=log_dir
        )[0]
    else:
        # 假设是 bytes
        return decrypt_results(
            secret_ctx_path=secret_ctx_path,
            encrypted_results_bytes=encrypted_result,
            dataset_name=dataset_name,
            patient_ids=[patient_id],
            prediction_id=prediction_id,
            model_id=model_id,
            log_dir=log_dir
        )[0]


# ======================== 命令行入口 ========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="医院端：解密云端返回的加密预测结果")
    parser.add_argument("--secret_ctx", default="keys/hospital_ckks_context_secret.bin",
                        help="医院私密上下文文件路径（含 SK）")
    parser.add_argument("--encrypted_result", default=None,
                        help="单个加密预测结果文件路径（.bin，向后兼容）")
    parser.add_argument("--encrypted_results", default=None,
                        help="批量加密预测结果文件路径（.pkl，来自云端预测服务）")
    parser.add_argument("--dataset", default=None, help="数据集名称")
    parser.add_argument("--patient_id", default=None, help="患者 ID（单样本时使用）")
    parser.add_argument("--patient_ids", nargs="+", default=None, help="患者 ID 列表（批量时使用）")
    parser.add_argument("--prediction_id", default=None, help="预测 ID")
    parser.add_argument("--model_id", default=None, help="模型 ID")
    parser.add_argument("--log_dir", default="audit_logs", help="审计日志目录")

    args = parser.parse_args()

    if args.encrypted_results:
        # 批量模式
        decrypt_results(
            secret_ctx_path=args.secret_ctx,
            encrypted_results_path=args.encrypted_results,
            dataset_name=args.dataset,
            patient_ids=args.patient_ids,
            prediction_id=args.prediction_id,
            model_id=args.model_id,
            log_dir=args.log_dir
        )
    elif args.encrypted_result:
        # 单样本模式（向后兼容）
        decrypt_prediction(
            secret_ctx_path=args.secret_ctx,
            encrypted_result=args.encrypted_result,
            dataset_name=args.dataset,
            patient_id=args.patient_id,
            prediction_id=args.prediction_id,
            model_id=args.model_id,
            log_dir=args.log_dir
        )
    else:
        print("请提供 --encrypted_result (单样本) 或 --encrypted_results (批量) 参数")
        print("示例：")
        print("  单样本: python decrypt_prediction.py --encrypted_result result.bin --patient_id P001")
        print("  批量:   python decrypt_prediction.py --encrypted_results heart_disease_encrypted_predictions.pkl --patient_ids P001 P002")