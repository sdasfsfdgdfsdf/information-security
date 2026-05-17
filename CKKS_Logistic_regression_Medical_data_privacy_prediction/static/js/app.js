// 全局变量
let patientData = {
    predictionId: '',
    encryptedResult: '',
    patientId: ''
};

// ==========================================
// 页面导航
// ==========================================
function showPage(pageName) {
    // 隐藏所有页面
    document.querySelectorAll('.page').forEach(page => {
        page.classList.add('hidden');
    });

    // 显示目标页面
    document.getElementById(pageName + '-page').classList.remove('hidden');

    // 更新导航状态
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        if (link.dataset.page === pageName) {
            link.classList.add('active');
        }
    });

    // 页面特定初始化
    if (pageName === 'patient') {
        startPatientApplicationPolling();
        patientLoadNormParamsList();
        patientLoadDataFiles();
        patientLoadModels();
    } else if (pageName === 'hospital') {
        startHospitalApplicationPolling();
        hospitalCheckApplications();
        hospitalLoadDataFiles();
        hospitalLoadEncryptedFiles();
        hospitalLoadDecryptRequests();
    } else if (pageName === 'cloud') {
        startCloudApplicationPolling();
        cloudRefreshStatus();
        cloudLoadModels();
        cloudLoadDatasets();
        startCloudContextCheck();
    }
}

// ==========================================
// 工具函数
// ==========================================
function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('zh-CN', { hour12: false });
}

function addLog(logId, message, icon = '📋') {
    const logContainer = document.getElementById(logId);
    const logItem = document.createElement('div');
    logItem.className = 'log-entry log-info';
    const timestamp = new Date().toLocaleTimeString('zh-CN');
    logItem.innerHTML = `[${timestamp}] ${icon} ${message}`;
    logContainer.appendChild(logItem);
    logContainer.scrollTop = logContainer.scrollHeight;
}

function showResult(elementId, html, isSuccess = true) {
    const el = document.getElementById(elementId);
    el.classList.remove('hidden');
    el.innerHTML = html;
}

// ==========================================
// 患者端功能
// ==========================================
// 患者端申请公钥
async function patientApplyPublicKey() {
    const patientId = document.getElementById('patient-apply-id').value.trim();

    if (!patientId) {
        showResult('patient-apply-status', '<p><strong>⚠️ 请输入患者ID</strong></p>', false);
        addLog('patient-log', '申请公钥失败：未输入患者ID', '⚠️');
        return;
    }

    try {
        addLog('patient-log', `正在向医院端申请公钥（患者ID: ${patientId}）...`, '🔑');

        const response = await fetch('/patient/apply_public_key', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ patient_id: patientId })
        });

        const data = await response.json();

        if (data.success) {
            showResult('patient-apply-status', `
                <p><strong>✅ 申请已发送!</strong></p>
                <p>患者ID: ${patientId}</p>
                <p>等待医院端审核...</p>
            `, true);

            addLog('patient-log', '公钥申请已发送，等待医院端审核', '⏳');
        } else {
            showResult('patient-apply-status', `<p><strong>❌ 失败:</strong> ${data.message}</p>`, false);
            addLog('patient-log', '申请失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('patient-apply-status', `<p><strong>❌ 错误:</strong> ${error.message}</p>`, false);
        addLog('patient-log', '申请时出错: ' + error.message, '❌');
    }
}

// 患者端轮询检查医院申请响应
let patientApplicationPollingInterval = null;
function startPatientApplicationPolling() {
    if (patientApplicationPollingInterval) clearInterval(patientApplicationPollingInterval);

    patientApplicationPollingInterval = setInterval(async () => {
        try {
            const response = await fetch('/patient/check_hospital_response');
            const data = await response.json();

            if (data.success && data.has_response) {
                clearInterval(patientApplicationPollingInterval);
                patientApplicationPollingInterval = null;

                if (data.approved) {
                    addLog('patient-log', '医院端已批准申请', '✅');
                    showResult('patient-apply-status', `
                        <p><strong>✅ 申请已批准!</strong></p>
                        <p>公钥已下载到本地</p>
                    `, true);
                } else {
                    addLog('patient-log', '医院端已拒绝申请', '❌');
                    showResult('patient-apply-status', `
                        <p><strong>❌ 申请被拒绝!</strong></p>
                        <p>原因: ${data.reason}</p>
                    `, false);
                }
            }
        } catch (error) {
            console.error('轮询检查医院响应失败:', error);
        }
    }, 3000);
}

