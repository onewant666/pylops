#!/bin/bash
# 打包脚本 — 生成自解压安装包
# 用法: bash package.sh
# 产出: lhm-install.tar.gz（自带安装脚本，复制到目标机器一键安装）

set -e

PACKAGE_NAME="lhm-install.tar.gz"
TEMP_DIR=$(mktemp -d)
PKG_DIR="$TEMP_DIR/lhm"

echo "正在打包 LHM ..."

# 1. 复制项目文件（排除不需要的）
mkdir -p "$PKG_DIR"
cp -r . "$PKG_DIR/"
rm -rf "$PKG_DIR/.git" "$PKG_DIR/__pycache__" "$PKG_DIR/.claude" "$PKG_DIR/data" "$PKG_DIR/"*.egg-info 2>/dev/null || true
find "$PKG_DIR" -name '*.pyc' -delete 2>/dev/null || true

# 2. 内嵌安装脚本
cat > "$PKG_DIR/install.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
set -e
SKIP_YUM=${SKIP_YUM:-0}

echo "======================================"
echo "  LHM 一键安装"
echo "======================================"

cd "$(dirname "$0")"

# --- 检测操作系统 ---
if [ -f /etc/redhat-release ]; then
    OS="rhel"
    VER=$(cat /etc/redhat-release)
elif [ -f /etc/debian_version ]; then
    OS="debian"
else
    echo "⚠ 未知系统，尝试继续..."
    OS="unknown"
fi

echo "检测到: $VER"

# --- 安装 Python 3.8+ ---
if [ "$SKIP_YUM" != "1" ]; then
    case $OS in
        rhel)
            # CentOS 7 停服修复
            echo "[1/5] 修复 CentOS 7 yum 源..."
            for f in /etc/yum.repos.d/CentOS-*.repo; do
                [ -f "$f" ] && sed -i \
                    -e 's|^mirrorlist=|#mirrorlist=|g' \
                    -e 's|^#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' \
                    "$f" 2>/dev/null || true
            done
            for f in /etc/yum.repos.d/epel*.repo; do
                [ -f "$f" ] && sed -i \
                    -e 's|^metalink|#metalink|g' \
                    -e 's|^#baseurl=https://download.fedoraproject.org/pub/epel|baseurl=https://archives.fedoraproject.org/pub/archive/epel|g' \
                    "$f"
            done
            yum clean all 2>/dev/null || true
            yum makecache 2>/dev/null || true

            echo "[2/5] 安装 Python 3.8 + 依赖..."
            yum install -y epel-release centos-release-scl 2>/dev/null || true
            yum install -y rh-python38 rh-python38-python-devel gcc

            source /opt/rh/rh-python38/enable
            echo "Python: $(python3 --version)"
            ;;

        debian)
            echo "[1/5] 安装依赖..."
            apt-get update
            apt-get install -y python3 python3-pip python3-venv
            echo "Python: $(python3 --version)"
            ;;
    esac
else
    echo "[1/5] 跳过系统依赖安装 (SKIP_YUM=1)"
    echo "[2/5] 跳过系统依赖安装 (SKIP_YUM=1)"
fi

# --- 安装 LHM ---
echo "[3/5] 安装 LHM..."
pip3 install -e . --no-warn-script-location 2>/dev/null || pip3 install -e . 2>/dev/null || {
    # 如果 pip 可编辑安装失败，用 pip install .
    pip3 install . --no-warn-script-location
}

# --- 初始化 ---
echo "[4/5] 初始化配置和数据库..."
lhm init 2>/dev/null || python3 -m lhm init

# --- 完成 ---
echo "[5/5] 完成！"
echo ""
echo "======================================"
echo "  LHM 安装成功！"
echo "======================================"
echo ""
echo "  快速开始:"
echo "    lhm run         单次采集+自检"
echo "    lhm daemon      守护进程"
echo "    lhm web         仪表盘 (http://本机IP:5000)"
echo "    lhm --help      查看所有命令"
echo ""
echo "  CentOS 7 注意: 每次登录先执行 scl enable rh-python38 bash"
echo ""
INSTALL_SCRIPT

chmod +x "$PKG_DIR/install.sh"

# 3. 打包
cd "$TEMP_DIR"
tar -czf "$OLDPWD/$PACKAGE_NAME" lhm/
cd "$OLDPWD"

# 4. 清理
rm -rf "$TEMP_DIR"

echo ""
echo "======================================"
echo " 打包完成: $PACKAGE_NAME"
echo " 大小: $(du -h $PACKAGE_NAME | cut -f1)"
echo "======================================"
echo ""
echo "  >>> 把这个文件复制到 Linux 虚拟机"
echo ""
echo "  在目标机器上:"
echo "    tar -xzf lhm-install.tar.gz"
echo "    cd lhm"
echo "    sudo bash install.sh"
echo ""
