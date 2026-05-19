# ThinkLand 自动部署说明

本目录用于 GitHub Actions 自动发布到腾讯云 Ubuntu。

## 1. 服务器首次准备

```bash
sudo apt update
sudo apt install -y git nginx mysql-server python3-venv python3-pip nodejs npm
sudo mkdir -p /www
sudo chown -R "$USER:$USER" /www
cd /www
git clone 你的GitHub仓库地址 thinkland
```

后端 `.env` 只放服务器，不提交到 GitHub：

```bash
cd /www/thinkland/consumer-backend
cp .env.example .env
nano .env
```

MySQL 建议给部署用户配置 `~/.my.cnf`，这样 `deploy/deploy.sh` 可以直接执行 SQL：

```ini
[client]
user=root
password=你的MySQL密码
host=127.0.0.1
default-character-set=utf8mb4
```

然后限制权限：

```bash
chmod 600 ~/.my.cnf
```

## 2. 安装 systemd 服务

如果服务器登录用户不是 `ubuntu`，先修改 `deploy/thinkland-backend.service` 里的 `User` 和 `Group`。

```bash
sudo cp /www/thinkland/deploy/thinkland-backend.service /etc/systemd/system/thinkland-backend.service
sudo systemctl daemon-reload
sudo systemctl enable thinkland-backend
```

## 3. 安装 Nginx 配置

如果有域名，把 `deploy/nginx-thinkland.conf` 里的 `server_name _;` 改成你的域名。

```bash
sudo cp /www/thinkland/deploy/nginx-thinkland.conf /etc/nginx/sites-available/thinkland
sudo ln -sf /etc/nginx/sites-available/thinkland /etc/nginx/sites-enabled/thinkland
sudo nginx -t
sudo systemctl reload nginx
```

## 4. GitHub Secrets

进入仓库页面：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

添加：

```text
SERVER_HOST=服务器公网IP
SERVER_USER=ubuntu
SERVER_PORT=22
SERVER_SSH_KEY=用于登录服务器的 SSH 私钥完整内容
```

## 5. 自动发布

push 到 `main` 后，GitHub Actions 会执行：

```text
.github/workflows/deploy.yml
  -> SSH 到服务器
  -> /www/thinkland/deploy/deploy.sh
```

部署脚本会拉取最新代码、安装后端依赖、执行 SQL、构建前端、重启后端、重载 Nginx。
