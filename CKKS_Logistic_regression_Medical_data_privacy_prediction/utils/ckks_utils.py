import tenseal as ts
import numpy as np
import joblib
import os

STORAGE_DIR = 'storage'
CLOUD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cloud')
ENCRYPTED_DATASET_DIR = os.path.join(CLOUD_DIR, 'encrypted_dataset')
ENCRYPTED_MODELS_DIR = os.path.join(CLOUD_DIR, 'encrypted_models')

# 确保目录存在
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)
if not os.path.exists(ENCRYPTED_DATASET_DIR):
    os.makedirs(ENCRYPTED_DATASET_DIR)
if not os.path.exists(ENCRYPTED_MODELS_DIR):
    os.makedirs(ENCRYPTED_MODELS_DIR)

def generate_ckks_keys(poly_modulus_degree=8192, coeff_mod_bit_sizes=[60, 40, 40, 60]):
    context = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=poly_modulus_degree,
        coeff_mod_bit_sizes=coeff_mod_bit_sizes
    )
    context.generate_galois_keys()
    context.generate_relin_keys()
    sk = context.secret_key()
    pk = context.public_key()
    return context, sk, pk

def save_public_key(context, filename='public_key.bin'):
    path = os.path.join(STORAGE_DIR, filename)
    context_copy = ts.context_from(context.serialize())
    context_copy.make_context_public()
    with open(path, 'wb') as f:
        f.write(context_copy.serialize())

def load_public_key(filename='public_key.bin'):
    path = os.path.join(STORAGE_DIR, filename)
    with open(path, 'rb') as f:
        context_bytes = f.read()
    context = ts.context_from(context_bytes)
    return context

def save_context(context, filename='secret_context.bin'):
    path = os.path.join(STORAGE_DIR, filename)
    with open(path, 'wb') as f:
        f.write(context.serialize())

def load_context(filename='secret_context.bin'):
    path = os.path.join(STORAGE_DIR, filename)
    with open(path, 'rb') as f:
        context_bytes = f.read()
    return ts.context_from(context_bytes)

def encrypt_vector(context, vector):
    return ts.ckks_vector(context, vector)

def decrypt_vector(sk, encrypted_vector):
    return encrypted_vector.decrypt(sk)

def encrypt_matrix(context, matrix):
    encrypted_rows = []
    for row in matrix:
        encrypted_rows.append(ts.ckks_vector(context, row))
    return encrypted_rows

def decrypt_matrix(sk, encrypted_matrix):
    decrypted_matrix = []
    for row in encrypted_matrix:
        decrypted_matrix.append(row.decrypt(sk))
    return decrypted_matrix

def save_encrypted_data(data, filename):
    path = os.path.join(STORAGE_DIR, filename)
    serialized = []
    for item in data:
        if hasattr(item, 'serialize'):
            serialized.append(item.serialize())
        else:
            serialized.append(item)
    joblib.dump(serialized, path)

def load_encrypted_data(filename, context=None):
    path = os.path.join(STORAGE_DIR, filename)
    serialized = joblib.load(path)
    data = []
    for item in serialized:
        if isinstance(item, bytes) and context is not None:
            data.append(ts.ckks_vector_from(context, item))
        else:
            data.append(item)
    return data

def save_model(model, filename='encrypted_model.pkl'):
    path = os.path.join(STORAGE_DIR, filename)
    joblib.dump(model, path)

def load_model(filename='encrypted_model.pkl'):
    path = os.path.join(STORAGE_DIR, filename)
    return joblib.load(path)

def list_models():
    if not os.path.exists(ENCRYPTED_MODELS_DIR):
        return []
    files = os.listdir(ENCRYPTED_MODELS_DIR)
    models = [f for f in files if f.endswith('.bin') and 'model' in f.lower()]
    return sorted(models, reverse=True)

def list_train_files():
    if not os.path.exists(ENCRYPTED_DATASET_DIR):
        return []
    files = os.listdir(ENCRYPTED_DATASET_DIR)
    train_files = [f for f in files if f.endswith('.pkl')]
    return sorted(train_files, reverse=True)
