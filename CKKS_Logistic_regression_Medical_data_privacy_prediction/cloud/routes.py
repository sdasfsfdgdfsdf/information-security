from flask import Blueprint, request, jsonify
import sys
import os
import uuid
import time
import tenseal as ts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import list_train_files

cloud_bp = Blueprint('cloud', __name__, url_prefix='/cloud')

# 存储云计算中心密钥接收状态
cloud_context_received = False

# 存储待处理的环境参数申请（云计算中心）
pending_context_requests = []

# 存储医院端的响应（云计算中心需要轮询）
hospital_cloud_responses = []

# 当前云计算中心ID
current_cloud_id = None

# 预测历史记录
prediction_history = []

# 训练历史记录
train_history = []
TRAIN_HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'train_history.json')

# 预测申请队列（等待云计算中心确认）
prediction_requests = []

# 密钥更新通知标志（只通知一次）
key_update_notified = False

@cloud_bp.route('/check_cloud_context', methods=['GET'])
def check_cloud_context():
    try:
        global cloud_context_received
        keys_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys')
        context_path = os.path.join(keys_dir, 'cloud_ckks_context_public.bin')
        context_exists = os.path.exists(context_path)
        context_size = os.path.getsize(context_path) if context_exists else 0
        
        if cloud_context_received:
            return jsonify({
                'success': True,
                'received': True,
                'context_exists': context_exists,
                'context_size': context_size,
                'message': '已接收到医院端的CKKS环境参数'
            }), 200
        else:
            return jsonify({
                'success': True,
                'received': False,
                'context_exists': context_exists,
                'context_size': context_size,
                'message': '尚未接收到环境参数'
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/receive_cloud_context', methods=['POST'])
def receive_cloud_context():
    try:
        global cloud_context_received
        cloud_context_received = True
        return jsonify({
            'success': True,
            'message': '环境参数已成功接收'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/receive_hospital_response', methods=['POST'])
def receive_hospital_response():
    try:
        data = request.json
        approved = data.get('approved', False)
        cloud_id = data.get('cloud_id')
        message = data.get('message', '')

        # 存储医院的响应
        response_info = {
            'cloud_id': cloud_id,
            'approved': approved,
            'message': message,
            'timestamp': time.time(),
            'read': False
        }
        hospital_cloud_responses.append(response_info)

        print(f"[云计算中心] 收到医院对云计算中心 {cloud_id} 的响应: {'批准' if approved else '拒绝'}")

        return jsonify({
            'success': True,
            'message': '已收到医院的响应'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/apply_context', methods=['POST'])
def apply_context():
    try:
        data = request.json
        cloud_id = data.get('cloud_id')

        if not cloud_id:
            return jsonify({
                'success': False,
                'message': '云计算中心ID不能为空'
            }), 400

        global current_cloud_id
        current_cloud_id = cloud_id

        # 添加到待处理申请列表
        request_info = {
            'cloud_id': cloud_id,
            'timestamp': time.time(),
            'status': 'pending'
        }
        pending_context_requests.append(request_info)

        print(f"[云计算中心] 云计算中心 {cloud_id} 申请环境参数，等待医院审核...")

        # 通知医院端有新的申请
        try:
            import requests as req
            hospital_resp = req.post('http://127.0.0.1:5000/hospital/add_cloud_application', json={
                'cloud_id': cloud_id
            })
            print(f"[云计算中心] 已通知医院端云计算中心 {cloud_id} 的申请")
        except Exception as e:
            print(f"[云计算中心] 通知医院端失败: {e}")

        return jsonify({
            'success': True,
            'message': f'已向医院端发送环境参数申请，等待审核...',
            'request_id': len(pending_context_requests) - 1
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/check_hospital_response', methods=['GET'])
def check_hospital_response():
    try:
        global hospital_cloud_responses, current_cloud_id

        # 查找最新的针对当前云计算中心的未读响应
        for i in range(len(hospital_cloud_responses) - 1, -1, -1):
            resp = hospital_cloud_responses[i]
            if resp.get('cloud_id') == current_cloud_id and not resp.get('read'):
                # 标记为已读
                resp['read'] = True
                return jsonify({
                    'success': True,
                    'has_response': True,
                    'approved': resp.get('approved'),
                    'message': resp.get('message')
                }), 200

        return jsonify({
            'success': True,
            'has_response': False,
            'message': '等待医院审核...'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/confirm_context_reception', methods=['POST'])
def confirm_context_reception():
    try:
        data = request.json
        accepted = data.get('accepted', True)
        cloud_id = data.get('cloud_id')

        global cloud_context_received

        if accepted:
            cloud_context_received = True

            # 保存环境参数文件到 cloud/keys 目录
            cloud_keys_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys')
            os.makedirs(cloud_keys_dir, exist_ok=True)

            # 从医院端获取环境参数文件
            hospital_key_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'hospital', 'keys', 'cloud_ckks_context_public.bin'
            )

            if os.path.exists(hospital_key_path):
                dest_path = os.path.join(cloud_keys_dir, 'cloud_ckks_context_public.bin')
                import shutil
                shutil.copy(hospital_key_path, dest_path)
                print(f"[云计算中心] 环境参数已保存至 {dest_path}")

            print(f"[云计算中心] 云计算中心 {cloud_id} 已接收环境参数")

            # 通知医院端云计算中心的确认结果
            try:
                import requests as req
                req.post('http://127.0.0.1:5000/hospital/add_cloud_confirmation', json={
                    'cloud_id': cloud_id,
                    'accepted': accepted
                })
                print(f"[云计算中心] 已通知医院端云计算中心 {cloud_id} 的确认结果")
            except Exception as e:
                print(f"[云计算中心] 通知医院端确认结果失败: {e}")

            return jsonify({
                'success': True,
                'message': '已确认接收环境参数，正在保存...'
            }), 200
        else:
            print(f"[云计算中心] 云计算中心 {cloud_id} 拒绝接收环境参数")

            # 通知医院端云计算中心的确认结果
            try:
                import requests as req
                req.post('http://127.0.0.1:5000/hospital/add_cloud_confirmation', json={
                    'cloud_id': cloud_id,
                    'accepted': accepted
                })
                print(f"[云计算中心] 已通知医院端云计算中心 {cloud_id} 的确认结果")
            except Exception as e:
                print(f"[云计算中心] 通知医院端确认结果失败: {e}")

            return jsonify({
                'success': True,
                'message': '已拒绝接收环境参数'
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/get_current_cloud_id', methods=['GET'])
def get_current_cloud_id():
    try:
        global current_cloud_id
        return jsonify({
            'success': True,
            'cloud_id': current_cloud_id
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/list_train_datasets', methods=['GET'])
def list_train_datasets():
    """获取可用的训练数据集对（匹配的_X.pkl和_y.pkl文件）"""
    try:
        cloud_dir = os.path.dirname(os.path.abspath(__file__))
        encrypted_dataset_dir = os.path.join(cloud_dir, 'encrypted_dataset')
        os.makedirs(encrypted_dataset_dir, exist_ok=True)
        
        files = os.listdir(encrypted_dataset_dir)
        
        # 找出所有 _encrypted_X.pkl 和 _y.pkl 文件
        x_files = []
        y_files = []
        
        for filename in files:
            if filename.endswith('_encrypted_X.pkl'):
                x_files.append(filename)
            elif filename.endswith('_y.pkl') and not filename.startswith('model_'):
                y_files.append(filename)
        
        # 匹配数据集名称
        datasets = []
        
        for x_file in x_files:
            # 提取数据集名称（去掉 _encrypted_X.pkl）
            dataset_name = x_file.replace('_encrypted_X.pkl', '')
            # 查找对应的 y 文件
            y_file = f'{dataset_name}_y.pkl'
            
            if y_file in y_files:
                datasets.append({
                    'name': dataset_name,
                    'x_file': x_file,
                    'y_file': y_file,
                    'matched': True
                })
            else:
                datasets.append({
                    'name': dataset_name,
                    'x_file': x_file,
                    'y_file': None,
                    'matched': False
                })
        
        return jsonify({
            'success': True,
            'datasets': datasets,
            'count': len(datasets)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/train_all', methods=['POST'])
def train_all():
    """一键训练所有可用的数据集"""
    try:
        # 导入必要的模块
        import gc
        
        # 导入 encrypted_train.py
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from encrypted_train import train_from_encrypted_data
        
        cloud_dir = os.path.dirname(os.path.abspath(__file__))
        keys_dir = os.path.join(cloud_dir, 'keys')
        
        # 查找公开上下文
        context_path = None
        for filename in os.listdir(keys_dir):
            if filename.endswith('_public.bin') or filename.endswith('_public.pkl') or 'context' in filename.lower():
                context_path = os.path.join(keys_dir, filename)
                break
        
        if not context_path:
            return jsonify({
                'success': False,
                'message': '未找到公开运算上下文，请先从医院端获取环境参数'
            }), 400
        
        # 获取所有匹配的数据集
        encrypted_dataset_dir = os.path.join(cloud_dir, 'encrypted_dataset')
        files = os.listdir(encrypted_dataset_dir)
        x_files = [f for f in files if f.endswith('_encrypted_X.pkl')]
        y_files = [f for f in files if f.endswith('_y.pkl') and not f.startswith('model_')]
        
        matched_datasets = []
        for x_file in x_files:
            ds_name = x_file.replace('_encrypted_X.pkl', '')
            y_file = f'{ds_name}_y.pkl'
            if y_file in y_files:
                matched_datasets.append(ds_name)
        
        if not matched_datasets:
            return jsonify({
                'success': False,
                'message': '未找到匹配的训练数据集'
            }), 400
        
        encrypted_models_dir = os.path.join(cloud_dir, 'encrypted_models')
        os.makedirs(encrypted_models_dir, exist_ok=True)
        
        # 依次训练每个数据集
        results = []
        total_time = 0
        
        for idx, dataset_name in enumerate(matched_datasets):
            print(f"[一键训练] [{idx+1}/{len(matched_datasets)}] 开始训练数据集: {dataset_name}")
            train_start_time = time.time()
            
            try:
                model_path = train_from_encrypted_data(
                    context_pub_path=context_path,
                    dataset_name=dataset_name,
                    data_dir=encrypted_dataset_dir,
                    model_dir=encrypted_models_dir,
                    lr=0.1,
                    gamma=0.9,
                    n_iters=3
                )
                
                train_duration = time.time() - train_start_time
                total_time += train_duration
                
                model_filename = os.path.basename(model_path)
                model_id = model_filename.replace('_encrypted_model.bin', '')
                
                train_record = {
                    'model_id': model_id,
                    'dataset_name': dataset_name,
                    'train_time': round(train_duration, 2),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                train_history.append(train_record)
                
                results.append({
                    'success': True,
                    'dataset_name': dataset_name,
                    'model_id': model_id,
                    'model_path': model_filename,
                    'train_time': round(train_duration, 2),
                    'train_time_formatted': f"{int(train_duration // 60)}分{int(train_duration % 60)}秒"
                })
                print(f"[一键训练] [{idx+1}/{len(matched_datasets)}] 训练完成: {dataset_name} ({round(train_duration, 2)}秒)")
                
            except Exception as e:
                print(f"[一键训练] [{idx+1}/{len(matched_datasets)}] 训练失败: {dataset_name} | 错误: {str(e)}")
                results.append({
                    'success': False,
                    'dataset_name': dataset_name,
                    'error': str(e)
                })
            
            # 清理内存和缓存
            gc.collect()
            time.sleep(0.1)
        
        # 保存训练历史
        try:
            import json
            with open(TRAIN_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(train_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 保存训练记录失败: {e}")
        
        success_count = sum(1 for r in results if r['success'])
        fail_count = len(results) - success_count
        
        return jsonify({
            'success': True,
            'message': f'批量训练完成！成功: {success_count} 个, 失败: {fail_count} 个',
            'total_time': round(total_time, 2),
            'total_time_formatted': f"{int(total_time // 60)}分{int(total_time % 60)}秒",
            'results': results,
            'total_count': len(matched_datasets),
            'success_count': success_count,
            'fail_count': fail_count
        }), 200
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] 批量训练失败: {error_msg}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/train', methods=['POST'])
def train():
    """使用 encrypted_train.py 进行密文训练"""
    try:
        data = request.json
        dataset_name = data.get('dataset_name')
        
        # 导入 encrypted_train.py
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from encrypted_train import train_from_encrypted_data
        
        # 设置路径
        cloud_dir = os.path.dirname(os.path.abspath(__file__))
        keys_dir = os.path.join(cloud_dir, 'keys')
        
        # 查找公开上下文
        context_path = None
        for filename in os.listdir(keys_dir):
            if filename.endswith('_public.bin') or filename.endswith('_public.pkl') or 'context' in filename.lower():
                context_path = os.path.join(keys_dir, filename)
                break
        
        if not context_path:
            return jsonify({
                'success': False,
                'message': '未找到公开运算上下文，请先从医院端获取环境参数'
            }), 400
        
        # 如果没有指定数据集名称，自动查找第一个匹配的数据集
        if not dataset_name:
            # 手动执行查询
            datasets = []
            try:
                encrypted_dataset_dir = os.path.join(cloud_dir, 'encrypted_dataset')
                files = os.listdir(encrypted_dataset_dir)
                x_files = [f for f in files if f.endswith('_encrypted_X.pkl')]
                y_files = [f for f in files if f.endswith('_y.pkl') and not f.startswith('model_')]
                
                for x_file in x_files:
                    ds_name = x_file.replace('_encrypted_X.pkl', '')
                    y_file = f'{ds_name}_y.pkl'
                    if y_file in y_files:
                        datasets.append({'name': ds_name, 'matched': True})
            except:
                pass
            
            matched_datasets = [d for d in datasets if d['matched']]
            
            if not matched_datasets:
                return jsonify({
                    'success': False,
                    'message': '未找到匹配的训练数据集（需要同时有 _encrypted_X.pkl 和 _y.pkl 文件）'
                }), 400
            
            dataset_name = matched_datasets[0]['name']
        
        # 创建必要的目录
        encrypted_dataset_dir = os.path.join(cloud_dir, 'encrypted_dataset')
        encrypted_models_dir = os.path.join(cloud_dir, 'encrypted_models')
        os.makedirs(encrypted_dataset_dir, exist_ok=True)
        os.makedirs(encrypted_models_dir, exist_ok=True)
        
        # 记录训练开始时间
        train_start_time = time.time()
        
        # 调用 encrypted_train.py 的训练函数
        model_path = train_from_encrypted_data(
            context_pub_path=context_path,
            dataset_name=dataset_name,
            data_dir=encrypted_dataset_dir,
            model_dir=encrypted_models_dir,
            lr=0.1,
            gamma=0.9,
            n_iters=3
        )
        
        # 计算训练耗时
        train_duration = time.time() - train_start_time
        
        model_filename = os.path.basename(model_path)
        model_id = model_filename.replace('_encrypted_model.bin', '')
        
        train_record = {
            'model_id': model_id,
            'dataset_name': dataset_name,
            'train_time': round(train_duration, 2),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        train_history.append(train_record)
        
        try:
            import json
            with open(TRAIN_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(train_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 保存训练记录失败: {e}")
        
        return jsonify({
            'success': True,
            'message': '密文模型训练完成',
            'model_id': model_id,
            'model_path': model_filename,
            'dataset_name': dataset_name,
            'train_time': round(train_duration, 2),
            'train_time_formatted': f"{int(train_duration // 60)}分{int(train_duration % 60)}秒"
        }), 200
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/predict', methods=['POST'])
def predict():
    """接收患者上传的加密查询向量，保存数据并放入队列等待确认（支持单样本和批量）"""
    try:
        data = request.json
        
        # 支持批量预测
        encrypted_features_list_hex = data.get('encrypted_features_list')
        encrypted_features_hex = data.get('encrypted_features')
        patient_id = data.get('patient_id', str(uuid.uuid4()))
        model_id = data.get('model_id')
        is_batch = data.get('is_batch', False)
        request_id = data.get('request_id')  # 用户自定义的请求ID
        
        # 确定是批量还是单样本
        if encrypted_features_list_hex:
            features_data = encrypted_features_list_hex
            is_batch = True
        elif encrypted_features_hex:
            features_data = [encrypted_features_hex]
            is_batch = False
        else:
            return jsonify({
                'success': False,
                'message': '未提供加密特征'
            }), 400
        
        # 检查模型是否存在
        cloud_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(cloud_dir, 'encrypted_models')
        
        if model_id:
            model_path = os.path.join(models_dir, f'{model_id}_encrypted_model.bin')
            if not os.path.exists(model_path):
                return jsonify({
                    'success': False,
                    'message': f'加密模型文件不存在: {model_id}_encrypted_model.bin'
                }), 400
        else:
            models = [f for f in os.listdir(models_dir) if f.endswith('_encrypted_model.bin')]
            if not models:
                return jsonify({
                    'success': False,
                    'message': '云端暂无加密模型，请先进行训练'
                }), 400
            model_id = models[0].replace('_encrypted_model.bin', '')
        
        # 创建预测申请记录（优先使用用户提供的请求ID）
        if not request_id or request_id.strip() == '':
            request_id = str(uuid.uuid4())[:8]
        
        # 保存患者上传的加密数据到文件
        import pickle
        uploads_dir = os.path.join(cloud_dir, 'encrypted_uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        upload_filename = f'{request_id}_{patient_id}_query.pkl'
        upload_path = os.path.join(uploads_dir, upload_filename)
        
        # 将 hex 转换为 bytes 并保存
        features_bytes_list = [bytes.fromhex(f) for f in features_data]
        with open(upload_path, 'wb') as f:
            pickle.dump(features_bytes_list, f)
        
        request_record = {
            'request_id': request_id,
            'patient_id': patient_id,
            'model_id': model_id,
            'encrypted_features': features_data,
            'upload_file': upload_filename,
            'is_batch': is_batch,
            'num_samples': len(features_data),
            'timestamp': time.time(),
            'status': 'pending'
        }
        
        global prediction_requests
        prediction_requests.append(request_record)
        
        if is_batch:
            print(f"[云计算中心] 接收到批量预测申请 | 请求ID: {request_id} | 患者ID: {patient_id} | 模型: {model_id} | 样本数: {len(features_data)}")
        else:
            print(f"[云计算中心] 接收到预测申请 | 请求ID: {request_id} | 患者ID: {patient_id} | 模型: {model_id}")
        print(f"[云计算中心] 加密数据已保存: {upload_path}")
        
        return jsonify({
            'success': True,
            'request_id': request_id,
            'patient_id': patient_id,
            'model_id': model_id,
            'is_batch': is_batch,
            'num_samples': len(features_data),
            'message': '预测申请已提交，数据已保存，请等待云计算中心确认'
        }), 200
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@cloud_bp.route('/list_prediction_requests', methods=['GET'])
def list_prediction_requests():
    """获取所有预测申请列表（包含所有状态）"""
    global prediction_requests
    
    return jsonify({
        'success': True,
        'requests': prediction_requests
    }), 200


@cloud_bp.route('/confirm_prediction', methods=['POST'])
def confirm_prediction():
    """确认并执行预测（支持单样本和批量）- 立即返回状态更新，后台异步执行预测"""
    try:
        data = request.json
        request_id = data.get('request_id')
        
        global prediction_requests
        request_index = None
        
        for i, req in enumerate(prediction_requests):
            if req['request_id'] == request_id and req['status'] == 'pending':
                request_index = i
                break
        
        if request_index is None:
            return jsonify({
                'success': False,
                'message': '未找到待确认的预测申请'
            }), 404
        
        request_record = prediction_requests[request_index]
        patient_id = request_record['patient_id']
        model_id = request_record['model_id']
        upload_file = request_record.get('upload_file')
        is_batch = request_record.get('is_batch', False)
        num_samples = request_record.get('num_samples', 1)
        
        # 更新状态为处理中
        prediction_requests[request_index]['status'] = 'processing'
        print(f"[云计算中心] 开始处理预测申请 | 请求ID: {request_id} | 状态: processing")
        
        # 立即返回响应，不阻塞服务器
        return jsonify({
            'success': True,
            'request_id': request_id,
            'message': '预测申请已接受，正在处理中...'
        }), 200
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def _execute_prediction_task(request_index, request_id, patient_id, model_id, upload_file, is_batch, num_samples):
    """后台执行的预测任务"""
    try:
        global prediction_requests
        
        # 设置路径
        cloud_dir = os.path.dirname(os.path.abspath(__file__))
        keys_dir = os.path.join(cloud_dir, 'keys')
        models_dir = os.path.join(cloud_dir, 'encrypted_models')
        uploads_dir = os.path.join(cloud_dir, 'encrypted_uploads')
        
        # 查找公开上下文
        context_path = None
        for filename in os.listdir(keys_dir):
            if filename.endswith('_public.bin') or 'context' in filename.lower():
                context_path = os.path.join(keys_dir, filename)
                break
        
        if not context_path:
            print(f"[云计算中心] 预测失败: 未找到公开运算上下文")
            prediction_requests[request_index]['status'] = 'failed'
            prediction_requests[request_index]['error'] = '未找到公开运算上下文'
            return
        
        # 获取 request_record
        request_record = prediction_requests[request_index]
        
        # 从保存的文件中加载加密数据
        if upload_file:
            upload_path = os.path.join(uploads_dir, upload_file)
            if os.path.exists(upload_path):
                import pickle
                with open(upload_path, 'rb') as f:
                    features_bytes_list = pickle.load(f)
                print(f"[云计算中心] 从文件加载加密数据: {upload_path}")
            else:
                features_bytes_list = [bytes.fromhex(f) for f in request_record['encrypted_features']]
                print("[云计算中心] 从内存加载加密数据")
        else:
            features_bytes_list = [bytes.fromhex(f) for f in request_record['encrypted_features']]
            print("[云计算中心] 从内存加载加密数据")
        
        # 调用 encrypted_predict.py 进行预测
        sys.path.insert(0, cloud_dir)
        from encrypted_predict import encrypted_predict
        
        # 设置预测结果保存目录
        predictions_dir = os.path.join(cloud_dir, 'encrypted_predictions')
        os.makedirs(predictions_dir, exist_ok=True)
        
        # 先生成 prediction_id，用于命名文件
        prediction_id = str(uuid.uuid4())[:8]
        
        result = encrypted_predict(
            public_ctx_path=context_path,
            model_dir=models_dir,
            dataset_name=model_id,
            query_list=features_bytes_list,
            output_dir=predictions_dir,
            patient_id=patient_id,
            prediction_id=prediction_id
        )
        
        encrypted_results_bytes = result['encrypted_results']
        encrypted_results_hex = [r.hex() for r in encrypted_results_bytes]
        
        prediction_filename = f"{patient_id}_{prediction_id}_{model_id}_encrypted_predictions.pkl"
        prediction_filepath = os.path.join(predictions_dir, prediction_filename)
        print(f"[云计算中心] 预测结果已保存到: {prediction_filepath}")
        
        # 更新申请状态
        prediction_requests[request_index]['status'] = 'completed'
        prediction_requests[request_index]['prediction_id'] = prediction_id
        prediction_requests[request_index]['encrypted_results'] = encrypted_results_hex
        prediction_requests[request_index]['encrypted_result'] = encrypted_results_hex[0] if encrypted_results_hex else None
        
        # 记录预测历史
        prediction_history.append({
            'prediction_id': prediction_id,
            'patient_id': patient_id,
            'model_id': model_id,
            'timestamp': time.time(),
            'encrypted_results': encrypted_results_hex,
            'encrypted_result': encrypted_results_hex[0] if encrypted_results_hex else None,
            'is_batch': is_batch,
            'num_samples': num_samples
        })
        
        if is_batch:
            print(f"[云计算中心] 批量预测确认并执行完成 | 请求ID: {request_id} | 患者ID: {patient_id} | 模型: {model_id} | 样本数: {num_samples}")
        else:
            print(f"[云计算中心] 预测确认并执行完成 | 请求ID: {request_id} | 患者ID: {patient_id} | 模型: {model_id}")
        
        # 自动将预测结果文件和信息发送给医院端
        try:
            import requests as req
            
            # 读取预测结果文件
            with open(prediction_filepath, 'rb') as f:
                prediction_file_data = f.read()
            
            # 发送文件到医院端
            hospital_response = req.post(
                'http://127.0.0.1:5000/hospital/receive_prediction_file',
                files={'file': (prediction_filename, prediction_file_data, 'application/octet-stream')},
                data={
                    'patient_id': patient_id,
                    'prediction_id': prediction_id,
                    'model_id': model_id,
                    'is_batch': is_batch,
                    'num_samples': num_samples
                },
                timeout=30
            )
            if hospital_response.status_code == 200:
                print(f"[云计算中心] 预测结果已成功发送给医院端")
            else:
                print(f"[云计算中心] 发送预测结果到医院端失败: {hospital_response.status_code}")
        except Exception as e:
            print(f"[云计算中心] 发送预测结果到医院端时出错: {e}")
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] 预测任务执行失败: {error_msg}")
        prediction_requests[request_index]['status'] = 'failed'
        prediction_requests[request_index]['error'] = str(e)


@cloud_bp.route('/start_prediction_task', methods=['POST'])
def start_prediction_task():
    """启动后台预测任务（实际执行预测）"""
    try:
        import threading
        
        data = request.json
        request_id = data.get('request_id')
        
        global prediction_requests
        request_index = None
        request_record = None
        
        for i, req in enumerate(prediction_requests):
            if req['request_id'] == request_id:
                request_index = i
                request_record = req
                break
        
        if request_index is None:
            return jsonify({
                'success': False,
                'message': '未找到预测申请'
            }), 404
        
        if request_record['status'] != 'processing':
            return jsonify({
                'success': False,
                'message': f'预测申请状态不是 processing，当前状态: {request_record["status"]}'
            }), 400
        
        # 启动后台线程执行预测
        thread = threading.Thread(
            target=_execute_prediction_task,
            args=(
                request_index,
                request_record['request_id'],
                request_record['patient_id'],
                request_record['model_id'],
                request_record.get('upload_file'),
                request_record.get('is_batch', False),
                request_record.get('num_samples', 1)
            )
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': '预测任务已启动'
        }), 200
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@cloud_bp.route('/reject_prediction', methods=['POST'])
def reject_prediction():
    """拒绝预测申请"""
    try:
        data = request.json
        request_id = data.get('request_id')
        
        global prediction_requests
        request_index = None
        
        for i, req in enumerate(prediction_requests):
            if req['request_id'] == request_id and req['status'] == 'pending':
                request_index = i
                break
        
        if request_index is None:
            return jsonify({
                'success': False,
                'message': '未找到待确认的预测申请'
            }), 404
        
        prediction_requests[request_index]['status'] = 'rejected'
        
        print(f"[云计算中心] 预测申请已拒绝 | 请求ID: {request_id}")
        
        return jsonify({
            'success': True,
            'request_id': request_id,
            'message': '预测申请已拒绝'
        }), 200
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@cloud_bp.route('/check_key_update', methods=['GET'])
def check_key_update():
    """检查是否需要更新密钥（医院端密钥更新后通知）"""
    global key_update_notified
    return jsonify({
        'success': True,
        'key_update_notified': key_update_notified
    }), 200


@cloud_bp.route('/reset_key_update_notification', methods=['POST'])
def reset_key_update_notification():
    """重置密钥更新通知标志"""
    global key_update_notified
    key_update_notified = False
    return jsonify({
        'success': True,
        'message': '密钥更新通知已重置'
    }), 200


@cloud_bp.route('/predict_batch', methods=['POST'])
def predict_batch():
    """接收患者上传的批量加密查询，使用加密模型进行批量密文预测"""
    try:
        data = request.json
        encrypted_features_list_hex = data.get('encrypted_features_list', [])
        patient_id = data.get('patient_id', 'batch_test')
        model_id = data.get('model_id')
        
        if not encrypted_features_list_hex:
            return jsonify({
                'success': False,
                'message': '未提供加密特征列表'
            }), 400
        
        # 设置路径
        cloud_dir = os.path.dirname(os.path.abspath(__file__))
        keys_dir = os.path.join(cloud_dir, 'keys')
        models_dir = os.path.join(cloud_dir, 'encrypted_models')
        
        # 查找公开上下文
        context_path = None
        for filename in os.listdir(keys_dir):
            if filename.endswith('_public.bin') or 'context' in filename.lower():
                context_path = os.path.join(keys_dir, filename)
                break
        
        if not context_path:
            return jsonify({
                'success': False,
                'message': '未找到公开运算上下文，请先从医院端获取环境参数'
            }), 400
        
        # 加载公开上下文
        with open(context_path, 'rb') as f:
            context = ts.context_from(f.read())
        
        # 加载加密模型
        if model_id:
            model_path = os.path.join(models_dir, f'{model_id}_encrypted_model.bin')
        else:
            # 自动选择第一个模型
            models = [f for f in os.listdir(models_dir) if f.endswith('_encrypted_model.bin')]
            if not models:
                return jsonify({
                    'success': False,
                    'message': '云端暂无加密模型，请先进行训练'
                }), 400
            model_path = os.path.join(models_dir, models[0])
        
        if not os.path.exists(model_path):
            return jsonify({
                'success': False,
                'message': f'加密模型文件不存在: {os.path.basename(model_path)}'
            }), 400
        
        with open(model_path, 'rb') as f:
            enc_w = ts.ckks_vector_from(context, f.read())
        
        # 反序列化所有加密查询向量
        enc_x_list = []
        for enc_hex in encrypted_features_list_hex:
            enc_x = ts.ckks_vector_from(context, bytes.fromhex(enc_hex))
            enc_x_list.append(enc_x)
        
        print(f"[云计算中心] 开始批量密文预测 | 样本数: {len(enc_x_list)} | 模型: {model_id}")
        
        # 批量同态预测
        enc_prob_list = []
        for enc_x in enc_x_list:
            enc_z = enc_x.dot(enc_w)
            enc_prob = enc_z * 0.125 + 0.5
            enc_prob_list.append(enc_prob)
        
        # 序列化结果
        enc_prob_hex_list = [enc_prob.serialize().hex() for enc_prob in enc_prob_list]
        
        prediction_id = str(uuid.uuid4())[:8]
        model_name = os.path.basename(model_path).replace('_encrypted_model.bin', '')
        
        # 记录预测历史（只记录一条，因为是批量）
        prediction_record = {
            'prediction_id': prediction_id,
            'patient_id': patient_id,
            'model_id': model_name,
            'timestamp': time.time(),
            'is_batch': True,
            'num_samples': len(enc_prob_hex_list)
        }
        prediction_history.append(prediction_record)
        
        print(f"[云计算中心] 批量密文预测完成 | 样本数: {len(enc_prob_hex_list)} | 预测ID: {prediction_id}")
        
        return jsonify({
            'success': True,
            'prediction_id': prediction_id,
            'encrypted_results': enc_prob_hex_list,
            'patient_id': patient_id,
            'model_id': model_name,
            'num_samples': len(enc_prob_hex_list)
        }), 200
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/list_prediction_history', methods=['GET'])
def list_prediction_history():
    """获取预测历史记录"""
    try:
        return jsonify({
            'success': True,
            'predictions': prediction_history[-20:],  # 返回最近20条
            'count': len(prediction_history)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@cloud_bp.route('/list_train_history', methods=['GET'])
def list_train_history():
    """获取训练历史记录"""
    try:
        global train_history
        
        if os.path.exists(TRAIN_HISTORY_FILE):
            try:
                import json
                with open(TRAIN_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    train_history = json.load(f)
            except Exception as e:
                print(f"[WARN] 加载训练历史失败: {e}")
        
        return jsonify({
            'success': True,
            'train_history': train_history,
            'count': len(train_history)
        }), 200
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/clear_prediction_history', methods=['POST'])
def clear_prediction_history():
    """清空预测历史记录"""
    try:
        global prediction_history
        prediction_history = []
        return jsonify({
            'success': True,
            'message': '预测历史已清空'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/list_models', methods=['GET'])
def get_models():
    """获取已训练的加密模型列表"""
    try:
        cloud_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(cloud_dir, 'encrypted_models')
        os.makedirs(models_dir, exist_ok=True)
        
        models = [f for f in os.listdir(models_dir) if f.endswith('_encrypted_model.bin')]
        models = sorted(models, reverse=True)
        
        return jsonify({
            'success': True,
            'models': models,
            'count': len(models)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/list_train_files', methods=['GET'])
def get_train_files():
    """获取可用的训练数据文件列表"""
    try:
        cloud_dir = os.path.dirname(os.path.abspath(__file__))
        dataset_dir = os.path.join(cloud_dir, 'encrypted_dataset')
        os.makedirs(dataset_dir, exist_ok=True)
        
        files = [f for f in os.listdir(dataset_dir) if f.endswith('.pkl')]
        files = sorted(files)
        
        return jsonify({
            'success': True,
            'train_files': files,
            'count': len(files)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@cloud_bp.route('/status', methods=['GET'])
def get_status():
    """获取云端服务状态"""
    try:
        cloud_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(cloud_dir, 'encrypted_models')
        dataset_dir = os.path.join(cloud_dir, 'encrypted_dataset')
        keys_dir = os.path.join(cloud_dir, 'keys')
        
        models_count = len([f for f in os.listdir(models_dir) if f.endswith('_encrypted_model.bin')]) if os.path.exists(models_dir) else 0
        dataset_count = len([f for f in os.listdir(dataset_dir) if f.endswith('.pkl')]) if os.path.exists(dataset_dir) else 0
        has_context = os.path.exists(os.path.join(keys_dir, 'cloud_ckks_context_public.bin'))
        
        return jsonify({
            'success': True,
            'status': '服务正常运行中' if has_context else '未配置环境参数',
            'has_context': has_context,
            'models_count': models_count,
            'dataset_count': dataset_count
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