// 加载标准化参数列表
async function patientLoadNormParamsList() {
    try {
        const response = await fetch('/hospital/list_norm_params');
        const data = await response.json();
        
        if (data.success && data.files) {
            const container = document.getElementById('patient-norm-params-list');
            container.innerHTML = '';
            
            if (data.files.length === 0) {
                container.innerHTML = '<div style="color: #8c8c8c;">暂无标准化参数文件...</div>';
                return;
            }
            
            data.files.forEach(file => {
                const div = document.createElement('div');
                div.style.padding = '5px';
                div.style.marginBottom = '5px';
                div.style.border = '1px solid #ddd';
                div.style.borderRadius = '4px';
                div.style.cursor = 'pointer';
                div.dataset.file = file;
                div.innerHTML = `<span>📄 ${file}</span>`;
                div.onclick = function() {
                    document.querySelectorAll('#patient-norm-params-list div').forEach(el => {
                        el.style.backgroundColor = 'white';
                    });
                    div.style.backgroundColor = '#e3f2fd';
                };
                container.appendChild(div);
            });
        }
    } catch (error) {
        addLog('patient-log', '加载标准化参数列表失败: ' + error.message, '❌');
    }
}

// 加载标准化参数
async function patientLoadNormParams() {
    try {
        const selectedFile = document.querySelector('#patient-norm-params-list div[style*="background-color: rgb(227, 242, 253)"]');
        if (!selectedFile) {
            addLog('patient-log', '请先选择一个标准化参数文件', '⚠️');
            return;
        }
        
        const fileName = selectedFile.dataset.file;
        addLog('patient-log', `正在加载标准化参数: ${fileName}`, '📊');
        
        const response = await fetch(`/hospital/download_norm_params?filename=${encodeURIComponent(fileName)}`);
        const data = await response.json();
        
        if (data.success) {
            showResult('patient-norm-params-result', `
                <p><strong>✅ 加载成功!</strong></p>
                <p>文件名: ${fileName}</p>
            `, true);
            addLog('patient-log', '标准化参数加载成功', '✅');
        } else {
            showResult('patient-norm-params-result', `<p><strong>❌ 加载失败:</strong> ${data.message}</p>`, false);
            addLog('patient-log', '标准化参数加载失败: ' + data.message, '❌');
        }
    } catch (error) {
        addLog('patient-log', '加载标准化参数出错: ' + error.message, '❌');
    }
}

// 加载患者数据文件列表
async function patientLoadDataFiles() {
    try {
        const response = await fetch('/patient/list_csv_files');
        const data = await response.json();
        
        if (data.success && data.files) {
            const container = document.getElementById('patient-csv-list');
            container.innerHTML = '';
            
            if (data.files.length === 0) {
                container.innerHTML = '<div style="color: #8c8c8c;">暂无CSV文件...</div>';
                return;
            }
            
            data.files.forEach(file => {
                const div = document.createElement('div');
                div.style.padding = '5px';
                div.style.marginBottom = '5px';
                div.style.border = '1px solid #ddd';
                div.style.borderRadius = '4px';
                div.innerHTML = `<span>📄 ${file}</span>`;
                container.appendChild(div);
            });
            
            const select = document.getElementById('patient-csv-select');
            select.innerHTML = '<option value="">请选择CSV文件...</option>';
            data.files.forEach(file => {
                const option = document.createElement('option');
                option.value = file;
                option.textContent = file;
                select.appendChild(option);
            });
        }
    } catch (error) {
        addLog('patient-log', '加载CSV文件列表失败: ' + error.message, '❌');
    }
}

