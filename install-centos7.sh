#!/bin/bash
set -e

echo "======================================"
echo " LHM CentOS 7 一键安装脚本"
echo "======================================"

# ------ 1. 修复 CentOS 7 停服源 ------
echo "[1/6] 修复 yum 源为 vault 归档仓库..."
for f in /etc/yum.repos.d/CentOS-*.repo; do
    sudo sed -i \
        -e 's|^mirrorlist=|#mirrorlist=|g' \
        -e 's|^#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' \
        "$f" 2>/dev/null || true
done

for f in /etc/yum.repos.d/epel*.repo; do
    [ -f "$f" ] && sudo sed -i \
        -e 's|^metalink|#metalink|g' \
        -e 's|^#baseurl=https://download.fedoraproject.org/pub/epel|baseurl=https://archives.fedoraproject.org/pub/archive/epel|g' \
        "$f"
done

sudo yum clean all
sudo yum makecache

# ------ 2. 安装 Python 3.8 ------
echo "[2/6] 安装 Python 3.8 + 依赖..."
sudo yum install -y epel-release centos-release-scl
sudo yum install -y rh-python38 rh-python38-python-devel gcc git

# ------ 3. 启用 Python 3.8 环境 ------
echo "[3/6] 启用 Python 3.8..."
source /opt/rh/rh-python38/enable
echo "Python: $(python3 --version)"
echo "pip:    $(pip3 --version)"

# ------ 4. 克隆并安装 LHM ------
echo "[4/6] 克隆 LHM..."
cd /opt
sudo rm -rf lhm 2>/dev/null || true
sudo git clone https://github.com/onewant666/lhm.git
sudo chown -R $USER:$USER lhm
cd lhm

echo "[5/6] 安装 LHM..."
pip3 install -e . --no-warn-script-location

# ------ 5. 初始化 ------
echo "[6/6] 初始化..."
lhm init

# ------ 完成 ------
echo ""
echo "======================================"
echo " 安装完成！"
echo "======================================"
echo ""
echo " 验证:   lhm run"
echo " 守护:   lhm daemon"
echo " 仪表盘: lhm web --host 0.0.0.0"
echo " 帮助:   lhm --help"
echo ""
echo " 注意: 每次登录需先执行: scl enable rh-python38 bash"
echo ""
