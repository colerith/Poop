# 🚽 拉屎小能手

基于 https://github.com/colerith/Poop 的 `d244481` 版本精简修复。保留原版打卡功能，移除本地额外的游戏大厅、图鉴、下水道探险和厕所经营模块。

## 功能

| 命令 | 用途 |
| --- | --- |
| `/开始拉屎` | 开始计时，每 10 分钟尝试私信提醒，满 1 小时自动记录 |
| `/结束拉屎` | 在开始计时的服务器结束并记录软硬程度、颜色等 |
| `/拉屎打卡` | 事后补录，也计入排行榜次数 |
| `/取消打卡` | 确认后删除最近一条已完成记录 |
| `/本周详细日志` | 私密查看周报，长内容自动分多条消息发送 |
| `/本月热力图` | 私密查看本月颜色与软硬程度日历 |
| `/排行榜` | 查看当前服务器的次数和总时长排行 |

日期按北京时间统计。已完成记录保存在项目根目录 `poop.db`；进行中的计时仍保存在内存，重启后会丢失。重置源码不会清空已有数据库。

## 安装与启动

需要 Python 3.10 或更新版本。

```sh
python -m pip install -r requirements.txt
```

复制 `.env.example` 为 `.env`，填入机器人令牌：

```dotenv
DISCORD_TOKEN=YOUR_BOT_TOKEN
ENABLE_MESSAGE_CONTENT=false
```

在 Discord Developer Portal 为应用创建 Bot，并通过 OAuth2 邀请至服务器，勾选 `bot` 和 `applications.commands`，允许机器人查看频道、发送消息和嵌入链接。

```sh
python main.py
```

启动时先加载追踪插件、清空旧全局命令，连接就绪后逐个同步已加入服务器的命令；新加入服务器也会自动同步。仅注册服务器专属命令，避免和全局命令重复；每次启动会以当前 7 条命令替换服务器远端列表，清理旧游戏命令。插件加载失败会终止启动；网络或授权错误会写入日志。

## 命令不显示时

1. 查看日志是否出现目标服务器 ID 和“已同步 7 条命令”；若插件加载失败，先处理对应异常并重启。
2. 若提示同步被拒绝，检查是否邀请了正确的机器人、是否包含 `applications.commands` 授权。
3. 在服务器“整合”设置中检查命令访问限制，并确认成员在目标频道有使用应用命令的权限；同步成功后刷新 Discord 客户端再试。
4. 必要时由机器人所有者手动同步：先把 `.env` 中 `ENABLE_MESSAGE_CONTENT` 设为 `true`，同时在 Developer Portal 的 Bot 页面开启 Message Content Intent，再重启。

```text
!sync                         同步当前服务器
!sync sync 服务器ID            同步指定服务器
!sync clear                   清除当前服务器专属命令
!sync clear_global            清除全局命令（服务器专属命令仍保留）
```

清除命令不会删除本地定义，可以再次同步恢复；下次启动也会重新注册服务器专属命令。无需手动修改或硬编码服务器 ID。默认斜杠命令不需要开启 Message Content Intent。

## 结构与验证

- `main.py`：启动、命令同步与所有者维护命令。
- `cogs/poop_tracker/`：原版 7 条命令、进行中计时、周报和月历。
- `cogs/core/`：SQLite、选项文案和删除确认按钮。
- `tests/`：无需机器人令牌的离线回归测试。

```sh
python -m unittest discover -s tests -v
```

本次精简前的源码备份保存在 `.local-backups/before-reset-20261009.zip`，该目录不会提交到 Git。

## PM2 提示没有 tree 属性

`AttributeError: 'PoopBot' object has no attribute 'tree'` 表示实际加载的 Discord 库不符合本项目要求。官方 discord.py 2.x 的 `commands.Bot` 会自动创建命令树。旧版本、同名分支包覆盖或者 PM2 使用了其他 Python 环境都可能造成问题。启动前会检查版本和必要 API，并在不兼容时报告解释器及模块路径。

建议在服务器的项目目录创建独立虚拟环境，不要卸载系统 Python 中其他项目的依赖：

```sh
cd /root/Poop
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --upgrade -r requirements.txt
.venv/bin/python -c "import sys, discord; from discord.ext import commands; print(sys.executable, discord.__version__, discord.__file__); assert hasattr(commands.Bot, 'tree')"
```

若提示缺少 venv 模块，在 Debian/Ubuntu 安装与当前 Python 版本对应的 venv 包（例如 `python3-venv`）。确认以上步骤成功后，重新创建此机器人的 PM2 进程以明确指定解释器：

```sh
pm2 delete poop
pm2 start /root/Poop/main.py --name poop --cwd /root/Poop --interpreter /root/Poop/.venv/bin/python
pm2 save
pm2 logs poop --lines 50
```

以上命令使用项目 `.env` 配置。若原 PM2 进程另有自定义环境变量或启动参数，请在重建时一并保留。`.env` 必须使用 Developer Portal 中应用的 Bot Token。
