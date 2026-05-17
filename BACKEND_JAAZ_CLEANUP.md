# 后端 Jaaz 清理计划

> 目标：项目改名 **Funblock**，完全脱离 Jaaz 云依赖，由自部署的 `https://aiapi.funblocks.app` 接管全部能力。
>
> 范围：仅 `server/` 目录（Python 后端）。前端的 Jaaz 清理已完成（任务 #005/#006）。

---

## 背景

- 当前 `_jaaz` 系列工具的实现是把请求转发到 `${BASE_API_URL}/api/v1/image/magic` 等接口
- `BASE_API_URL` 现已指向 `https://aiapi.funblocks.app`，即"远端"就是这套代码本身
- 转发会自调，且本套代码并未实现 `/api/v1/*` 路由 → `_jaaz` 工具全部失效
- 结论：**所有 jaaz 转发逻辑应整体下线**，由自实现的 provider（volces/replicate/直连 OpenAI 等）替代

---

## Tier 1：物理删除文件（17 个）

### 核心服务（4 个）

| 文件 | 删除理由 |
|---|---|
| `server/services/jaaz_service.py` | `JaazService` 类，POST 到 jaaz 云 API 转发器 |
| `server/services/magic_service.py` | "魔法生图"业务，依赖 JaazService |
| `server/services/OpenAIAgents_service/jaaz_magic_agent.py` | magic agent，依赖 JaazService |
| `server/services/OpenAIAgents_service/__init__.py` | 只 export `create_jaaz_response`，跟着删 |

### Jaaz 图像工具（8 个）

- `server/tools/generate_image_by_gpt_image_1_jaaz.py`
- `server/tools/generate_image_by_imagen_4_jaaz.py`
- `server/tools/generate_image_by_recraft_v3_jaaz.py`
- `server/tools/generate_image_by_ideogram3_bal_jaaz.py`
- `server/tools/generate_image_by_flux_1_1_pro_jaaz.py`（注：当前已在 `tool_service.py` 注释，未注册）
- `server/tools/generate_image_by_flux_kontext_pro_jaaz.py`
- `server/tools/generate_image_by_flux_kontext_max_jaaz.py`
- `server/tools/generate_image_by_midjourney_jaaz.py`
- `server/tools/generate_image_by_doubao_seedream_3_jaaz.py`

### Jaaz 视频工具（4 个）

- `server/tools/generate_video_by_seedance_v1_jaaz.py`
- `server/tools/generate_video_by_hailuo_02_jaaz.py`
- `server/tools/generate_video_by_kling_v2_jaaz.py`
- `server/tools/generate_video_by_veo3_fast_jaaz.py`

### Provider 适配器（1 个）

- `server/tools/image_providers/jaaz_provider.py`

---

## Tier 2：改写文件（清引用与注册表）

### 1. `server/services/tool_service.py`

- 第 7-53 行附近：删除 12 个 `from tools.generate_*_jaaz import ...` 导入
- 第 57-193 行 `TOOL_MAPPING`：删除所有 `"provider": "jaaz"` 的条目（共 12 个）
- 保留 `_volces` 和 `_replicate` 条目

### 2. `server/services/config_service.py`

- 删除 `DEFAULT_PROVIDERS_CONFIG` 里整个 `'jaaz'` 条目（第 25-41 行附近）
- 删除 `_get_jaaz_url()` 方法（第 101-103 行附近）
- 移除 `BASE_API_URL` 环境变量相关引用（已无消费者）

### 3. `server/routers/chat_router.py`

- 删除 `from services.magic_service import handle_magic` 导入
- 删除对应的 `/api/magic`、`/api/magic/cancel/{session_id}` 路由

### 4. `server/tools/utils/image_generation_core.py`

- 搜 `jaaz` 关键字，移除 provider 分支判断（保留 volces / replicate / wavespeed 等）

### 5. `server/tools/video_generation/video_generation_core.py`

- 同上，删除 jaaz provider 分支

### 6. `server/tools/video_providers/video_base_provider.py`