// 加密查询数据
async function patientEncryptData() {
    const csvFile = document.getElementById('patient-csv-select').value;
    const patientId = document.getElementById('patient-encrypt-id').value.trim();
    const requestId = document.getElementById('patient-encrypt-request-id').value.trim();

    if (!csvFile) {
        addLog('patient-log', '请选择要加密的CSV文件', '⚠️');
        return;
    }

    if (!patientId) {
        addLog('patient-log', '请输入患者ID', '⚠️');
        return;
    }

    try {
        addLog('patient-log', `正在加密数据文件: ${csvFile}`, '🔐');

        const response = await fetch('/patient/encrypt_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                csv_file: csvFile, 
                patient_id: patientId,
                request_id: requestId
            })
        });

        const data = await response.json();

        if (data.success) {
            showResult('patient-encrypt-status', `
                <p><strong>✅ 加密成功!</strong></p>
                <p>请求ID: ${data.request_id}</p>
            `, true);
            addLog('patient-log', '数据加密成功', '✅');
            
            document.getElementById('patient-request-id').value = data.request_id;
        } else {
            showResult('patient-encrypt-status', `<p><strong>❌ 加密失败:</strong> ${data.message}</p>`, false);
            addLog('patient-log', '数据加密失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('patient-encrypt-status', `<p><strong>❌ 加密出错:</strong> ${error.message}</p>`, false);
        addLog('patient-log', '加密数据出错: ' + error.message, '❌');
    }
}

// 加载模型列表
async function patientLoadModels() {
    try {
        const response = await fetch('/cloud/list_models');
        const data = await response.json();
        
        if (data.success && data.models) {
            const select = document.getElementById('patient-model-select');
            select.innerHTML = '<option value="">请选择模型...</option>';
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                select.appendChild(option);
            });
            
            const decryptSelect = document.getElementById('patient-decrypt-model-select');
            decryptSelect.innerHTML = '<option value="">请选择模型...</option>';
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                decryptSelect.appendChild(option);
            });
        }
    } catch (error) {
        addLog('patient-log', '加载模型列表失败: ' + error.message, '❌');
    }
}

// 发送预测请求
async function patientRequestPredict() {
    const requestId = document.getElementById('patient-request-id').value.trim();
    const patientId = document.getElementById('patient-predict-id').value.trim();
    const modelName = document.getElementById('patient-model-select').value;

    if (!requestId) {
        addLog('patient-log', '请输入请求ID', '⚠️');
        return;
    }

    if (!patientId) {
        addLog('patient-log', '请输入患者ID', '⚠️');
        return;
    }

    if (!modelName) {
        addLog('patient-log', '请选择模型', '⚠️');
        return;
    }

    try {
        addLog('patient-log', '正在发送预测请求...', '📝');

        const response = await fetch('/patient/request_prediction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                request_id: requestId,
                patient_id: patientId,
                model_name: modelName
            })
        });

        const data = await response.json();

        if (data.success) {
            showResult('patient-predict-status', `
                <p><strong>✅ 预测请求已发送!</strong></p>
                <p>请求ID: ${data.request_id}</p>
                <p>模型: ${modelName}</p>
                <p>等待云计算中心处理...</p>
            `, true);
            addLog('patient-log', '预测请求已发送，等待处理', '⏳');
        } else {
            showResult('patient-predict-status', `<p><strong>❌ 失败:</strong> ${data.message}</p>`, false);
            addLog('patient-log', '预测请求失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('patient-predict-status', `<p><strong>❌ 错误:</strong> ${error.message}</p>`, false);
        addLog('patient-log', '发送预测请求出错: ' + error.message, '❌');
    }
}

