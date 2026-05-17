import uuid
import json
import os

STORAGE_DIR = 'storage'
AUTH_TOKENS_FILE = os.path.join(STORAGE_DIR, 'auth_tokens.json')

def load_auth_tokens():
    if not os.path.exists(AUTH_TOKENS_FILE):
        return {}
    with open(AUTH_TOKENS_FILE, 'r') as f:
        return json.load(f)

def save_auth_tokens(tokens):
    with open(AUTH_TOKENS_FILE, 'w') as f:
        json.dump(tokens, f)

def generate_auth_token(patient_id, prediction_id):
    tokens = load_auth_tokens()
    token = str(uuid.uuid4())
    tokens[token] = {
        'patient_id': patient_id,
        'prediction_id': prediction_id,
        'used': False
    }
    save_auth_tokens(tokens)
    return token

def validate_auth_token(token, prediction_id=None):
    tokens = load_auth_tokens()
    if token not in tokens:
        return False, 'Invalid token'
    token_data = tokens[token]
    if token_data['used']:
        return False, 'Token already used'
    if prediction_id is not None and token_data['prediction_id'] != prediction_id:
        return False, 'Token does not match prediction'
    return True, token_data

def use_auth_token(token):
    tokens = load_auth_tokens()
    if token in tokens:
        tokens[token]['used'] = True
        save_auth_tokens(tokens)
        return True
    return False