- 搜 `jaaz`，可能是 base class 里的 provider 名判断，删除相关分支

### 7. `server/tools/image_providers/wavespeed_provider.py`

- 搜 `jaaz`，确认是否依赖 `jaaz_provider`，剥离

### 8. `server/services/langgraph_service/StreamProcessor.py`

- 搜 `jaaz`，移除对 `_jaaz` 后缀工具名的特殊处理

### 9. `server/services/langgraph_service/configs/image_vide_creator_config.py`

- 搜 `jaaz`，agent 配置里如有硬编码 jaaz 模型名作默认，改成其他 provider 或移除默认

### 10. `server/routers/comfyui_execution.py`

- 搜 `jaaz`，确认是否为无关引用（如导出文件名、注释），按需清理

---

## Tier 3：可选清理（字符串残留，无副作用）

- `server/main.py`、`server/common.py`：日志/错误信息里若有 `jaaz` 字样，替换为 `funblock`
- `server/utils/*`：扫描 `jaaz` 关键字，捎带清理
- 配置文件的注释、docstring 等

---

## 联动改动（清完后端再执行）

### 前端

- `react/src/components/settings/dialog/providers.tsx:89` —— 后端不再返回 jaaz key 后，`.filter((key) => key !== 'jaaz')` 变死代码，删除
- `react/src/components/chat/ChatMagicGenerator.tsx` —— 调用 `/api/magic`，后端删除 endpoint 后失效，整个组件删除
- `react/src/components/chat/Chat.tsx` —— 移除 `<ChatMagicGenerator ... />` 引用和相关 import
- `react/src/api/magic.ts` —— 整个文件删除

### Electron

- `electron/main.js` —— `env.BASE_API_URL` 注入逻辑可删（后端不再消费此变量）
- `electron/comfyUIInstaller.js` —— 同步移除 `process.env.BASE_API_URL` 兜底逻辑

### 用户配置文件

- 用户机器上既有的 `config.toml` 可能仍含 `[jaaz]` 段
- 建议在 `config_service.initialize()` 里加入兼容逻辑：`self.app_config.pop('jaaz', None)`，启动时自动清理旧配置
- 或：发版说明里告知用户手动删除

---

## 执行顺序

1. **删除 Tier 1 的 17 个文件**
2. **跑 `python server/main.py`** 看 import 报错堆栈
3. **按报错精准修 Tier 2**（确保不漏 import）
4. **手动测试**：起前端 → 配 OpenAI key → 发消息 → 选模型 → 看是否能跑通
5. **处理 Tier 3** 字符串残留
6. **执行"联动改动"** 部分清理前端 + Electron

---

## 验证清单

- [ ] `grep -rn "jaaz" server/ --include="*.py"` 输出为空（或仅剩 Tier 3 字符串）
- [ ] `python server/main.py` 启动无 ImportError
- [ ] `curl http://localhost:57988/api/list_tools` 返回的工具列表不含任何 `_jaaz` 后缀
- [ ] `curl http://localhost:57988/api/config` 返回的 providers 不含 `jaaz` key
- [ ] 前端打开设置面板 → 看不到 Jaaz provider
- [ ] 前端选 OpenAI 模型 → 发消息 → 正常返回
- [ ] 前端选 volces / replicate 模型 → 生图正常

---

## 风险与确认事项

| 项 | 风险 | 应对 |
|---|---|---|
| 用户机器既有 config.toml 含 jaaz 段 | 启动读取后还是有 jaaz key | 在 `initialize()` 加 `pop('jaaz', None)` 自动清理 |
| 删除 magic_service 但前端 ChatMagicGenerator 还在 | 调 `/api/magic` 报 404 | 联动改动里同步删前端 |
| `_jaaz` 工具被某 langgraph agent 配置硬引用 | 启动崩溃 | Tier 2 第 9 项已包含，删配置默认值 |
| Tier 1 文件被其他模块 import 但未在 Tier 2 列表 | 启动 ImportError | 执行步骤 #2 跑启动看 import 错误，按需补充 |
