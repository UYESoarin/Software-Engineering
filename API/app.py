# ==================== 第1步：导入工具箱 ====================
import os
import base64
import io

from flask import Flask, request, jsonify
from huggingface_hub import InferenceClient
from PIL import Image
from dotenv import load_dotenv

# ==================== 第2步：加载密钥 ====================
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("❌ 没有找到 HF_TOKEN！请检查 .env 文件是否存在并填写了令牌。")

MODEL_ID = "XLabs-AI/flux-RealismLora"
client = InferenceClient(token=HF_TOKEN)

# ==================== 第3步：创建Flask应用 ====================
app = Flask(__name__)


# ==================== 第4步：风格化前端页面 ====================
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Flux 真实感 · AI 图像生成</title>

        <!-- 字体：Inter 和 JetBrains Mono，营造专业感 -->
        <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />

        <style>
            /* ===== 全局重置 & 暗色主题 ===== */
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Inter', -apple-system, sans-serif;
                background: #0b0d0f;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 40px 24px;
                background-image: radial-gradient(ellipse at 20% 50%, rgba(30, 40, 60, 0.4) 0%, transparent 60%),
                                  radial-gradient(ellipse at 80% 50%, rgba(60, 30, 50, 0.3) 0%, transparent 60%);
            }

            /* ===== 主容器 - 16:9 比例约束 ===== */
            .container {
                max-width: 1280px;
                width: 100%;
                aspect-ratio: 16 / 9;
                background: rgba(18, 22, 28, 0.85);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border-radius: 40px;
                padding: 48px 56px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                box-shadow: 0 30px 80px rgba(0, 0, 0, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.05);
                display: flex;
                flex-direction: column;
                overflow-y: auto;
            }

            /* ===== 滚动条美化 ===== */
            .container::-webkit-scrollbar {
                width: 4px;
            }
            .container::-webkit-scrollbar-track {
                background: transparent;
            }
            .container::-webkit-scrollbar-thumb {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 10px;
            }

            /* ===== 顶部导航 / 品牌 ===== */
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 36px;
                flex-shrink: 0;
            }

            .brand {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .brand-icon {
                width: 40px;
                height: 40px;
                background: linear-gradient(135deg, #6C5CE7, #a855f7);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                font-weight: 700;
                color: #fff;
            }

            .brand h1 {
                font-size: 22px;
                font-weight: 600;
                color: #ffffff;
                letter-spacing: -0.3px;
            }

            .brand h1 span {
                color: #a78bfa;
                font-weight: 400;
            }

            .badge {
                font-size: 12px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.4);
                background: rgba(255, 255, 255, 0.06);
                padding: 6px 16px;
                border-radius: 100px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                letter-spacing: 0.3px;
            }

            /* ===== CSS Grid 核心布局：左（输入） + 右（输出） ===== */
            .main-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 40px;
                flex: 1;
                min-height: 0;
            }

            /* ===== 左卡片：输入区 ===== */
            .input-card {
                background: rgba(255, 255, 255, 0.03);
                border-radius: 24px;
                padding: 32px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                display: flex;
                flex-direction: column;
                transition: border-color 0.3s ease;
            }

            .input-card:focus-within {
                border-color: rgba(167, 139, 250, 0.3);
            }

            .input-card label {
                font-size: 13px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.5);
                text-transform: uppercase;
                letter-spacing: 0.8px;
                margin-bottom: 12px;
            }

            .input-card textarea {
                flex: 1;
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 20px;
                font-family: 'Inter', sans-serif;
                font-size: 16px;
                line-height: 1.7;
                color: #e8edf5;
                resize: none;
                outline: none;
                transition: all 0.3s ease;
                min-height: 140px;
            }

            .input-card textarea::placeholder {
                color: rgba(255, 255, 255, 0.2);
                font-weight: 400;
            }

            .input-card textarea:focus {
                border-color: rgba(167, 139, 250, 0.4);
                background: rgba(255, 255, 255, 0.06);
                box-shadow: 0 0 0 4px rgba(167, 139, 250, 0.05);
            }

            /* ===== 提示词示例快速填充 ===== */
            .prompt-examples {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
                margin: 16px 0 20px 0;
            }

            .prompt-examples button {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 100px;
                padding: 6px 16px;
                font-size: 12px;
                font-family: 'Inter', sans-serif;
                color: rgba(255, 255, 255, 0.5);
                cursor: pointer;
                transition: all 0.2s ease;
                font-weight: 500;
            }

            .prompt-examples button:hover {
                background: rgba(167, 139, 250, 0.15);
                color: #c4b5fd;
                border-color: rgba(167, 139, 250, 0.2);
            }

            /* ===== 生成按钮 ===== */
            .generate-btn {
                width: 100%;
                padding: 16px 24px;
                background: linear-gradient(135deg, #6C5CE7, #8b5cf6);
                border: none;
                border-radius: 16px;
                font-family: 'Inter', sans-serif;
                font-size: 16px;
                font-weight: 600;
                color: #ffffff;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                letter-spacing: 0.3px;
                position: relative;
                overflow: hidden;
                margin-top: auto;
            }

            .generate-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 12px 40px rgba(107, 92, 231, 0.35);
            }

            .generate-btn:active {
                transform: translateY(0px);
                box-shadow: 0 4px 20px rgba(107, 92, 231, 0.2);
            }

            .generate-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none !important;
                box-shadow: none !important;
            }

            /* ===== 右卡片：输出区 ===== */
            .output-card {
                background: rgba(255, 255, 255, 0.03);
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 24px;
                position: relative;
                min-height: 300px;
                overflow: hidden;
            }

            .output-card .placeholder {
                color: rgba(255, 255, 255, 0.12);
                font-size: 14px;
                font-weight: 500;
                letter-spacing: 0.5px;
                text-align: center;
                line-height: 1.8;
            }

            .output-card .placeholder .icon {
                font-size: 48px;
                display: block;
                margin-bottom: 16px;
                opacity: 0.3;
            }

            #result-image {
                max-width: 100%;
                max-height: 100%;
                border-radius: 16px;
                display: none;
                object-fit: contain;
                box-shadow: 0 8px 40px rgba(0, 0, 0, 0.6);
                transition: opacity 0.6s ease;
            }

            #result-image.visible {
                display: block;
                animation: fadeIn 0.6s ease;
            }

            @keyframes fadeIn {
                0% { opacity: 0; transform: scale(0.96); }
                100% { opacity: 1; transform: scale(1); }
            }

            /* ===== 状态提示 ===== */
            #status {
                margin-top: 16px;
                font-size: 13px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.3);
                text-align: center;
                transition: all 0.3s ease;
                font-family: 'JetBrains Mono', monospace;
                min-height: 24px;
            }

            #status.loading {
                color: #a78bfa;
            }

            #status.success {
                color: #34d399;
            }

            #status.error {
                color: #f87171;
            }

            /* ===== 响应式：平板 ===== */
            @media (max-width: 1024px) {
                .container {
                    aspect-ratio: auto;
                    padding: 32px 28px;
                    border-radius: 28px;
                }
                .main-grid {
                    grid-template-columns: 1fr;
                    gap: 28px;
                }
                .input-card textarea {
                    min-height: 100px;
                }
            }

            /* ===== 响应式：手机 ===== */
            @media (max-width: 640px) {
                body {
                    padding: 16px;
                }
                .container {
                    padding: 24px 16px;
                    border-radius: 20px;
                }
                .header {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 12px;
                    margin-bottom: 24px;
                }
                .brand h1 {
                    font-size: 18px;
                }
                .input-card {
                    padding: 20px;
                }
                .input-card textarea {
                    font-size: 14px;
                    padding: 14px;
                    min-height: 80px;
                }
                .generate-btn {
                    padding: 14px 20px;
                    font-size: 14px;
                }
                .badge {
                    font-size: 10px;
                    padding: 4px 12px;
                }
            }
        </style>
    </head>
    <body>

        <div class="container">
            <!-- ===== 头部 ===== -->
            <header class="header">
                <div class="brand">
                    <div class="brand-icon">✦</div>
                    <h1>Flux <span>· 真实感</span></h1>
                </div>
                <span class="badge">Hugging Face · XLabs-AI</span>
            </header>

            <!-- ===== 主区域 Grid ===== -->
            <div class="main-grid">
                <!-- 左：输入卡片 -->
                <div class="input-card">
                    <label for="prompt">提示词</label>
                    <textarea id="prompt" placeholder="描述你想要的真实世界画面…&#10;例如：A photorealistic cat sitting on a wooden table, soft lighting, 8k">A photorealistic orange tabby cat sitting on a rustic wooden table, soft sunlight streaming through a window, cinematic lighting, shallow depth of field, highly detailed, 8k, national geographic style</textarea>

                    <!-- 快速示例 -->
                    <div class="prompt-examples">
                        <button data-prompt="A photorealistic Japanese street at night, neon lights reflecting on wet pavement, cinematic, 8k, ultra detailed">🌃 雨夜街头</button>
                        <button data-prompt="A photorealistic close-up portrait of a young woman with freckles, natural sunlight, shallow depth of field, sharp focus, 8k, shot on Canon EOS R5">👩 人像特写</button>
                        <button data-prompt="A photorealistic macro shot of a dew-covered rose petal, morning light, bokeh background, hyper-detailed, 8k, nature photography">🌹 微距花卉</button>
                    </div>

                    <button class="generate-btn" id="generateBtn" onclick="generateImage()">✦ 生成图像</button>
                </div>

                <!-- 右：输出卡片 -->
                <div class="output-card" id="outputCard">
                    <div class="placeholder" id="placeholder">
                        <span class="icon">🖼️</span>
                        输入提示词，点击生成<br />
                        <span style="font-size:12px;opacity:0.5;">Flux 真实感模型 · 约 10–30 秒</span>
                    </div>
                    <img id="result-image" alt="生成的图像" />
                    <div id="status">就绪</div>
                </div>
            </div>
        </div>

        <!-- ===== JavaScript ===== -->
        <script>
            // 快速填充示例
            document.querySelectorAll('.prompt-examples button').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.getElementById('prompt').value = this.dataset.prompt;
                });
            });

            async function generateImage() {
                const prompt = document.getElementById('prompt');
                const btn = document.getElementById('generateBtn');
                const img = document.getElementById('result-image');
                const placeholder = document.getElementById('placeholder');
                const status = document.getElementById('status');

                const text = prompt.value.trim();
                if (!text) {
                    alert('请先输入一段提示词！');
                    return;
                }

                // UI 状态：加载中
                btn.disabled = true;
                btn.textContent = '⏳ 生成中...';
                status.textContent = '⏳ 正在请求 AI 模型…';
                status.className = 'loading';
                img.className = '';
                img.style.display = 'none';
                placeholder.style.display = 'block';

                try {
                    const response = await fetch('/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt: text })
                    });

                    const data = await response.json();

                    if (!response.ok || data.error) {
                        throw new Error(data.error || '服务器处理失败');
                    }

                    // 成功：显示图片
                    img.src = 'data:image/png;base64,' + data.image;
                    img.style.display = 'block';
                    img.className = 'visible';
                    placeholder.style.display = 'none';
                    status.textContent = '✅ 生成成功！';
                    status.className = 'success';

                } catch (error) {
                    status.textContent = '❌ ' + error.message;
                    status.className = 'error';
                    img.style.display = 'none';
                    placeholder.style.display = 'block';
                } finally {
                    btn.disabled = false;
                    btn.textContent = '✦ 生成图像';
                }
            }

            // 回车快捷键（Ctrl+Enter 生成）
            document.getElementById('prompt').addEventListener('keydown', function(e) {
                if (e.ctrlKey && e.key === 'Enter') {
                    e.preventDefault();
                    generateImage();
                }
            });
        </script>

    </body>
    </html>
    '''


# ==================== 第5步：后端接口 ====================
@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    user_prompt = data.get('prompt', '').strip()

    if not user_prompt:
        return jsonify({'error': '提示词不能为空'}), 400

    try:
        print(f"📡 正在请求 AI 模型，提示词为: {user_prompt}")
        image: Image.Image = client.text_to_image(user_prompt, model=MODEL_ID)

        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        return jsonify({'image': img_base64})

    except Exception as e:
        print(f"🔥 API 调用异常: {e}")
        return jsonify({'error': f'AI 服务异常: {str(e)}'}), 500


# ==================== 第6步：启动服务 ====================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)