import subprocess
import os
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProxyConfigManager:
    def __init__(self, base_dir, start_port):
        self.base_dir = Path(base_dir)
        self.start_port = start_port
        self.proxy_configs_file = self.base_dir / "socks-proxy.txt"
        self.configs_dir = self.base_dir / "generated-configs"
        self.ensure_directory(self.base_dir)
        self.ensure_directory(self.configs_dir)

    def ensure_directory(self, directory):
        """确保目录存在，如果不存在则创建"""
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"目录 '{directory}' 已创建或已存在")
        except Exception as e:
            logger.error(f"创建目录 '{directory}' 时出现错误: {e}")
            raise

    def read_proxy_config(self):
        """读取并解析代理配置文件"""
        proxy_configs = []
        if not self.proxy_configs_file.is_file():
            logger.error(f"文件 '{self.proxy_configs_file}' 不存在")
            return proxy_configs

        try:
            with self.proxy_configs_file.open('r') as file:
                for line in file:
                    line = line.strip()
                    if line:
                        parts = line.split(':')
                        if len(parts) == 4:
                            ip, port, username, password = parts
                            proxy_configs.append({
                                'ip': ip,
                                'port': port,
                                'username': username,
                                'password': password
                            })
                        else:
                            logger.warning(f"文件内容格式不正确: {line}")
        except Exception as e:
            logger.error(f"读取文件时出现错误: {e}")

        return proxy_configs

    def generate_config_files(self, configs):
        """根据代理配置生成配置文件"""
        for index, proxy_config in enumerate(configs):
            port = self.start_port + index
            config_content = (
                f"forward-socks5t / {proxy_config['username']}:{proxy_config['password']}@{proxy_config['ip']}:{proxy_config['port']} . \n"
                f"listen-address 0.0.0.0:{port}\n"
            )
            config_filename = self.configs_dir / f"Config{port}.conf"

            try:
                with config_filename.open('w') as config_file:
                    config_file.write(config_content)
                # 设置文件权限为可读
                os.chmod(config_filename, 0o644)
                logger.info(f"配置文件 '{config_filename}' 已生成")
            except Exception as e:
                logger.error(f"写入配置文件 '{config_filename}' 时出现错误: {e}")

    def start_privoxy(self):
        """启动目录下所有配置文件的 privoxy 实例"""
        config_files = list(self.configs_dir.glob('*.conf'))
        if not config_files:
            logger.warning("没有找到配置文件")
            return

        for config_file in config_files:
            try:
                command = ['sudo', 'privoxy', str(config_file)]
                logger.info(f"启动 privoxy 使用配置文件 '{config_file}'")
                subprocess.run(command, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"启动 privoxy 使用配置文件 '{config_file}' 时出现错误: {e}")

def is_privoxy_running():
    """检查 privoxy 进程是否在运行"""
    try:
        result = subprocess.run(['pgrep', '-f', 'privoxy'], stdout=subprocess.PIPE, text=True)
        return result.stdout.strip() != ""
    except Exception as e:
        logger.error(f"检查 privoxy 进程时出现错误: {e}")
        return False

def main():
    """主函数"""
    base_dir = '/etc/privoxy'
    start_port = 10325

    if is_privoxy_running():
        manager = ProxyConfigManager(base_dir, start_port)
        proxy_configs = manager.read_proxy_config()

        if proxy_configs:
            manager.generate_config_files(proxy_configs)
            manager.start_privoxy()
        else:
            logger.error("无法读取或解析代理配置文件")
    else:
        logger.error("privoxy 未启动")
        exit(1)

if __name__ == '__main__':
    main()
