from flask import Flask, jsonify, render_template
from hospital import hospital_bp
from patient import patient_bp
from cloud import cloud_bp
from utils import load_public_key

app = Flask(__name__)

app.register_blueprint(hospital_bp)
app.register_blueprint(patient_bp)
app.register_blueprint(cloud_bp)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api')
def api_home():
    return jsonify({
        'name': 'CKKS-Based Medical Privacy Protection Prediction System',
        'version': '1.0',
        'status': 'Running'
    }), 200

@app.route('/public_key', methods=['GET'])
def get_public_key():
    try:
        context = load_public_key()
        public_key_bytes = context.serialize()
        return jsonify({
            'success': True,
            'public_key': public_key_bytes.hex()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy'
    }), 200

if __name__ == '__main__':
    print('='*60)
    print('医疗数据隐私保护预测系统')
    print('='*60)
    print('系统运行中...')
    print('访问地址: http://127.0.0.1:5000')
    print('API接口: http://127.0.0.1:5000/api')
    print('='*60)
    app.run(debug=True, host='127.0.0.1', port=5000)
