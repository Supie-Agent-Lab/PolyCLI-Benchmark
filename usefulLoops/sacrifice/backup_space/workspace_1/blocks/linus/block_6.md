### 编辑内容44（会议模式旁路TTS/LLM + 线程池缩减 + 设备侧VAD优先）
#### 编辑人
- w

#### 新增/修改内容
- 会议模式旁路 TTS/LLM
  - 文件：`backend/core/handle/receiveAudioHandle.py`
  - 变更：`startToChat` 在 `conn.current_mode=="meeting"` 时，仅注入 `meeting.snippet`；支持按配置 `meeting.disable_chat_on_snippet`（默认 true）阻止触发对话 LLM；`meeting.disable_tts` 为 true 时不发送 STT。
- 会议模式禁用 TTS 音频下发
  - 文件：`backend/core/handle/sendAudioHandle.py`
  - 变更：当 `meeting.disable_tts==true` 时，不下发音频帧与表情，仅在 FIRST/LAST 时发送 `tts start/stop` 占位。
- 线程池缩减/可配置
  - 文件：`backend/core/connection.py`
  - 变更：连接级 `ThreadPoolExecutor` 从 5 → 2，支持 `meeting.threadpool_max_workers` 覆盖；初始化组件时如 `meeting.disable_tts==true`，跳过打开 TTS 通道（懒启动）。
- 设备侧 VAD 优先
  - 文件：`backend/core/handle/textHandle.py`
  - 变更：进入会议模式时按 `meeting.prefer_device_vad`（默认 true）将 `client_listen_mode` 设为 `manual`，提示前端/硬件以 `listen start/stop` 括起语音段；退出会议模式恢复 `auto`。

#### 配置建议
- `meeting.disable_tts: true`
- `meeting.disable_chat_on_snippet: true`
- `meeting.prefer_device_vad: true`
- 可选：`meeting.threadpool_max_workers: 2`

#### 影响范围与回滚
- 仅影响会议模式；回滚删除上述条件分支即可恢复原行为。


### 编辑内容46（按模式选择LLM + 连接级LLM缓存 + 意图/记忆切换）
#### 编辑人
- w

#### 新增/修改内容
- 模式/用途选择 LLM
  - 文件：`backend/core/connection.py`
  - 新增：`get_llm_for(purpose)`，按 `server.config.llm_by_mode` → `config.selected_module.LLM` 解析别名，懒加载与缓存 LLM 实例
  - 关闭连接时清理 `self._llm_cache`
- 会议总结切换模型
  - 文件：`backend/core/handle/meeting_handle.py`
  - 变更：`finalize_meeting_and_send_summary` 改为使用 `get_llm_for("meeting")`
- 实时对话/函数调用切换
  - 文件：`backend/core/connection.py`
  - 变更：`chat()` 根据 `self.current_mode` 选择 LLM；function_call 路径同样使用所选 LLM
- 意图识别/记忆总结切换
  - 文件：`backend/core/connection.py`
  - 变更：`_initialize_intent()` 和 `_initialize_memory()` 中优先使用 `get_llm_for("intent"/"memory")`
- 其它引用点
  - 文件：`backend/core/handle/peerHandle.py`、`backend/core/handle/helloHandle.py`
  - 变更：统一通过 `get_llm_for("chat")` 获取 LLM
- 配置示例（方式B：多个别名 + llm_by_mode 直切别名）
  - 文件：`backend/data/.config.yaml`
  - 在 `LLM:` 下新增两个别名（同一适配器，不同模型），并在 `llm_by_mode:` 直切别名：
  ```yaml
  LLM:
    ChatGLM_Flashx:
      type: openai
      url: https://open.bigmodel.cn/api/paas/v4/
      model_name: glm-4-flashx-250414
      api_key: <你的key>
    ChatGLM_45:
      type: openai
      url: https://open.bigmodel.cn/api/paas/v4/
      model_name: glm-4.5
      api_key: <你的key>

  llm_by_mode:
    default: ChatGLM_Flashx
    chat:    ChatGLM_Flashx
    meeting: ChatGLM_45
    coding:  ChatGLM_45
    working: ChatGLM_45
    intent:  ChatGLM_Flashx
    memory:  ChatGLM_45
  ```
  - 更新后可通过 `{"type":"server","action":"update_config"}` 热更生效；新会话/下一次用途获取将按新别名实例化。

