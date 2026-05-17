import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ===============================
# 1. 读取数据
# ===============================
def load_data(csv_path, label_column=None):
    df = pd.read_csv(csv_path)

    # 自动识别标签列（如果没指定）
    if label_column is None:
        label_column = df.columns[-1]

    X = df.drop(columns=[label_column]).values
    y = df[label_column].values

    return X, y


# ===============================
# 2. 分位数裁剪（去极端值）
# ===============================
def quantile_clip(X, low_q=0.01, high_q=0.99):
    X_clipped = X.copy()
    for i in range(X.shape[1]):
        low = np.quantile(X[:, i], low_q)
        high = np.quantile(X[:, i], high_q)
        X_clipped[:, i] = np.clip(X[:, i], low, high)
    return X_clipped


# ===============================
# 3. 标准化 + 裁剪 + 特征均衡
# ===============================
def preprocess_features(X_train, X_test):
    # StandardScaler
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # clip范围（关键步骤）
    X_train = np.clip(X_train, -3, 3)
    X_test = np.clip(X_test, -3, 3)

    # 特征均衡（防止内积过大）
    scale_factor = np.sqrt(X_train.shape[1])
    X_train = X_train / scale_factor
    X_test = X_test / scale_factor

    return X_train, X_test, scaler


# ===============================
# 4. 主流程
# ===============================
def process_gallstone(csv_path, label_column=None, test_size=0.2, random_state=42):
    # 读取数据
    X, y = load_data(csv_path, label_column)

    # 分位数裁剪
    X = quantile_clip(X, 0.01, 0.99)

    # 划分数据集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # 预处理
    X_train, X_test, scaler = preprocess_features(X_train, X_test)

    return X_train, X_test, y_train, y_test, scaler


# ===============================
# 5. 保存处理结果（可选）
# ===============================
def save_processed_data(X_train, X_test, y_train, y_test, prefix="gallstone_processed"):
    np.save(f"{prefix}_X_train.npy", X_train)
    np.save(f"{prefix}_X_test.npy", X_test)
    np.save(f"{prefix}_y_train.npy", y_train)
    np.save(f"{prefix}_y_test.npy", y_test)


# ===============================
# 6. 测试运行
# ===============================
if __name__ == "__main__":
    csv_path = "Gallstone Dataset Analysis and Prediction.csv"  # 修改成你的路径

    X_train, X_test, y_train, y_test, scaler = process_gallstone(csv_path)

    print("处理完成")
    print("训练集形状:", X_train.shape)
    print("测试集形状:", X_test.shape)

    # 查看数值范围（非常关键）
    print("特征范围（train）:", np.min(X_train), np.max(X_train))

    # 检查是否稳定
    print("是否存在异常大值:", np.max(np.abs(X_train)) > 5)

    # 保存
    save_processed_data(X_train, X_test, y_train, y_test)
    
    z = model.decision_function(X_test)
    print(np.percentile(z, [1, 50, 99]))