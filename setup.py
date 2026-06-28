"""安装配置"""

from setuptools import setup, find_packages

with open("requirements.txt", encoding="utf-8") as f:
    requirements = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="pylops",
    version="0.2.0",
    description="Linux 主机状态采集与定时自检工具",
    author="Your Name",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "pylops=pylops.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