#### 影响范围与回滚
- 仅涉及 LLM 选择入口；删除 `get_llm_for` 调用并回退至 `conn.llm` 即可恢复。


### 编辑内容48（Meeting 查询接口统一响应与鉴权；推送/终止幂等；finalize 并发幂等与时长修正）
#### 编辑人
- w

#### 新增/修改内容
- Meeting 查询接口统一返回与 CORS
  - 文件：`backend/core/http_server.py`
  - 统一返回结构：成功 `{"success":true,"data":...}`；异常 `{"success":false,"error":"..."}`。
  - `GET /supie/meetings/recent`、`/supie/meetings/{sessionId}`、`/supie/meetings/{sessionId}/transcript` 增加统一 CORS（GET/OPTIONS）。
  - `transcript` 参数校验：`offset>=0`、`1<=limit<=500`，越界时返回空 `items` 且 `total` 保持。

- Meeting 查询接口只读鉴权
  - 文件：`backend/core/http_server.py`
  - 可选 `server.meeting_api_token`：支持 `Authorization: Bearer`、`X-API-Token`、`?token=` 三种传递方式；校验失败返回 401。
  - 仅作用于 `/supie/meetings/*`。

- Transcript 周期推送停止与热更幂等
  - 文件：`backend/core/handle/meeting_handle.py`
  - `stop_meeting_timers()` 二次调用幂等：取消后清空任务引用并置位 `meeting_timers_stopped`。
  - 推送间隔热更只影响"下一周期"：当前周期固定 `meeting_push_interval_ms_current`；推送完成日志打印 `next interval=...ms`。

- Finalize 并发幂等与时长估算修正
  - 文件：`backend/core/handle/meeting_handle.py`
  - 连接级互斥锁 `meeting_finalize_lock`；并发 finalize 时仅首次执行，其余直接重发上次 summary 并加 `idempotent:true`。
  - `duration` 以 `start → max(lastSnippet, now)` 估算，避免 00:00:00 或过短。

#### 待验证内容
- recent/detail/transcript 三接口在无/有 token 下的返回与 CORS 预检通过；错误码与包裹结构符合预期。
- transcript 越界分页返回空 `items` 但 `total` 正确。
- 修改 `meeting.transcript_push_interval_ms` 后，下一周期生效；日志包含 `next interval=...ms`。
- 多次并发 finalize：仅一次生成；其余返回 `idempotent:true`。

#### 影响范围与回滚
- 改动集中在 `http_server.py` 与 `meeting_handle.py`；删除鉴权与包装器、恢复原推送循环读取配置与原 finalize 流程即可回滚。

### 编辑内容49（VAD健壮性修复：_vad_detection_count 初始化）

#### 编辑人
- w

#### 问题与现象
- 日志持续报错：`VAD处理异常: 'ConnectionHandler' object has no attribute '_vad_detection_count'`（包计数递增时重复出现）。

#### 根因
- `backend/core/providers/vad/silero.py::VADProvider.is_vad()` 中，仅在缺少 `client_voice_frame_count` 时同时初始化 `_vad_detection_count`。当连接对象先前已创建过 `client_voice_frame_count`，而未曾创建 `_vad_detection_count`，在后续 `conn._vad_detection_count += 1` 处触发 `AttributeError`。

#### 修复内容（最小变更）
- 文件：`backend/core/providers/vad/silero.py`
- 位置：`is_vad(self, conn, opus_packet)` 初始化帧计数器段落
- 变更：将 `_vad_detection_count` 的初始化从与 `client_voice_frame_count` 绑定改为独立确保存在：

```python
# 初始化帧计数器
if not hasattr(conn, "client_voice_frame_count"):
    conn.client_voice_frame_count = 0
# 确保 _vad_detection_count 一定存在（避免 AttributeError）
if not hasattr(conn, "_vad_detection_count"):
    conn._vad_detection_count = 0
```

#### 影响与验证
- 保持原有行为不变，仅补充健壮性；避免长连接/阶段性状态下出现 `AttributeError`。
- 验证：启动后端并以 WebSocket 推送 OPUS（meeting 模式）；日志不再出现上述异常；VAD 统计与转写链路正常，包计数平稳增长。

#### 回滚
- 还原 `silero.py` 对应编辑即可。