// 检查预测状态
async function patientCheckStatus() {
    const requestId = document.getElementById('patient-check-id').value.trim();

    if (!requestId) {
        addLog('patient-log', '请输入请求ID', '⚠️');
        return;
    }

    try {
        addLog('patient-log', `正在检查预测状态（请求ID: ${requestId}）...`, '🔍');

        const response = await fetch(`/patient/check_prediction_status?request_id=${requestId}`);
        const data = await response.json();

        if (data.success) {
            let statusHtml = `<p><strong>请求ID:</strong> ${requestId}</p>`;
            statusHtml += `<p><strong>状态:</strong> ${data.status}</p>`;
            
            if (data.prediction_id) {
                statusHtml += `<p><strong>预测ID:</strong> ${data.prediction_id}</p>`;
                patientData.predictionId = data.prediction_id;
                document.getElementById('patient-decrypt-prediction-id').value = data.prediction_id;
            }
            
            showResult('patient-predict-progress', statusHtml, true);
            addLog('patient-log', `当前状态: ${data.status}`, 'ℹ️');
        } else {
            showResult('patient-predict-progress', `<p><strong>❌ 检查失败:</strong> ${data.message}</p>`, false);
            addLog('patient-log', '检查状态失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('patient-predict-progress', `<p><strong>❌ 错误:</strong> ${error.message}</p>`, false);
        addLog('patient-log', '检查状态出错: ' + error.message, '❌');
    }
}

// 清空字段
function patientClearFields() {
    document.getElementById('patient-apply-id').value = '';
    document.getElementById('patient-encrypt-id').value = '';
    document.getElementById('patient-encrypt-request-id').value = '';
    document.getElementById('patient-request-id').value = '';
    document.getElementById('patient-predict-id').value = '';
    document.getElementById('patient-check-id').value = '';
    document.getElementById('patient-decrypt-id').value = '';
    document.getElementById('patient-decrypt-prediction-id').value = '';
    patientData.predictionId = '';
    addLog('patient-log', '已清空所有输入字段', 'ℹ️');
}

// 申请解密预测结果
async function patientRequestDecrypt() {
    const patientId = document.getElementById('patient-decrypt-id').value.trim();
    const predictionId = document.getElementById('patient-decrypt-prediction-id').value.trim();
    const modelName = document.getElementById('patient-decrypt-model-select').value;

    if (!patientId) {
        addLog('patient-log', '请输入患者ID', '⚠️');
        return;
    }

    if (!predictionId) {
        addLog('patient-log', '请输入预测ID', '⚠️');
        return;
    }

    if (!modelName) {
        addLog('patient-log', '请选择模型', '⚠️');
        return;
    }

    try {
        addLog('patient-log', '正在向医院端申请解密...', '🔓');

        const response = await fetch('/patient/request_decrypt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                patient_id: patientId,
                prediction_id: predictionId,
                model_name: modelName
            })
        });

        const data = await response.json();

        if (data.success) {
            showResult('patient-decrypt-status', `
                <p><strong>✅ 解密申请已发送!</strong></p>
                <p>患者ID: ${patientId}</p>
                <p>预测ID: ${predictionId}</p>
                <p>等待医院端审核...</p>
            `, true);
            addLog('patient-log', '解密申请已发送，等待审核', '⏳');
        } else {
            showResult('patient-decrypt-status', `<p><strong>❌ 失败:</strong> ${data.message}</p>`, false);
            addLog('patient-log', '解密申请失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('patient-decrypt-status', `<p><strong>❌ 错误:</strong> ${error.message}</p>`, false);
        addLog('patient-log', '发送解密申请出错: ' + error.message, '❌');
    }
}

// ==========================================
// 医院端功能
// ==========================================
// 医院端生成密钥
async function hospitalGenerateKeys() {
    try {
        addLog('hospital-log', '正在生成CKKS密钥对...', '🔑');

        const response = await fetch('/hospital/generate_keys', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showResult('hospital-key-status', `
                <p><strong>✅ 密钥对生成成功!</strong></p>
                <p>私钥已保存到医院端</p>
                <p>公钥已准备好供患者下载</p>
            `, true);
            addLog('hospital-log', 'CKKS密钥对生成成功', '✅');
        } else {
            showResult('hospital-key-status', `<p><strong>❌ 生成失败:</strong> ${data.message}</p>`, false);
            addLog('hospital-log', '密钥生成失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('hospital-key-status', `<p><strong>❌ 错误:</strong> ${error.message}</p>`, false);
        addLog('hospital-log', '生成密钥出错: ' + error.message, '❌');
    }
}

// 医院端轮询检查患者申请
let hospitalApplicationPollingInterval = null;
function startHospitalApplicationPolling() {
    if (hospitalApplicationPollingInterval) clearInterval(hospitalApplicationPollingInterval);

    hospitalApplicationPollingInterval = setInterval(async () => {
        try {
            const response = await fetch('/hospital/check_patient_applications');
            const data = await response.json();

            if (data.success && data.applications) {
                const container = document.getElementById('hospital-apply-list');
                container.innerHTML = '';
                
                if (data.applications.length === 0) {
                    container.innerHTML = '<div style="color: #8c8c8c;">暂无申请记录...</div>';
                } else {
                    data.applications.forEach(app => {
                        const div = document.createElement('div');
                        div.style.padding = '8px';
                        div.style.marginBottom = '5px';
                        div.style.border = '1px solid #ddd';
                        div.style.borderRadius = '4px';
                        div.innerHTML = `
                            <div><strong>患者ID:</strong> ${app.patient_id}</div>
                            <div><strong>时间:</strong> ${app.timestamp}</div>
                            <div><strong>状态:</strong> ${app.status}</div>
                        `;
                        container.appendChild(div);
                    });
                }
            }
        } catch (error) {
            console.error('轮询检查患者申请失败:', error);
        }
    }, 5000);
}

// 加载医院数据文件列表
async function hospitalLoadDataFiles() {
    try {
        const response = await fetch('/hospital/list_data_files');
        const data = await response.json();
        
        if (data.success && data.files) {
            const container = document.getElementById('hospital-data-list');
            container.innerHTML = '';
            
            if (data.files.length === 0) {
                container.innerHTML = '<div style="color: #8c8c8c;">暂无CSV文件...</div>';
                return;
            }
            
            data.files.forEach(file => {
                const div = document.createElement('div');
                div.style.padding = '5px';
                div.style.marginBottom = '5px';
                div.style.border = '1px solid #ddd';
                div.style.borderRadius = '4px';
                div.innerHTML = `<span>📄 ${file}</span>`;
                container.appendChild(div);
            });
            
            const select = document.getElementById('hospital-data-select');
            select.innerHTML = '<option value="">请选择CSV文件...</option>';
            data.files.forEach(file => {
                const option = document.createElement('option');
                option.value = file;
                option.textContent = file;
                select.appendChild(option);
            });
        }
    } catch (error) {
        addLog('hospital-log', '加载CSV文件列表失败: ' + error.message, '❌');
    }
}

// 加密数据集
async function hospitalEncryptData() {
    const csvFile = document.getElementById('hospital-data-select').value;

    if (!csvFile) {
        addLog('hospital-log', '请选择要加密的CSV文件', '⚠️');
        return;
    }

    try {
        addLog('hospital-log', `正在加密数据文件: ${csvFile}`, '🔐');

        const response = await fetch('/hospital/encrypt_datasets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filenames: [csvFile] })
        });

        const data = await response.json();

        if (data.success) {
            showResult('hospital-encrypt-status', `
                <p><strong>✅ 加密成功!</strong></p>
                <p>成功加密: ${data.encrypted_files_info.length} 个数据集</p>
            `, true);
            addLog('hospital-log', '数据加密成功', '✅');
            
            hospitalLoadEncryptedFiles();
        } else {
            showResult('hospital-encrypt-status', `<p><strong>❌ 加密失败:</strong> ${data.message}</p>`, false);
            addLog('hospital-log', '数据加密失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('hospital-encrypt-status', `<p><strong>❌ 加密出错:</strong> ${error.message}</p>`, false);
        addLog('hospital-log', '加密数据出错: ' + error.message, '❌');
    }
}

// 加载已加密文件列表
async function hospitalLoadEncryptedFiles() {
    try {
        const response = await fetch('/hospital/list_encrypted_files');
        const data = await response.json();
        
        if (data.success && data.files) {
            const container = document.getElementById('hospital-encrypted-list');
            container.innerHTML = '';
            
            if (data.files.length === 0) {
                container.innerHTML = '<div style="color: #8c8c8c;">暂无加密文件...</div>';
                return;
            }
            
            data.files.forEach(file => {
                const div = document.createElement('div');
                div.style.padding = '5px';
                div.style.marginBottom = '5px';
                div.style.border = '1px solid #ddd';
                div.style.borderRadius = '4px';
                div.innerHTML = `<span>🔒 ${file}</span>`;
                container.appendChild(div);
            });
            
            const select = document.getElementById('hospital-encrypted-select');
            select.innerHTML = '<option value="">请选择加密文件...</option>';
            data.files.forEach(file => {
                const option = document.createElement('option');
                option.value = file;
                option.textContent = file;
                select.appendChild(option);
            });
        }
    } catch (error) {
        addLog('hospital-log', '加载加密文件列表失败: ' + error.message, '❌');
    }
}

// 上传加密数据到云端
async function hospitalUploadEncrypted() {
    const encryptedFile = document.getElementById('hospital-encrypted-select').value;

    if (!encryptedFile) {
        addLog('hospital-log', '请选择要上传的加密文件', '⚠️');
        return;
    }

    try {
        addLog('hospital-log', `正在上传加密数据到云端: ${encryptedFile}`, '☁️');

        const response = await fetch('/hospital/upload_encrypted_dataset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: encryptedFile })
        });

        const data = await response.json();

        if (data.success) {
            showResult('hospital-upload-status', `
                <p><strong>✅ 上传成功!</strong></p>
                <p>文件名: ${data.filename}</p>
            `, true);
            addLog('hospital-log', '加密数据上传成功', '✅');
        } else {
            showResult('hospital-upload-status', `<p><strong>❌ 上传失败:</strong> ${data.message}</p>`, false);
            addLog('hospital-log', '上传失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('hospital-upload-status', `<p><strong>❌ 上传出错:</strong> ${error.message}</p>`, false);
        addLog('hospital-log', '上传数据出错: ' + error.message, '❌');
    }
}

// 加载解密申请列表
async function hospitalLoadDecryptRequests() {
    try {
        const response = await fetch('/hospital/list_decrypt_requests');
        const data = await response.json();
        
        if (data.success && data.requests) {
            const container = document.getElementById('hospital-decrypt-list');
            container.innerHTML = '';
            
            if (data.requests.length === 0) {
                container.innerHTML = '<div style="color: #8c8c8c;">暂无解密申请...</div>';
                return;
            }
            
            data.requests.forEach(req => {
                const div = document.createElement('div');
                div.style.padding = '8px';
                div.style.marginBottom = '5px';
                div.style.border = '1px solid #ddd';
                div.style.borderRadius = '4px';
                div.style.backgroundColor = req.status === 'pending' ? '#fff3cd' : '#d4edda';
                div.innerHTML = `
                    <div><strong>患者ID:</strong> ${req.patient_id}</div>
                    <div><strong>预测ID:</strong> ${req.prediction_id}</div>
                    <div><strong>模型:</strong> ${req.model_name}</div>
                    <div><strong>时间:</strong> ${req.timestamp}</div>
                    <div><strong>状态:</strong> ${req.status}</div>
                `;
                container.appendChild(div);
            });
        }
    } catch (error) {
        addLog('hospital-log', '加载解密申请列表失败: ' + error.message, '❌');
    }
}

// 解密预测结果
async function hospitalDecryptPrediction() {
    try {
        addLog('hospital-log', '正在解密预测结果...', '🔓');

        const response = await fetch('/hospital/decrypt_prediction', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showResult('hospital-decrypt-status', `
                <p><strong>✅ 解密成功!</strong></p>
                <p>预测结果已解密</p>
            `, true);
            addLog('hospital-log', '预测结果解密成功', '✅');
            
            hospitalLoadDecryptRequests();
        } else {
            showResult('hospital-decrypt-status', `<p><strong>❌ 解密失败:</strong> ${data.message}</p>`, false);
            addLog('hospital-log', '解密失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('hospital-decrypt-status', `<p><strong>❌ 解密出错:</strong> ${error.message}</p>`, false);
        addLog('hospital-log', '解密出错: ' + error.message, '❌');
    }
}

// ==========================================
// 云计算中心功能
// ==========================================
// 云计算中心轮询检查申请
let cloudApplicationPollingInterval = null;
function startCloudApplicationPolling() {
    if (cloudApplicationPollingInterval) clearInterval(cloudApplicationPollingInterval);

    cloudApplicationPollingInterval = setInterval(async () => {
        try {
            const response = await fetch('/cloud/check_prediction_requests');
            const data = await response.json();

            if (data.success && data.requests) {
                const container = document.getElementById('cloud-prediction-list');
                container.innerHTML = '';
                
                if (data.requests.length === 0) {
                    container.innerHTML = '<div style="color: #8c8c8c;">暂无预测请求...</div>';
                } else {
                    data.requests.forEach(req => {
                        const div = document.createElement('div');
                        div.style.padding = '8px';
                        div.style.marginBottom = '5px';
                        div.style.border = '1px solid #ddd';
                        div.style.borderRadius = '4px';
                        let bgColor = '#fff3cd';
                        if (req.status === 'processing') bgColor = '#cce5ff';
                        if (req.status === 'completed') bgColor = '#d4edda';
                        div.style.backgroundColor = bgColor;
                        div.innerHTML = `
                            <div><strong>请求ID:</strong> ${req.request_id}</div>
                            <div><strong>患者ID:</strong> ${req.patient_id}</div>
                            <div><strong>模型:</strong> ${req.model_name}</div>
                            <div><strong>状态:</strong> ${req.status}</div>
                        `;
                        container.appendChild(div);
                    });
                }
            }
        } catch (error) {
            console.error('轮询检查预测请求失败:', error);
        }
    }, 3000);
}

// 加载云端公钥
async function cloudLoadPublicKey() {
    try {
        addLog('cloud-log', '正在加载医院端公钥...', '🔑');

        const response = await fetch('/cloud/load_public_key', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showResult('cloud-key-status', `
                <p><strong>✅ 公钥加载成功!</strong></p>
                <p>已准备好密文运算</p>
            `, true);
            addLog('cloud-log', '医院端公钥加载成功', '✅');
        } else {
            showResult('cloud-key-status', `<p><strong>❌ 加载失败:</strong> ${data.message}</p>`, false);
            addLog('cloud-log', '加载公钥失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('cloud-key-status', `<p><strong>❌ 加载出错:</strong> ${error.message}</p>`, false);
        addLog('cloud-log', '加载公钥出错: ' + error.message, '❌');
    }
}

// 加载数据集列表
async function cloudLoadDatasets() {
    try {
        const response = await fetch('/cloud/list_datasets');
        const data = await response.json();
        
        if (data.success && data.datasets) {
            const container = document.getElementById('cloud-dataset-list');
            container.innerHTML = '';
            
            if (data.datasets.length === 0) {
                container.innerHTML = '<div style="color: #8c8c8c;">暂无加密数据集...</div>';
                return;
            }
            
            data.datasets.forEach(ds => {
                const div = document.createElement('div');
                div.style.padding = '5px';
                div.style.marginBottom = '5px';
                div.style.border = '1px solid #ddd';
                div.style.borderRadius = '4px';
                div.innerHTML = `<span>🔒 ${ds}</span>`;
                container.appendChild(div);
            });
            
            const select = document.getElementById('cloud-dataset-select');
            select.innerHTML = '<option value="">请选择数据集...</option>';
            data.datasets.forEach(ds => {
                const option = document.createElement('option');
                option.value = ds;
                option.textContent = ds;
                select.appendChild(option);
            });
        }
    } catch (error) {
        addLog('cloud-log', '加载数据集列表失败: ' + error.message, '❌');
    }
}

// 触发训练
async function cloudTrain() {
    const datasetName = document.getElementById('cloud-dataset-select').value;

    if (!datasetName) {
        addLog('cloud-log', '请选择要训练的数据集', '⚠️');
        return;
    }

    try {
        addLog('cloud-log', `正在开始训练（数据集: ${datasetName}）...`, '⚙️');

        const response = await fetch('/cloud/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_name: datasetName })
        });

        const data = await response.json();

        if (data.success) {
            showResult('cloud-train-result', `
                <p><strong>✅ 训练成功!</strong></p>
                <p>模型ID: ${data.model_id}</p>
                <p>训练耗时: ${data.train_time}秒</p>
            `, true);
            addLog('cloud-log', `训练完成，模型已保存（${data.train_time}秒）`, '✅');
            
            cloudLoadModels();
        } else {
            showResult('cloud-train-result', `<p><strong>❌ 训练失败:</strong> ${data.message}</p>`, false);
            addLog('cloud-log', '训练失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('cloud-train-result', `<p><strong>❌ 训练出错:</strong> ${error.message}</p>`, false);
        addLog('cloud-log', '训练出错: ' + error.message, '❌');
    }
}

// 一键训练所有
async function cloudTrainAll() {
    try {
        addLog('cloud-log', '正在开始一键训练所有数据集...', '🚀');

        const response = await fetch('/cloud/train_all', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            let resultHtml = `<p><strong>✅ 一键训练完成!</strong></p>`;
            resultHtml += `<p>成功: ${data.success_count}个</p>`;
            resultHtml += `<p>失败: ${data.failed_count}个</p>`;
            resultHtml += `<p>总耗时: ${data.total_time}秒</p>`;
            
            if (data.results.length > 0) {
                resultHtml += `<p><strong>训练结果:</strong></p>`;
                data.results.forEach(res => {
                    resultHtml += `<p>- ${res.dataset_name}: ${res.status} ${res.train_time ? '(' + res.train_time + '秒)' : ''}</p>`;
                });
            }
            
            showResult('cloud-train-result', resultHtml, true);
            addLog('cloud-log', `一键训练完成，成功${data.success_count}个，失败${data.failed_count}个`, '✅');
            
            cloudLoadModels();
        } else {
            showResult('cloud-train-result', `<p><strong>❌ 一键训练失败:</strong> ${data.message}</p>`, false);
            addLog('cloud-log', '一键训练失败: ' + data.message, '❌');
        }
    } catch (error) {
        showResult('cloud-train-result', `<p><strong>❌ 一键训练出错:</strong> ${error.message}</p>`, false);
        addLog('cloud-log', '一键训练出错: ' + error.message, '❌');
    }
}

// 加载模型列表
async function cloudLoadModels() {
    try {
        const response = await fetch('/cloud/list_models');
        const data = await response.json();
        
        if (data.success && data.models) {
            const container = document.getElementById('cloud-model-list');
            container.innerHTML = '';
            
            if (data.models.length === 0) {
                container.innerHTML = '<div style="color: #8c8c8c;">暂无训练好的模型...</div>';
                return;
            }
            
            data.models.forEach(model => {
                const div = document.createElement('div');
                div.style.padding = '5px';
                div.style.marginBottom = '5px';
                div.style.border = '1px solid #ddd';
                div.style.borderRadius = '4px';
                div.innerHTML = `<span>🤖 ${model}</span>`;
                container.appendChild(div);
            });
        }
    } catch (error) {
        addLog('cloud-log', '加载模型列表失败: ' + error.message, '❌');
    }
}

// 检查上下文
async function startCloudContextCheck() {
    setInterval(async () => {
        try {
            const response = await fetch('/cloud/check_context');
            const data = await response.json();
            if (!data.success) {
                addLog('cloud-log', '提示: 需要先加载公钥才能进行密文运算', 'ℹ️');
            }
        } catch (error) {
            console.error('检查上下文失败:', error);
        }
    }, 10000);
}

// 刷新状态
function cloudRefreshStatus() {
    addLog('cloud-log', '云计算中心已就绪', 'ℹ️');
}

// ==========================================
// 初始化
// ==========================================
document.addEventListener('DOMContentLoaded', function() {
    showPage('home');
});
