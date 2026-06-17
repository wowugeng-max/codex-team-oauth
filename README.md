# Codex Team-跳过手机号注册脚本

## 说明

这是一个脱敏版的 `codex_team_oauth.py` 脚本，用于展示如何使用 Codex client_id 流程自动注册账号并获取 OAuth token。

该脚本依赖本地 `deps/` 目录中的 Sentinel 支持代码。

## 需要分享的文件

- `codex_team_oauth.py`
- `mail_providers.py`
- `oauth_steps.py`
- `registration_identity.py`
- `token_output.py`
- `deps/__init__.py`
- `deps/sentinel.py`
- `deps/sentinel_quickjs.py`
- `deps/openai_sentinel_quickjs.js`
- `.env.example`

## 依赖安装

请先安装 Python 依赖：

```bash
python3 -m pip install --upgrade pip
pip install curl_cffi
```

如果要走 QuickJS 路径，还需要系统可用 `node`：

```bash
node -v
```

## 环境变量配置

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

编辑 `.env`，将以下变量替换为真实值：

- `MAIL_PROVIDER`：邮箱链路，可选 `cloudmail` 或 `inbuck`
- `RUN_COUNT`：执行次数，默认 `1`；配置为正整数时会连续执行多轮完整注册流程。多轮执行时，单轮失败会记录错误并继续下一轮，最后如有失败会返回非 0 退出码。

### Cloud Mail 链路

参考 [cloudmailmanual](https://github.com/wowugeng-max/cloudmailmanual) 的 Cloud Mail 公共 API 调用方式。Cloud Mail 链路会自动创建邮箱地址、生成邮箱密码，并用参考项目的资料生成逻辑创建姓名和生日；不需要配置 `TEST_EMAIL` / `TEST_PASSWORD`。

```env
MAIL_PROVIDER=cloudmail
RUN_COUNT=1
CLOUDMAIL_API_BASE=https://your-cloudmail-api.example
CLOUDMAIL_ADMIN_EMAIL=admin@example.com
CLOUDMAIL_ADMIN_PASSWORD=your_admin_password
CLOUDMAIL_DOMAIN_SUFFIX=mx.example.com
CLOUDMAIL_ROLE_NAME=
CLOUDMAIL_PROXY=
```

脚本会通过 `genToken` 获取管理员 token，通过 `addUser` 创建 `本地名@CLOUDMAIL_DOMAIN_SUFFIX` 邮箱，再用 `emailList` 查询该邮箱验证码。`CLOUDMAIL_ROLE_NAME` 和 `CLOUDMAIL_PROXY` 可留空。

### inbuck 链路

inbuck 是旧链路，需要手动提供注册邮箱、OpenAI 注册密码和 OTP 邮件服务接口：

```env
MAIL_PROVIDER=inbuck
TEST_EMAIL=your-test-email@example.com
TEST_PASSWORD=your-password
TEST_INBOX_API=http://your-mailbox-service.example/api/v1
```

`CLIENT_ID` 和 `CODEX_REDIRECT_URI` 已固定在脚本中，无需在 `.env` 中配置。

## 运行方式

```bash
python3 codex_team_oauth.py
```

脚本会自动读取当前目录下的 `.env` 文件。

OAuth token 交换成功后，脚本会保存到项目目录下的 `result/json/<邮箱地址>.json`，格式与 Codex 可用 token JSON 保持一致。

## 注意

- 该脚本仅用于示例和测试，切勿分享 `.env` 中的真实凭据。
- 不要分享项目目录下生成的 `result/json/<邮箱地址>.json` 或其他敏感输出文件。
- Cloud Mail 链路需要 `CLOUDMAIL_API_BASE`、`CLOUDMAIL_ADMIN_EMAIL`、`CLOUDMAIL_ADMIN_PASSWORD`、`CLOUDMAIL_DOMAIN_SUFFIX`；inbuck 链路需要 `TEST_EMAIL`、`TEST_PASSWORD`、`TEST_INBOX_API`。

## 友情链接

- [LINUX DO - 新的理想型社区](https://linux.do/)
