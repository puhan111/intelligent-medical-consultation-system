# 使用官方 Python 3.12 slim 镜像作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
# 先将 apt 源替换为清华镜像以加速国内下载（Debian trixie 使用 deb822 格式）
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 使用清华镜像源以加速国内下载
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 复制依赖文件并安装 Python 依赖
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建运行时可写目录；命名卷首次挂载时会继承这些目录的属主
RUN mkdir -p logs celerybeat-data

# 创建非 root 用户运行应用
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import http.client, os; c = http.client.HTTPConnection('127.0.0.1', int(os.getenv('API_PORT', '8001')), timeout=5); c.request('GET', '/api/v1/config/health'); assert c.getresponse().status == 200" || exit 1

# 启动命令
CMD ["python", "main.py"]
