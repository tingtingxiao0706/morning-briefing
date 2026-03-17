# Morning Briefing Agent

每日晨间简报 Agent —— 自动抓取 AI 行业热门资讯，生成精美报告，推送至飞书。

## 数据来源

| 来源 | 方式 | 内容 |
|------|------|------|
| 机器之心 | 页面解析 | AI 前沿技术与产业资讯 Top 5 |
| 新智元 | 页面解析 | AI 产业深度报道 Top 5 |
| 量子位 | 页面解析 | 人工智能新趋势 Top 5 |
| AITOP100 | 页面解析 | 热门 AI 工具与排行 Top 5 |
| GitHub Trending | 页面解析 | 今日热门仓库 Top 5 |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 2. 配置飞书凭据
cp .env.example .env
# 编辑 .env 填入你的飞书 App ID / Secret / Chat ID

# 3. 手动运行一次
python main.py

# 4. 定时模式（每天早 8 点自动执行）
python main.py --schedule
```

## 配置

编辑 `config.yaml` 可自定义：

- 启用/禁用特定数据源
- 每个来源抓取的条目数
- 定时调度的 cron 表达式
- 报告输出目录和宽度

## 飞书配置

1. 在[飞书开放平台](https://open.feishu.cn)创建自建应用
2. 开启「机器人」能力
3. 添加权限：`im:message:send_as_bot`、`im:resource`
4. 将机器人添加到目标群聊
5. 获取群聊的 `chat_id`（可通过 API 查询）

## 输出示例

生成的报告保存在 `output/` 目录，包含：
- `briefing_YYYY-MM-DD.html` — 可直接浏览器打开的完整报告
- `briefing_YYYY-MM-DD.png` — 截图版本，用于飞书发送
