                pass

            # 从 Header 兜底解析（包含非规范写法）
            def _normalize_id(v):
                try:
                    if v is None:
                        return None
                    vv = str(v).strip().strip('"').strip("'")
                    return vv.lower() if vv else None
                except Exception:
                    return None
            header_device_id = _normalize_id(
                self.headers.get("device-id")
                or self.headers.get("device_id")
                or self.headers.get("x-device-id")
                or self.headers.get("x-device_id")
            )
            header_client_id = _normalize_id(
                self.headers.get("client-id")
                or self.headers.get("client_id")
                or self.headers.get("x-client-id")
                or self.headers.get("x-client_id")
            )

            # 赋值优先级：Query > Header > 回退
            chosen_device_id = device_id_from_query or header_device_id or header_client_id
            chosen_client_id = client_id_from_query or header_client_id or chosen_device_id

            if chosen_device_id:
                self.headers["device-id"] = chosen_device_id
                if chosen_client_id:
                    self.headers["client-id"] = chosen_client_id
                # 打印来源与解析快照（包含原始 path 片段便于定位异常客户端）
                try:
                    raw_paths_snapshot = []
                    if isinstance(raw_path_from_server, str) and raw_path_from_server:
                        raw_paths_snapshot.append(raw_path_from_server[:256])
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                        for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                            val = getattr(ws, attr, "")
                            if isinstance(val, str) and val:
                                raw_paths_snapshot.append(val[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    src = "query" if device_id_from_query else "header"
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={src}, rawPaths={truncate_for_log(str(raw_paths_snapshot))})"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={'query' if device_id_from_query else 'header'})"
                    )
            else:
                # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
                auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
                self.headers["device-id"] = auto_device_id
                self.headers["client-id"] = auto_device_id
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    header_keys = list(self.headers.keys())
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; rawPaths={truncate_for_log(str(raw_paths_snapshot))}, headerKeys={truncate_for_log(str(header_keys))}"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
                    )
            # 获取客户端ip地址
            try:
                remote = getattr(ws, "remote_address", None)
                if isinstance(remote, tuple) and len(remote) >= 1:
                    self.client_ip = remote[0]
                else:
                    self.client_ip = str(remote) if remote is not None else ""
            except Exception:
                self.client_ip = ""
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # 进行认证
            await self.auth.authenticate(self.headers)

            # 认证通过,继续处理
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)
            # 在 server 上注册设备路由（自动断开旧连接）
            if self.server and self.device_id:
                ok = await self.server.register_device_handler(self.device_id, self)
                if ok is False:
                    self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
                    await ws.send("设备注册失败")
                    await self.close(ws)
                    return

            # 启动超时检查任务
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.websocket.send(json.dumps(self.welcome_msg))

            # 获取差异化配置
            self._initialize_private_config()
            # 异步初始化
            self.executor.submit(self._initialize_components)

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            try:
                safe_e = truncate_for_log(str(e))
                safe_tb = truncate_for_log(stack_trace)
            except Exception:
                safe_e = str(e)
                safe_tb = stack_trace
            self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
            return
        finally:
            try:
                # 注销设备路由映射
                if self.server and self.device_id:
                    await self.server.unregister_device_handler(self.device_id, self)
            finally:
                await self._save_and_close(ws)

    async def _save_and_close(self, ws):
        """保存记忆并关闭连接"""
        try:
            if self.memory:
                # 使用线程池异步保存记忆
                def save_memory_task():
                    try:
                        # 创建新事件循环（避免与主循环冲突）
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            self.memory.save_memory(self.dialogue.dialogue)
                        )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
                    finally:
                        loop.close()

                # 启动线程保存记忆，不等待完成
                threading.Thread(target=save_memory_task, daemon=True).start()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
        finally:
            # 立即关闭连接，不等待记忆保存完成
            await self.close(ws)

    def reset_timeout(self):
        """重置超时计时器"""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._check_timeout())

    async def _route_message(self, message):
        """消息路由"""
        # 重置超时计时器
        self.reset_timeout()

        if isinstance(message, str):
            # 轻量 ping/keepalive：收到后仅重置计时器并忽略
            try:
                import json as _json
                try:
                    obj = _json.loads(message)
                except Exception:
                    obj = None
                if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
                    try:
                        # 可选：立即回 pong
                        await self.websocket.send(_json.dumps({"type": "pong"}))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None:
                return
            if self.asr is None:
                return
            self.asr_audio_queue.put(message)

    async def handle_restart(self, message):
        """处理服务器重启请求"""
        try:

            self.logger.bind(tag=TAG).info("收到服务器重启指令，准备执行...")

            # 发送确认响应
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "服务器重启中...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # 异步执行重启操作
            def restart_server():
                """实际执行重启的方法"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("执行服务器重启...")
                # 后台重启：避免继承TTY，全部重定向，保证 nohup/backgroud 模式不被SIGTTIN挂起
                with open(os.devnull, "rb", buffering=0) as devnull_in, \
                     open(os.devnull, "ab", buffering=0) as devnull_out, \
                     open(os.devnull, "ab", buffering=0) as devnull_err:
                    subprocess.Popen(
                        [sys.executable, "app.py"],
                        stdin=devnull_in,
                        stdout=devnull_out,
                        stderr=devnull_err,
                        start_new_session=True,
                        close_fds=True,
                    )
                os._exit(0)

            # 使用线程执行重启避免阻塞事件循环
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"重启失败: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            update_module_string(self.selected_module_str)
            """初始化组件"""
            if self.config.get("prompt") is not None:
                self.prompt = self.config["prompt"]
                self.change_system_prompt(self.prompt)
                self.logger.bind(tag=TAG).info(
                    f"初始化组件: prompt成功 {self.prompt[:50]}..."
                )

            """初始化本地组件"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()
            # 打开语音识别通道
            asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)

            if self.tts is None:
                self.tts = self._initialize_tts()
            # 会议模式可禁用 TTS 通道（懒启动）
            disable_tts = False
            try:
                srv = getattr(self, "server", None)
                base_cfg = getattr(srv, "config", None) if srv else None
                if isinstance(base_cfg, dict):
                    meeting_cfg2 = base_cfg.get("meeting", {})
                else:
                    meeting_cfg2 = self.config.get("meeting", {})
                disable_tts = bool(meeting_cfg2.get("disable_tts", False))
            except Exception:
                disable_tts = False
            if not disable_tts:
                asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)

            """加载记忆"""
            self._initialize_memory()
            """加载意图识别"""
            self._initialize_intent()
            """初始化上报线程"""
            self._init_report_threads()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"实例化组件失败: {e}")

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程已启动")

    def _initialize_tts(self):
        """初始化TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

    def _initialize_asr(self):
        """初始化ASR"""
        if self._asr.interface_type == InterfaceType.LOCAL:
            # 如果公共ASR是本地服务，则直接返回
            # 因为本地一个实例ASR，可以被多个连接共享
            asr = self._asr
        else:
            # 如果公共ASR是远程服务，则初始化一个新实例
            # 因为远程ASR，涉及到websocket连接和接收线程，需要每个连接一个实例
            asr = initialize_asr(self.config)

        return asr

    def _initialize_private_config(self):
        """如果是从配置文件获取，则进行二次实例化"""
        if not self.read_config_from_api:
            return
        """从接口获取差异化的配置进行二次实例化，非全量重新实例化"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} 秒，获取差异化配置成功: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get("selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # 加载插件配置
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                self.config["plugins"] = plugin_from_server
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = plugin_from_server.keys()
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """初始化记忆模块"""
        # 按模式选择记忆总结 LLM（可被 llm_by_mode.memory 覆盖）
        chosen_llm = self.llm
        try:
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                selected = self.get_llm_for("memory")
                if selected is not None:
                    chosen_llm = selected
        except Exception:
            pass

        self.memory.init_memory(
            role_id=self.device_id,
            llm=chosen_llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # 获取记忆总结配置
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # 如果使用 nomen，直接返回
        if memory_type == "nomem":
            return
        # 使用 mem_local_short 模式
        elif memory_type == "mem_local_short":
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get("type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为记忆总结创建了专用LLM: {memory_llm_name}, 类型: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # 否则使用主LLM
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """初始化意图识别模块"""
        # 获取意图识别配置
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # 如果使用 nointent，直接返回
        if intent_type == "nointent":
            return
        # 使用 intent_llm 模式
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为意图识别创建了专用LLM: {intent_llm_name}, 类型: {intent_llm_type}"
                )
                # 按模式选择意图识别 LLM（可被 llm_by_mode.intent 覆盖）
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(intent_llm)
                    else:
                        self.intent.set_llm(intent_llm)
                except Exception:
                    self.intent.set_llm(intent_llm)
            else:
                # 否则使用主LLM
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(self.llm)
                    else:
                        self.intent.set_llm(self.llm)
                except Exception:
                    self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """加载插件"""
        self.func_handler = FunctionHandler(self)
        self.mcp_manager = MCPManager(self)

        """加载MCP工具"""
        asyncio.run_coroutine_threadsafe(
            self.mcp_manager.initialize_servers(), self.loop
        )

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # 更新系统prompt至上下文
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, tool_call=False):
        try:
            safe_query = truncate_for_log(query)
        except Exception:
            safe_query = query
        self.logger.bind(tag=TAG).info(f"大模型收到用户消息: {safe_query}")
        self.llm_finish_task = False
        # 阶段2：进入对话活跃态（不再下发额外占位渲染，避免 c1→p1 的瞬时切换）
        try:
            self.current_mode = "dialog.active"
        except Exception:
            pass

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        if hasattr(self, "mcp_client"):
            mcp_tools = self.mcp_client.get_available_tools()
            if mcp_tools is not None and len(mcp_tools) > 0:
                if functions is None:
                    functions = []
                functions.extend(mcp_tools)
        response_message = []

        try:
            # 使用带记忆的对话
            memory_str = None
            if self.memory is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            self.sentence_id = str(uuid.uuid4().hex)


            # 按当前模式选择 LLM（默认chat；coding/working 切换对应别名）
            purpose = self.current_mode or "chat"
            active_llm = self.llm
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                try:
                    active_llm = self.get_llm_for(purpose) or self.llm
                except Exception:
                    active_llm = self.llm

            if self.intent_type == "function_call" and functions is not None:
                # 使用支持functions的streaming接口
                llm_responses = active_llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                    functions=functions,
                )
            else:
                llm_responses = active_llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        text_index = 0
        self.client_abort = False
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    # print("content_arguments", content_arguments)
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response
            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    if text_index == 0:
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=self.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )
                    text_index += 1
        # 处理function call
        if tool_call_flag:
            bHasError = False
            if function_id is None:
                a = extract_json_from_string(content_arguments)
                if a is not None:
                    try:
                        content_arguments_json = json.loads(a)
                        function_name = content_arguments_json["name"]
                        function_arguments = json.dumps(
                            content_arguments_json["arguments"], ensure_ascii=False
                        )
                        function_id = str(uuid.uuid4().hex)
                    except Exception as e:
                        bHasError = True
                        response_message.append(a)
                else:
                    bHasError = True
                    response_message.append(content_arguments)
                if bHasError:
                    self.logger.bind(tag=TAG).error(
                        f"function call error: {content_arguments}"
                    )
            if not bHasError:
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # 处理Server端MCP工具调用
                if self.mcp_manager.is_mcp_tool(function_name):
                    result = self._handle_mcp_tool_call(function_call_data)
                elif hasattr(self, "mcp_client") and self.mcp_client.has_tool(
                    function_name
                ):
                    # 如果是小智端MCP工具调用
                    self.logger.bind(tag=TAG).debug(
                        f"调用小智端MCP工具: {function_name}, 参数: {function_arguments}"
                    )
                    try:
                        result = asyncio.run_coroutine_threadsafe(
                            call_mcp_tool(
                                self, self.mcp_client, function_name, function_arguments
                            ),
                            self.loop,
                        ).result()
                        self.logger.bind(tag=TAG).debug(f"MCP工具调用结果: {result}")

                        resultJson = None
                        if isinstance(result, str):
                            try:
                                resultJson = json.loads(result)
                            except Exception as e:
                                self.logger.bind(tag=TAG).error(
                                    f"解析MCP工具返回结果失败: {e}"
                                )

                        # 视觉大模型不经过二次LLM处理
                        if (
                            resultJson is not None
                            and isinstance(resultJson, dict)
                            and "action" in resultJson
                        ):
                            result = ActionResponse(
                                action=Action[resultJson["action"]],
                                result=None,
                                response=resultJson.get("response", ""),
                            )
                        else:
                            result = ActionResponse(
                                action=Action.REQLLM, result=result, response=""
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
                        result = ActionResponse(
                            action=Action.REQLLM, result="MCP工具调用失败", response=""
                        )
                else:
                    # 处理系统函数
                    result = self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    )
                self._handle_function_result(result, function_call_data)

        # 存储对话内容
        if len(response_message) > 0:
            self.dialogue.put(
                Message(role="assistant", content="".join(response_message))
            )
            # 将最终回答渲染为 list 视图，遵循 hardware-ui-design.md 对话页面
            try:
                final_text = "".join(response_message)
                # 提取最近一条用户内容与近几条历史用户文本
                latest_user_text = None
                history_user = []
                try:
                    for m in reversed(self.dialogue.dialogue):
                        if m.role == "user" and latest_user_text is None:
                            latest_user_text = m.content
                        elif m.role == "user" and len(history_user) < 3:
                            history_user.append(m.content)
                        if latest_user_text and len(history_user) >= 3:
                            break
                except Exception:
                    pass

                try:
                    _, owner_name = get_badge_and_owner(getattr(self, "device_id", "")) or ("", "")
                except Exception:
                    owner_name = ""
                # 读取最近两次完整对话的“会话级摘要”
                summaries = get_recent_chat_summaries(getattr(self, "device_id", ""), limit=2)
                # 将摘要放在“历史对话”区域（最多两条）
                items = build_dialog_chat_items(owner_name, "喵喵同学", latest_user_text or "", final_text, summaries)
                payload_final = {
                    "type": "ui.render",
                    "id": f"dlg-final-{self.sentence_id or ''}",
                    "page": "dialog.chat",
                    "header": {},
                    "body": {"kind": "list", "items": items},
                    "footer": {"hint": build_chat_footer_hint()}
                }
                asyncio.run_coroutine_threadsafe(send_render(self, payload_final), self.loop)

                # 生成并保存本轮“完整对话摘要”（简单串接，可替换为专用总结器）
                try:
                    owner_label = owner_name or "用户"
                    summary_text = f"{owner_label}: {latest_user_text or ''} / 喵喵同学: {final_text}"
                    append_chat_summary(getattr(self, "device_id", ""), summary_text, max_items=2)
                except Exception:
                    pass
            except Exception:
                pass
        if text_index > 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )

        return True

    def _handle_mcp_tool_call(self, function_call_data):
        function_arguments = function_call_data["arguments"]
        function_name = function_call_data["name"]
        try:
            args_dict = function_arguments
            if isinstance(function_arguments, str):
                try:
                    args_dict = json.loads(function_arguments)
                except json.JSONDecodeError:
                    self.logger.bind(tag=TAG).error(
                        f"无法解析 function_arguments: {function_arguments}"
                    )
                    return ActionResponse(
                        action=Action.REQLLM, result="参数解析失败", response=""
                    )

            tool_result = asyncio.run_coroutine_threadsafe(
                self.mcp_manager.execute_tool(function_name, args_dict), self.loop
            ).result()
            # meta=None content=[TextContent(type='text', text='北京当前天气:\n温度: 21°C\n天气: 晴\n湿度: 6%\n风向: 西北 风\n风力等级: 5级', annotations=None)] isError=False
            content_text = ""
            if tool_result is not None and tool_result.content is not None:
                for content in tool_result.content:
                    content_type = content.type
                    if content_type == "text":
                        content_text = content.text
                    elif content_type == "image":
                        pass

            if len(content_text) > 0:
                return ActionResponse(
                    action=Action.REQLLM, result=content_text, response=""
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
            return ActionResponse(
                action=Action.REQLLM, result="工具调用出错", response=""
            )

        return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")

    def _handle_function_result(self, result, function_call_data):
        if result.action == Action.RESPONSE:  # 直接回复前端
            text = result.response
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4()) if function_id is None else function_id
                        ),
                        content=text,
                    )
                )
                self.chat(text, tool_call=True)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.result
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """聊天记录上报工作线程"""
        while not self.stop_event.is_set():
            try:
                # 从队列获取数据，设置超时以便定期检查停止事件
                item = self.report_queue.get(timeout=1)
                if item is None:  # 检测毒丸对象
                    break
                type, text, audio_data, report_time = item
                try:
                    # 检查线程池状态
                    if self.executor is None:
                        continue
                    # 提交任务到线程池
                    self.executor.submit(
                        self._process_report, type, text, audio_data, report_time
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"聊天记录上报线程异常: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"聊天记录上报工作线程异常: {e}")

        self.logger.bind(tag=TAG).info("聊天记录上报线程已退出")

    def _process_report(self, type, text, audio_data, report_time):
        """处理上报任务"""
        try:
            # 执行上报（传入二进制数据）
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"上报处理异常: {e}")
        finally:
            # 标记任务完成
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"清除服务端讲话状态")

    async def close(self, ws=None):
        """资源清理方法"""
        try:
            # 在会话关闭前，生成一次本轮“完整对话摘要”，加入历史（仅在存在有效轮次时）
            try:
                latest_user = None
                latest_assistant = None
                for m in reversed(self.dialogue.dialogue if isinstance(self.dialogue, Dialogue) else []):
                    if m.role == "assistant" and latest_assistant is None:
                        latest_assistant = m.content
                    elif m.role == "user" and latest_user is None:
                        latest_user = m.content
                    if latest_user and latest_assistant:
                        break
                if latest_user or latest_assistant:
                    try:
                        _, owner_name = get_badge_and_owner(getattr(self, "device_id", "")) or ("", "")
                    except Exception:
                        owner_name = ""
                    summary_text = f"{owner_name or '用户'}: {latest_user or ''} / 喵喵同学: {latest_assistant or ''}"
                    append_chat_summary(getattr(self, "device_id", ""), summary_text, max_items=2)
            except Exception:
                pass
            # 取消超时任务
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None

            # 取消编码洞察定时任务
            try:
                if hasattr(self, "coding_insight_task") and self.coding_insight_task and not self.coding_insight_task.done():
                    self.coding_insight_task.cancel()
            except Exception:
                pass

            # 清理MCP资源
            if hasattr(self, "mcp_manager") and self.mcp_manager:
                await self.mcp_manager.cleanup_all()

            # 触发停止事件
            if self.stop_event:
                self.stop_event.set()

            # 清空任务队列
            self.clear_queues()

            # 关闭WebSocket连接
            if ws:
                await ws.close()
            elif self.websocket:
                await self.websocket.close()

            # 最后关闭线程池（避免阻塞）
            if self.executor:
                try:
                    # Python 3.9+ 支持 cancel_futures
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    self.executor.shutdown(wait=False)
                self.executor = None

            # 清理 LLM 实例缓存
            try:
                if hasattr(self, "_llm_cache") and isinstance(self._llm_cache, dict):
                    self._llm_cache.clear()
            except Exception:
                pass

            # 关闭 asr/tts/llm 资源
            try:
                if hasattr(self, "asr") and hasattr(self.asr, "close") and callable(getattr(self.asr, "close")):
                    maybe_close = self.asr.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "tts") and hasattr(self.tts, "close") and callable(getattr(self.tts, "close")):
                    maybe_close = self.tts.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "llm") and hasattr(self.llm, "close") and callable(getattr(self.llm, "close")):
                    maybe_close = self.llm.close()  # 供应商可选实现
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass

            self.logger.bind(tag=TAG).info("连接资源已释放")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")

    def clear_queues(self):
        """清空所有任务队列"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

            # 使用非阻塞方式清空队列
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"清理结束: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self):
        """重置VAD状态，恢复到idle状态"""
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.listen_state = "idle"
        if self._listen_state_timer:
            self._listen_state_timer.cancel()
            self._listen_state_timer = None
        self.logger.bind(tag=TAG).debug("VAD states reset.")
    
    async def send_json(self, data: dict) -> bool:
        """统一的 JSON 消息发送封装，包含错误处理
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.websocket:
            self.logger.bind(tag=TAG).warning("send_json: websocket is None")
            return False
        
        try:
            # 优先使用 send_json 方法
            if hasattr(self.websocket, 'send_json'):
                await self.websocket.send_json(data)
            else:
                # 回退到字符串发送
                await self.websocket.send(json.dumps(data, ensure_ascii=False))
            return True
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，静默处理（预期情况）
            self.logger.bind(tag=TAG).debug(f"send_json: connection closed for device {self.device_id}")
            return False
        except Exception as e:
            # 其他异常，记录警告但不中断
            self.logger.bind(tag=TAG).warning(f"send_json failed for device {self.device_id}: {e}")
            return False
    
    async def send_text(self, text: str) -> bool:
        """统一的文本消息发送封装
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.websocket:
            self.logger.bind(tag=TAG).warning("send_text: websocket is None")
            return False
        
        try:
            await self.websocket.send(text)
            return True
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，静默处理
            self.logger.bind(tag=TAG).debug(f"send_text: connection closed for device {self.device_id}")
            return False
        except Exception as e:
            # 其他异常，记录警告
            self.logger.bind(tag=TAG).warning(f"send_text failed for device {self.device_id}: {e}")
            return False
    
    async def transition_listen_state(self, new_state: str):
        """状态机转换：idle -> listening -> finalizing -> idle"""
        old_state = self.listen_state
        if old_state == "idle" and new_state == "listening":
            self.listen_state = "listening"
            self._last_listen_event_ms = int(time.time() * 1000)
            self.logger.bind(tag=TAG).debug("Listen state: idle -> listening")
        elif old_state == "listening" and new_state == "finalizing":
            self.listen_state = "finalizing"
            self.logger.bind(tag=TAG).debug("Listen state: listening -> finalizing")
            # 触发一次handle_voice_stop
            if len(self.asr_audio) > 0:
                from core.handle.receiveAudioHandle import handleAudioMessage
                await handleAudioMessage(self, b"")
        elif old_state == "finalizing" and new_state == "idle":
            self.listen_state = "idle"
            self.logger.bind(tag=TAG).debug("Listen state: finalizing -> idle")
            self.reset_vad_states()
    
    def check_vad_fallback(self):
        """检查是否需要VAD兜底（超过fallback_ms未见设备边界）"""
        if self.listen_state != "listening":
            return False
        if self.client_listen_mode != "manual":
            return False
        now_ms = int(time.time() * 1000)
        fallback_ms = 2000  # 默认2秒
        try:
            base_cfg = self._get_base_config()
            meeting_cfg = base_cfg.get("meeting", {})
            fallback_ms = int(meeting_cfg.get("vad_fallback_ms", 2000))
        except Exception:
            pass
        last_event_ms = getattr(self, "_last_listen_event_ms", 0)
        if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
            self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
            return True
        return False

    async def send_text(self, text: str) -> None:
        """统一文本发送包装。"""
        try:
            if self.websocket:
                await self.websocket.send(text)
        except Exception:
            pass

    async def send_json(self, payload: dict) -> None:
        """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
        try:
            if self.websocket is None:
                return
            try:
                await self.websocket.send_json(payload)
            except AttributeError:
                import json as _json
                await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
        except Exception:
            # 发送错误不应中断主流程
            pass

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """检查连接超时"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.timeout_seconds)
                if not self.stop_event.is_set():
                    # 在关闭前先发送提示并提供缓冲期（与无声层策略一致）
                    try:
                        await self.websocket.send(json.dumps({
                            "type": "system",
                            "event": "timeout_warning",
                            "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
                        }))
                    except Exception:
                        pass
                    # 给予 10 秒缓冲，若期间收到任何消息，reset_timeout 会取消下一轮关闭
                    try:
                        await asyncio.sleep(10)
                    except Exception:
                        pass
                    if self.stop_event.is_set():
                        break
                    self.logger.bind(tag=TAG).info("连接超时，准备关闭")
                    await self.close(self.websocket)
                    break
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")

```

```python
import os
import sys
import copy
import json
import uuid
import time
import queue
import asyncio
import threading
import traceback
from config.logger import truncate_for_log
import subprocess
import websockets
from core.handle.mcpHandle import call_mcp_tool
from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
)
from typing import Dict, Any
from core.mcp.manager import MCPManager
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.handle.functionHandler import FunctionHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, update_module_string
from config.manage_api_client import DeviceNotFoundException, DeviceBindException
from core.orchestration.render_sender import send_render
from core.orchestration.dialog_ui import build_dialog_chat_items, build_chat_footer_hint
from core.utils.device_registry import get_badge_and_owner
from core.orchestration.history_store import append_chat_summary, get_recent_chat_summaries
from core.utils.dialogue import Dialogue


TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # 保存server实例的引用

        self.auth = AuthMiddleware(config)
        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.client_ip_info = {}
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"

        # 客户端状态相关
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"
        # 监听状态机：idle -> listening -> finalizing -> idle
        self.listen_state = "idle"
        self._listen_state_timer = None
        self._last_listen_event_ms = 0

        # 线程任务相关
        self.loop = asyncio.get_event_loop()
        self.stop_event = threading.Event()
        # 缩减线程池，降低上下文切换与内存占用
        try:
            meeting_cfg = self.config.get("meeting", {}) if isinstance(self.config, dict) else {}
            # 固化 W3：线程池默认 2，可被 meeting.threadpool_max_workers 覆盖
            default_workers = 2
            max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
            if max_workers < 1:
                max_workers = default_workers
        except Exception:
            max_workers = 2
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 添加上报线程池
        self.report_queue = queue.Queue()
        self.report_thread = None
        # 未来可以通过修改此处，调节asr的上报和tts的上报，目前默认都开启
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # 依赖的组件
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_no_voice_last_time = 0.0
        self.client_voice_stop = False
        self.client_voice_frame_count = 0

        # asr相关变量
        # 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
        # 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()

        # llm相关变量
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # tts相关变量
        self.sentence_id = None

        # iot相关变量
        self.iot_descriptors = {}
        self.func_handler = None

        # 模式状态（meeting/coding/working/dialog）
        # 阶段2默认进入 connected.idle，欢迎页不允许渲染
        self.current_mode = "connected.idle"
        # 会议模式相关缓存
        self.meeting_segments = []  # [{"ts": int(ms), "text": str}]
        self.meeting_start_ts = 0.0
        self.meeting_last_snippet_ts = 0.0
        self.meeting_last_snippet_index = 0
        # 会议片段节流与幂等状态
        self.meeting_recent_texts = {}
        self.meeting_pending_texts = []
        self.meeting_last_emit_ms = 0.0
        self.meeting_finalized = False
        # 编码模式日志流运行标志/阶段名（用于 stop/clear/phase 扩展）
        self.coding_stream_running = False
        self.coding_phase_name = ""

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        # 是否在聊天结束后关闭连接
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_task = None
        # 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
        try:
            base_idle = int(self.config.get("close_connection_no_voice_time", 600))
        except Exception:
            base_idle = 600
        self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭

        # {"mcp":true} 表示启用MCP功能
        self.features = None

        # LLM 按模式实例缓存（随连接释放）
        self._llm_cache = {}

    def _get_base_config(self) -> Dict[str, Any]:
        try:
            srv = getattr(self, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            if isinstance(base_cfg, dict):
                return base_cfg
        except Exception:
            pass
        return self.config if isinstance(self.config, dict) else {}

    def get_llm_for(self, purpose: str):
        """按用途/模式返回 LLM 实例，懒加载并缓存。

        purpose 可取："chat" | "meeting" | "coding" | "working" | "intent" | "memory"
        """
        try:
            key = str(purpose or "chat").lower()
        except Exception:
            key = "chat"

        # 缓存命中
        if key in self._llm_cache and self._llm_cache[key] is not None:
            return self._llm_cache[key]

        base_cfg = self._get_base_config()
        # 读取映射
        mapping = {}
        try:
            mapping = base_cfg.get("llm_by_mode", {}) or {}
        except Exception:
            mapping = {}

        mapping_val = mapping.get(key, None)
        if mapping_val is None:
            # 用途未配置专用 LLM，回退 default 并记录告警
            try:
                self.logger.bind(tag=TAG).warning(
                    f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
                )
            except Exception:
                pass
            mapping_val = mapping.get("default")

        alias = None
        overrides = None
        if isinstance(mapping_val, dict):
            # 支持 { alias: xxx, overrides: { model_name: '...' } } 或直接平铺覆盖字段
            alias = mapping_val.get("alias") or mapping_val.get("name") or mapping_val.get("module") or mapping_val.get("llm")
            overrides = mapping_val.get("overrides")
            if overrides is None:
                # 将除别名键外的其余键视为覆盖
                tmp = dict(mapping_val)
                for k in ["alias", "name", "module", "llm", "overrides"]:
                    tmp.pop(k, None)
                overrides = tmp if len(tmp) > 0 else None
        elif isinstance(mapping_val, str) and len(mapping_val) > 0:
            alias = mapping_val

        # 回退默认 alias
        try:
            if alias is None:
                alias = self.config["selected_module"]["LLM"]
        except Exception:
            alias = None

        # 若无覆盖且别名等于当前默认，直接复用
        try:
            current_default_alias = self.config["selected_module"]["LLM"]
            if (overrides is None or len(overrides) == 0) and alias == current_default_alias and getattr(self, "llm", None) is not None:
                self._llm_cache[key] = self.llm
                return self.llm
        except Exception:
            pass

        # 统一委托 server 级共享工厂；失败回退默认 LLM
        try:
            srv = getattr(self, "server", None)
            if srv and hasattr(srv, "get_or_create_llm") and callable(getattr(srv, "get_or_create_llm")) and alias:
                instance = srv.get_or_create_llm(alias, overrides)
                if instance is not None:
                    self._llm_cache[key] = instance
                    return instance
            # 回退默认
            self._llm_cache[key] = self.llm
            return self.llm
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
            self._llm_cache[key] = self.llm
            return self.llm

    async def handle_connection(self, ws, path=None):
        try:
            # 获取并验证headers（兼容 websockets 库的属性命名）
            try:
                raw_headers = getattr(ws, "request_headers", {})
                # 统一小写键，便于后续从 headers 获取 authorization/device-id
                headers_lower = {}
                try:
                    # 优先使用 items() 以兼容 websockets 的 Headers 类型
                    for k, v in raw_headers.items():
                        headers_lower[str(k).lower()] = v
                except Exception:
                    try:
                        headers_lower = {str(k).lower(): v for k, v in dict(raw_headers).items()}
                    except Exception:
                        headers_lower = {}
                self.headers = headers_lower
            except Exception:
                self.headers = {}

            # 统一调用服务器封装的握手解析；其次尝试 Header；最后回退自动分配
            device_id_from_query = None
            client_id_from_query = None
            raw_path_from_server = None
            try:
                server_obj = getattr(self, "server", None)
                if server_obj and hasattr(server_obj, "parse_ids_from_handshake"):
                    d, c, rawp = server_obj.parse_ids_from_handshake(ws, path)
                    device_id_from_query = d
                    client_id_from_query = c
                    raw_path_from_server = rawp
            except Exception:
                pass

            # 从 Header 兜底解析（包含非规范写法）
            def _normalize_id(v):
                try:
                    if v is None:
                        return None
                    vv = str(v).strip().strip('"').strip("'")
                    return vv.lower() if vv else None
                except Exception:
                    return None
            header_device_id = _normalize_id(
                self.headers.get("device-id")
                or self.headers.get("device_id")
                or self.headers.get("x-device-id")
                or self.headers.get("x-device_id")
            )
            header_client_id = _normalize_id(
                self.headers.get("client-id")
                or self.headers.get("client_id")
                or self.headers.get("x-client-id")
                or self.headers.get("x-client_id")
            )

            # 赋值优先级：Query > Header > 回退
            chosen_device_id = device_id_from_query or header_device_id or header_client_id
            chosen_client_id = client_id_from_query or header_client_id or chosen_device_id

            if chosen_device_id:
                self.headers["device-id"] = chosen_device_id
                if chosen_client_id:
                    self.headers["client-id"] = chosen_client_id
                # 打印来源与解析快照（包含原始 path 片段便于定位异常客户端）
                try:
                    raw_paths_snapshot = []
                    if isinstance(raw_path_from_server, str) and raw_path_from_server:
                        raw_paths_snapshot.append(raw_path_from_server[:256])
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                        for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                            val = getattr(ws, attr, "")
                            if isinstance(val, str) and val:
                                raw_paths_snapshot.append(val[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    src = "query" if device_id_from_query else "header"
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={src}, rawPaths={truncate_for_log(str(raw_paths_snapshot))})"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={'query' if device_id_from_query else 'header'})"
                    )
            else:
                # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
                auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
                self.headers["device-id"] = auto_device_id
                self.headers["client-id"] = auto_device_id
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    header_keys = list(self.headers.keys())
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; rawPaths={truncate_for_log(str(raw_paths_snapshot))}, headerKeys={truncate_for_log(str(header_keys))}"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
                    )
            # 获取客户端ip地址
            try:
                remote = getattr(ws, "remote_address", None)
                if isinstance(remote, tuple) and len(remote) >= 1:
                    self.client_ip = remote[0]
                else:
                    self.client_ip = str(remote) if remote is not None else ""
            except Exception:
                self.client_ip = ""
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # 进行认证
            await self.auth.authenticate(self.headers)

            # 认证通过,继续处理
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)
            # 在 server 上注册设备路由（自动断开旧连接）
            if self.server and self.device_id:
                ok = await self.server.register_device_handler(self.device_id, self)
                if ok is False:
                    self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
                    await ws.send("设备注册失败")
                    await self.close(ws)
                    return

            # 启动超时检查任务
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.websocket.send(json.dumps(self.welcome_msg))

            # 获取差异化配置
            self._initialize_private_config()
            # 异步初始化
            self.executor.submit(self._initialize_components)

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            try:
                safe_e = truncate_for_log(str(e))
                safe_tb = truncate_for_log(stack_trace)
            except Exception:
                safe_e = str(e)
                safe_tb = stack_trace
            self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
            return
        finally:
            try:
                # 注销设备路由映射
                if self.server and self.device_id:
                    await self.server.unregister_device_handler(self.device_id, self)
            finally:
                await self._save_and_close(ws)

    async def _save_and_close(self, ws):
        """保存记忆并关闭连接"""
        try:
            if self.memory:
                # 使用线程池异步保存记忆
                def save_memory_task():
                    try:
                        # 创建新事件循环（避免与主循环冲突）
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            self.memory.save_memory(self.dialogue.dialogue)
                        )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
                    finally:
                        loop.close()

                # 启动线程保存记忆，不等待完成
                threading.Thread(target=save_memory_task, daemon=True).start()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
        finally:
            # 立即关闭连接，不等待记忆保存完成
            await self.close(ws)

    def reset_timeout(self):
        """重置超时计时器"""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._check_timeout())

    async def _route_message(self, message):
        """消息路由"""
        # 重置超时计时器
        self.reset_timeout()

        if isinstance(message, str):
            # 轻量 ping/keepalive：收到后仅重置计时器并忽略
            try:
                import json as _json
                try:
                    obj = _json.loads(message)
                except Exception:
                    obj = None
                if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
                    try:
                        # 可选：立即回 pong
                        await self.websocket.send(_json.dumps({"type": "pong"}))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None:
                return
            if self.asr is None:
                return
            self.asr_audio_queue.put(message)

    async def handle_restart(self, message):
        """处理服务器重启请求"""
        try:

            self.logger.bind(tag=TAG).info("收到服务器重启指令，准备执行...")

            # 发送确认响应
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "服务器重启中...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # 异步执行重启操作
            def restart_server():
                """实际执行重启的方法"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("执行服务器重启...")
                # 后台重启：避免继承TTY，全部重定向，保证 nohup/backgroud 模式不被SIGTTIN挂起
                with open(os.devnull, "rb", buffering=0) as devnull_in, \
                     open(os.devnull, "ab", buffering=0) as devnull_out, \
                     open(os.devnull, "ab", buffering=0) as devnull_err:
                    subprocess.Popen(
                        [sys.executable, "app.py"],
                        stdin=devnull_in,
                        stdout=devnull_out,
                        stderr=devnull_err,
                        start_new_session=True,
                        close_fds=True,
                    )
                os._exit(0)

            # 使用线程执行重启避免阻塞事件循环
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"重启失败: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            update_module_string(self.selected_module_str)
            """初始化组件"""
            if self.config.get("prompt") is not None:
                self.prompt = self.config["prompt"]
                self.change_system_prompt(self.prompt)
                self.logger.bind(tag=TAG).info(
                    f"初始化组件: prompt成功 {self.prompt[:50]}..."
                )

            """初始化本地组件"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()
            # 打开语音识别通道
            asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)

            if self.tts is None:
                self.tts = self._initialize_tts()
            # 会议模式可禁用 TTS 通道（懒启动）
            disable_tts = False
            try:
                srv = getattr(self, "server", None)
                base_cfg = getattr(srv, "config", None) if srv else None
                if isinstance(base_cfg, dict):
                    meeting_cfg2 = base_cfg.get("meeting", {})
                else:
                    meeting_cfg2 = self.config.get("meeting", {})
                disable_tts = bool(meeting_cfg2.get("disable_tts", False))
            except Exception:
                disable_tts = False
            if not disable_tts:
                asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)

            """加载记忆"""
            self._initialize_memory()
            """加载意图识别"""
            self._initialize_intent()
            """初始化上报线程"""
            self._init_report_threads()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"实例化组件失败: {e}")

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程已启动")

    def _initialize_tts(self):
        """初始化TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

    def _initialize_asr(self):
        """初始化ASR"""
        if self._asr.interface_type == InterfaceType.LOCAL:
            # 如果公共ASR是本地服务，则直接返回
            # 因为本地一个实例ASR，可以被多个连接共享
            asr = self._asr
        else:
            # 如果公共ASR是远程服务，则初始化一个新实例
            # 因为远程ASR，涉及到websocket连接和接收线程，需要每个连接一个实例
            asr = initialize_asr(self.config)

        return asr

    def _initialize_private_config(self):
        """如果是从配置文件获取，则进行二次实例化"""
        if not self.read_config_from_api:
            return
        """从接口获取差异化的配置进行二次实例化，非全量重新实例化"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} 秒，获取差异化配置成功: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get("selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # 加载插件配置
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                self.config["plugins"] = plugin_from_server
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = plugin_from_server.keys()
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """初始化记忆模块"""
        # 按模式选择记忆总结 LLM（可被 llm_by_mode.memory 覆盖）
        chosen_llm = self.llm
        try:
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                selected = self.get_llm_for("memory")
                if selected is not None:
                    chosen_llm = selected
        except Exception:
            pass

        self.memory.init_memory(
            role_id=self.device_id,
            llm=chosen_llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # 获取记忆总结配置
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # 如果使用 nomen，直接返回
        if memory_type == "nomem":
            return
        # 使用 mem_local_short 模式
        elif memory_type == "mem_local_short":
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get("type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为记忆总结创建了专用LLM: {memory_llm_name}, 类型: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # 否则使用主LLM
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """初始化意图识别模块"""
        # 获取意图识别配置
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # 如果使用 nointent，直接返回
        if intent_type == "nointent":
            return
        # 使用 intent_llm 模式
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为意图识别创建了专用LLM: {intent_llm_name}, 类型: {intent_llm_type}"
                )
                # 按模式选择意图识别 LLM（可被 llm_by_mode.intent 覆盖）
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(intent_llm)
                    else:
                        self.intent.set_llm(intent_llm)
                except Exception:
                    self.intent.set_llm(intent_llm)
            else:
                # 否则使用主LLM
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(self.llm)
                    else:
                        self.intent.set_llm(self.llm)
                except Exception:
                    self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """加载插件"""
        self.func_handler = FunctionHandler(self)
        self.mcp_manager = MCPManager(self)

        """加载MCP工具"""
        asyncio.run_coroutine_threadsafe(
            self.mcp_manager.initialize_servers(), self.loop
        )

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # 更新系统prompt至上下文
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, tool_call=False):
        try:
            safe_query = truncate_for_log(query)
        except Exception:
            safe_query = query
        self.logger.bind(tag=TAG).info(f"大模型收到用户消息: {safe_query}")
        self.llm_finish_task = False
        # 阶段2：进入对话活跃态（不再下发额外占位渲染，避免 c1→p1 的瞬时切换）
        try:
            self.current_mode = "dialog.active"
        except Exception:
            pass

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        if hasattr(self, "mcp_client"):
            mcp_tools = self.mcp_client.get_available_tools()
            if mcp_tools is not None and len(mcp_tools) > 0:
                if functions is None:
                    functions = []
                functions.extend(mcp_tools)
        response_message = []

        try:
            # 使用带记忆的对话
            memory_str = None
            if self.memory is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            self.sentence_id = str(uuid.uuid4().hex)


            # 按当前模式选择 LLM（默认chat；coding/working 切换对应别名）
            purpose = self.current_mode or "chat"
            active_llm = self.llm
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                try:
                    active_llm = self.get_llm_for(purpose) or self.llm
                except Exception:
                    active_llm = self.llm

            if self.intent_type == "function_call" and functions is not None:
                # 使用支持functions的streaming接口
                llm_responses = active_llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                    functions=functions,
                )
            else:
                llm_responses = active_llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        text_index = 0
        self.client_abort = False
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    # print("content_arguments", content_arguments)
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response
            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    if text_index == 0:
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=self.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )
                    text_index += 1
        # 处理function call
        if tool_call_flag:
            bHasError = False
            if function_id is None:
                a = extract_json_from_string(content_arguments)
                if a is not None:
                    try:
                        content_arguments_json = json.loads(a)
                        function_name = content_arguments_json["name"]
                        function_arguments = json.dumps(
                            content_arguments_json["arguments"], ensure_ascii=False
                        )
                        function_id = str(uuid.uuid4().hex)
                    except Exception as e:
                        bHasError = True
                        response_message.append(a)
                else:
                    bHasError = True
                    response_message.append(content_arguments)
                if bHasError:
                    self.logger.bind(tag=TAG).error(
                        f"function call error: {content_arguments}"
                    )
            if not bHasError:
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # 处理Server端MCP工具调用
                if self.mcp_manager.is_mcp_tool(function_name):
                    result = self._handle_mcp_tool_call(function_call_data)
                elif hasattr(self, "mcp_client") and self.mcp_client.has_tool(
                    function_name
                ):
                    # 如果是小智端MCP工具调用
                    self.logger.bind(tag=TAG).debug(
                        f"调用小智端MCP工具: {function_name}, 参数: {function_arguments}"
                    )
                    try:
                        result = asyncio.run_coroutine_threadsafe(
                            call_mcp_tool(
                                self, self.mcp_client, function_name, function_arguments
                            ),
                            self.loop,
                        ).result()
                        self.logger.bind(tag=TAG).debug(f"MCP工具调用结果: {result}")

                        resultJson = None
                        if isinstance(result, str):
                            try:
                                resultJson = json.loads(result)
                            except Exception as e:
                                self.logger.bind(tag=TAG).error(
                                    f"解析MCP工具返回结果失败: {e}"
                                )

                        # 视觉大模型不经过二次LLM处理
                        if (
                            resultJson is not None
                            and isinstance(resultJson, dict)
                            and "action" in resultJson
                        ):
                            result = ActionResponse(
                                action=Action[resultJson["action"]],
                                result=None,
                                response=resultJson.get("response", ""),
                            )
                        else:
                            result = ActionResponse(
                                action=Action.REQLLM, result=result, response=""
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
                        result = ActionResponse(
                            action=Action.REQLLM, result="MCP工具调用失败", response=""
                        )
                else:
                    # 处理系统函数
                    result = self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    )
                self._handle_function_result(result, function_call_data)

        # 存储对话内容
        if len(response_message) > 0:
            self.dialogue.put(
                Message(role="assistant", content="".join(response_message))
            )
            # 将最终回答渲染为 list 视图，遵循 hardware-ui-design.md 对话页面
            try:
                final_text = "".join(response_message)
                # 提取最近一条用户内容与近几条历史用户文本
                latest_user_text = None
                history_user = []
                try:
                    for m in reversed(self.dialogue.dialogue):
                        if m.role == "user" and latest_user_text is None:
                            latest_user_text = m.content
                        elif m.role == "user" and len(history_user) < 3:
                            history_user.append(m.content)
                        if latest_user_text and len(history_user) >= 3:
                            break
                except Exception:
                    pass

                try:
                    _, owner_name = get_badge_and_owner(getattr(self, "device_id", "")) or ("", "")
                except Exception:
                    owner_name = ""
                # 读取最近两次完整对话的“会话级摘要”
                summaries = get_recent_chat_summaries(getattr(self, "device_id", ""), limit=2)
                # 将摘要放在“历史对话”区域（最多两条）
                items = build_dialog_chat_items(owner_name, "喵喵同学", latest_user_text or "", final_text, summaries)
                payload_final = {
                    "type": "ui.render",
                    "id": f"dlg-final-{self.sentence_id or ''}",
                    "page": "dialog.chat",
                    "header": {},
                    "body": {"kind": "list", "items": items},
                    "footer": {"hint": build_chat_footer_hint()}
                }
                asyncio.run_coroutine_threadsafe(send_render(self, payload_final), self.loop)

                # 不在轮次内保存“历史对话”（仅在会话关闭时保存整体摘要）
            except Exception:
                pass
        if text_index > 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )

        return True

    def _handle_mcp_tool_call(self, function_call_data):
        function_arguments = function_call_data["arguments"]
        function_name = function_call_data["name"]
        try:
            args_dict = function_arguments
            if isinstance(function_arguments, str):
                try:
                    args_dict = json.loads(function_arguments)
                except json.JSONDecodeError:
                    self.logger.bind(tag=TAG).error(
                        f"无法解析 function_arguments: {function_arguments}"
                    )
                    return ActionResponse(
                        action=Action.REQLLM, result="参数解析失败", response=""
                    )

            tool_result = asyncio.run_coroutine_threadsafe(
                self.mcp_manager.execute_tool(function_name, args_dict), self.loop
            ).result()
            # meta=None content=[TextContent(type='text', text='北京当前天气:\n温度: 21°C\n天气: 晴\n湿度: 6%\n风向: 西北 风\n风力等级: 5级', annotations=None)] isError=False
            content_text = ""
            if tool_result is not None and tool_result.content is not None:
                for content in tool_result.content:
                    content_type = content.type
                    if content_type == "text":
                        content_text = content.text
                    elif content_type == "image":
                        pass

            if len(content_text) > 0:
                return ActionResponse(
                    action=Action.REQLLM, result=content_text, response=""
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
            return ActionResponse(
                action=Action.REQLLM, result="工具调用出错", response=""
            )

        return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")

    def _handle_function_result(self, result, function_call_data):
        if result.action == Action.RESPONSE:  # 直接回复前端
            text = result.response
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4()) if function_id is None else function_id
                        ),
                        content=text,
                    )
                )
                self.chat(text, tool_call=True)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.result
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """聊天记录上报工作线程"""
        while not self.stop_event.is_set():
            try:
                # 从队列获取数据，设置超时以便定期检查停止事件
                item = self.report_queue.get(timeout=1)
                if item is None:  # 检测毒丸对象
                    break
                type, text, audio_data, report_time = item
                try:
                    # 检查线程池状态
                    if self.executor is None:
                        continue
                    # 提交任务到线程池
                    self.executor.submit(
                        self._process_report, type, text, audio_data, report_time
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"聊天记录上报线程异常: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"聊天记录上报工作线程异常: {e}")

        self.logger.bind(tag=TAG).info("聊天记录上报线程已退出")

    def _process_report(self, type, text, audio_data, report_time):
        """处理上报任务"""
        try:
            # 执行上报（传入二进制数据）
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"上报处理异常: {e}")
        finally:
            # 标记任务完成
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"清除服务端讲话状态")

    async def close(self, ws=None):
        """资源清理方法"""
        try:
            # 在会话关闭前，生成一次本轮“完整对话摘要”，加入历史（仅在存在有效轮次时）
            try:
                latest_user = None
                latest_assistant = None
                for m in reversed(self.dialogue.dialogue if isinstance(self.dialogue, Dialogue) else []):
                    if m.role == "assistant" and latest_assistant is None:
                        latest_assistant = m.content
                    elif m.role == "user" and latest_user is None:
                        latest_user = m.content
                    if latest_user and latest_assistant:
                        break
                if latest_user or latest_assistant:
                    try:
                        _, owner_name = get_badge_and_owner(getattr(self, "device_id", "")) or ("", "")
                    except Exception:
                        owner_name = ""
                    summary_text = f"{owner_name or '用户'}: {latest_user or ''} / 喵喵同学: {latest_assistant or ''}"
                    append_chat_summary(getattr(self, "device_id", ""), summary_text, max_items=2)
            except Exception:
                pass
            # 取消超时任务
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None

            # 取消编码洞察定时任务
            try:
                if hasattr(self, "coding_insight_task") and self.coding_insight_task and not self.coding_insight_task.done():
                    self.coding_insight_task.cancel()
            except Exception:
                pass

            # 清理MCP资源
            if hasattr(self, "mcp_manager") and self.mcp_manager:
                await self.mcp_manager.cleanup_all()

            # 触发停止事件
            if self.stop_event:
                self.stop_event.set()

            # 清空任务队列
            self.clear_queues()

            # 关闭WebSocket连接
            if ws:
                await ws.close()
            elif self.websocket:
                await self.websocket.close()

            # 最后关闭线程池（避免阻塞）
            if self.executor:
                try:
                    # Python 3.9+ 支持 cancel_futures
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    self.executor.shutdown(wait=False)
                self.executor = None

            # 清理 LLM 实例缓存
            try:
                if hasattr(self, "_llm_cache") and isinstance(self._llm_cache, dict):
                    self._llm_cache.clear()
            except Exception:
                pass

            # 关闭 asr/tts/llm 资源
            try:
                if hasattr(self, "asr") and hasattr(self.asr, "close") and callable(getattr(self.asr, "close")):
                    maybe_close = self.asr.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "tts") and hasattr(self.tts, "close") and callable(getattr(self.tts, "close")):
                    maybe_close = self.tts.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "llm") and hasattr(self.llm, "close") and callable(getattr(self.llm, "close")):
                    maybe_close = self.llm.close()  # 供应商可选实现
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass

            self.logger.bind(tag=TAG).info("连接资源已释放")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")

    def clear_queues(self):
        """清空所有任务队列"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

            # 使用非阻塞方式清空队列
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"清理结束: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self):
        """重置VAD状态，恢复到idle状态"""
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.listen_state = "idle"
        if self._listen_state_timer:
            self._listen_state_timer.cancel()
            self._listen_state_timer = None
        self.logger.bind(tag=TAG).debug("VAD states reset.")
    
    async def send_json(self, data: dict) -> bool:
        """统一的 JSON 消息发送封装，包含错误处理
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.websocket:
            self.logger.bind(tag=TAG).warning("send_json: websocket is None")
            return False
        
        try:
            # 优先使用 send_json 方法
            if hasattr(self.websocket, 'send_json'):
                await self.websocket.send_json(data)
            else:
                # 回退到字符串发送
                await self.websocket.send(json.dumps(data, ensure_ascii=False))
            return True
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，静默处理（预期情况）
            self.logger.bind(tag=TAG).debug(f"send_json: connection closed for device {self.device_id}")
            return False
        except Exception as e:
            # 其他异常，记录警告但不中断
            self.logger.bind(tag=TAG).warning(f"send_json failed for device {self.device_id}: {e}")
            return False
    
    async def send_text(self, text: str) -> bool:
        """统一的文本消息发送封装
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.websocket:
            self.logger.bind(tag=TAG).warning("send_text: websocket is None")
            return False
        
        try:
            await self.websocket.send(text)
            return True
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，静默处理
            self.logger.bind(tag=TAG).debug(f"send_text: connection closed for device {self.device_id}")
            return False
        except Exception as e:
            # 其他异常，记录警告
            self.logger.bind(tag=TAG).warning(f"send_text failed for device {self.device_id}: {e}")
            return False
    
    async def transition_listen_state(self, new_state: str):
        """状态机转换：idle -> listening -> finalizing -> idle"""
        old_state = self.listen_state
        if old_state == "idle" and new_state == "listening":
            self.listen_state = "listening"
            self._last_listen_event_ms = int(time.time() * 1000)
            self.logger.bind(tag=TAG).debug("Listen state: idle -> listening")
        elif old_state == "listening" and new_state == "finalizing":
            self.listen_state = "finalizing"
            self.logger.bind(tag=TAG).debug("Listen state: listening -> finalizing")
            # 触发一次handle_voice_stop
            if len(self.asr_audio) > 0:
                from core.handle.receiveAudioHandle import handleAudioMessage
                await handleAudioMessage(self, b"")
        elif old_state == "finalizing" and new_state == "idle":
            self.listen_state = "idle"
            self.logger.bind(tag=TAG).debug("Listen state: finalizing -> idle")
            self.reset_vad_states()
    
    def check_vad_fallback(self):
        """检查是否需要VAD兜底（超过fallback_ms未见设备边界）"""
        if self.listen_state != "listening":
            return False
        if self.client_listen_mode != "manual":
            return False
        now_ms = int(time.time() * 1000)
        fallback_ms = 2000  # 默认2秒
        try:
            base_cfg = self._get_base_config()
            meeting_cfg = base_cfg.get("meeting", {})
            fallback_ms = int(meeting_cfg.get("vad_fallback_ms", 2000))
        except Exception:
            pass
        last_event_ms = getattr(self, "_last_listen_event_ms", 0)
        if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
            self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
            return True
        return False

    async def send_text(self, text: str) -> None:
        """统一文本发送包装。"""
        try:
            if self.websocket:
                await self.websocket.send(text)
        except Exception:
            pass

    async def send_json(self, payload: dict) -> None:
        """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
        try:
            if self.websocket is None:
                return
            try:
                await self.websocket.send_json(payload)
            except AttributeError:
                import json as _json
                await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
        except Exception:
            # 发送错误不应中断主流程
            pass

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """检查连接超时"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.timeout_seconds)
                if not self.stop_event.is_set():
                    # 在关闭前先发送提示并提供缓冲期（与无声层策略一致）
                    try:
                        await self.websocket.send(json.dumps({
                            "type": "system",
                            "event": "timeout_warning",
                            "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
                        }))
                    except Exception:
                        pass
                    # 给予 10 秒缓冲，若期间收到任何消息，reset_timeout 会取消下一轮关闭
                    try:
                        await asyncio.sleep(10)
                    except Exception:
                        pass
                    if self.stop_event.is_set():
                        break
                    self.logger.bind(tag=TAG).info("连接超时，准备关闭")
                    await self.close(self.websocket)
                    break
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")

```

明白了，已按“整段会话=一次完整对话”的定义实现：

- 会话期内不再写入历史摘要
  - 移除了在每轮回答结束时写历史的逻辑。

- 仅在“断开连接/会话关闭”时汇总并入库
  - 在 `ConnectionHandler.close()` 开始处，从当前会话的对话队列中抓取“最后一条用户 + 最后一条助手”，拼成本轮会话的摘要，并通过 `append_chat_summary(device_id, summary, max_items=2)` 存储。
  - 历史区渲染时依旧读取 `get_recent_chat_summaries(device_id, 2)`，保证只显示最近两次完整会话的摘要。

现在历史对话只在断开（或被关闭）时更新，满足你的要求。

---

**User**

问题:当用户输入过多文本,大模型输出过多文本时,硬件屏幕(300*400)显示不下,所以在后端发送渲染引擎时,需要考虑单行的文本长度不要超出硬件屏幕的宽度(300);

---

**Cursor**

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional
import unicodedata
from copy import deepcopy
from config.logger import setup_logging
from core.utils.device_registry import get_display_title


_logger = setup_logging()


def _norm_str(v: Any) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v)
        s = s.strip()
        return s if len(s) > 0 else None
    except Exception:
        return None


def _ensure_list_of_str(items: Any, limit: int = 8) -> Optional[List[str]]:
    if not isinstance(items, list):
        return None
    out: List[str] = []
    for it in items:
        s = _norm_str(it)
        if s is None:
            continue
        out.append(s)
        if len(out) >= limit:
            break
    return out


def _normalize_device_id(v: Optional[str]) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v).strip().strip('"').strip("'")
        return s.lower() if s else None
    except Exception:
        return None


def clean_render_payload(device_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """轻量清洗渲染负载。仅允许 body.kind: text|list，并注入设备标题。

    - 强制保留字段：type=ui.render, page, header.title, body, footer.hint, id?
    - body: { kind: text, text } 或 { kind: list, items<=8 }
    - 其它未知字段忽略
    - 注入 header.title：若设备已注册 -> "工牌{badge} · {owner}"；未注册 -> 不注入，仅日志
    """
    if not isinstance(payload, dict):
        try:
            _logger.info("[DROP_INVALID] type=ui.render reason=payload-not-dict device=%s" % device_id)
        except Exception:
            pass
        return None

    device_id_norm = _normalize_device_id(device_id)
    if device_id_norm is None:
        try:
            _logger.info("[DROP_INVALID] type=ui.render reason=device-id-missing")
        except Exception:
            pass
        return None

    typ = _norm_str(payload.get("type")) or "ui.render"
    if typ != "ui.render":
        try:
            _logger.info(f"[DROP_INVALID] type={typ} reason=type-mismatch expected=ui.render device={device_id_norm}")
        except Exception:
            pass
        return None

    page = _norm_str(payload.get("page"))
    if page is None:
        try:
            _logger.info(f"[DROP_INVALID] type=ui.render reason=schema-invalid missing=page device={device_id_norm}")
        except Exception:
            pass
        return None

    header_in = payload.get("header") or {}
    body_in = payload.get("body") or {}
    footer_in = payload.get("footer") or {}

    body_kind = _norm_str(body_in.get("kind"))
    cleaned_body: Optional[Dict[str, Any]] = None
    if body_kind == "text":
        text = _norm_str(body_in.get("text")) or ""
        text = _wrap_text_to_width(text)
        cleaned_body = {"kind": "text", "text": text}
    elif body_kind == "list":
        items = _ensure_list_of_str(body_in.get("items"), limit=8) or []
        items = [_truncate_to_width(it) for it in items]
        cleaned_body = {"kind": "list", "items": items}
    else:
        # 不支持的 body，直接返回 None
        try:
            _logger.info(f"[DROP_INVALID] type=ui.render reason=unsupported-body-kind kind={body_kind} device={device_id_norm}")
        except Exception:
            pass
        return None

    # 注入标题策略：dialog.chat 标题为“对话模式”（设备端负责加左上角 C1 标识）；其他页面按设备标题注入
    if page == "dialog.chat":
        title = "对话模式"
    else:
        injected_title = get_display_title(device_id_norm)
        if injected_title is None:
            try:
                _logger.info(f"未注册设备，不注入标题 device={device_id_norm}")
            except Exception:
                pass
            title = _norm_str(header_in.get("title")) or ""
        else:
            title = injected_title

    cleaned: Dict[str, Any] = {
        "type": "ui.render",
        "page": page,
        "header": {"title": title},
        "body": cleaned_body,
    }

    # 透传 footer.hint 与 footer.page（若可解析）
    hint = _norm_str(footer_in.get("hint"))
    page_obj = footer_in.get("page") or {}
    try:
        page_index = int(page_obj.get("index"))
        page_total = int(page_obj.get("total"))
        if page_index >= 1 and page_total >= 1:
            footer_page = {"index": page_index, "total": page_total}
        else:
            footer_page = None
    except Exception:
        footer_page = None

    footer_out = {}
    if hint is not None:
        footer_out["hint"] = hint
    if footer_page is not None:
        footer_out["page"] = footer_page
    if len(footer_out) > 0:
        cleaned["footer"] = footer_out

    # 保留 id（幂等/ACK 关联）
    if payload.get("id") is not None:
        cleaned["id"] = str(payload.get("id"))

    return cleaned



```

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional
import unicodedata
from copy import deepcopy
from config.logger import setup_logging
from core.utils.device_registry import get_display_title


_logger = setup_logging()


def _norm_str(v: Any) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v)
        s = s.strip()
        return s if len(s) > 0 else None
    except Exception:
        return None


def _ensure_list_of_str(items: Any, limit: int = 8) -> Optional[List[str]]:
    if not isinstance(items, list):
        return None
    out: List[str] = []
    for it in items:
        s = _norm_str(it)
        if s is None:
            continue
        out.append(s)
        if len(out) >= limit:
            break
    return out


def _normalize_device_id(v: Optional[str]) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v).strip().strip('"').strip("'")
        return s.lower() if s else None
    except Exception:
        return None
def _char_display_width(ch: str) -> int:
    # 中日韩全角/宽字符按2，其他按1
    try:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            return 2
        return 1
    except Exception:
        return 1


def _truncate_to_width(s: str, max_units: int = 40) -> str:
    """按显示宽度截断至 max_units。单位：ASCII≈1，CJK≈2。

    估算：300px 宽，中文约16px 字号 → 一行≈18汉字；英文≈36字符。取40显示单位更保守。
    """
    if not s:
        return ""
    total = 0
    out_chars: List[str] = []
    for ch in s:
        w = _char_display_width(ch)
        if total + w > max_units:
            out_chars.append("…")
            break
        out_chars.append(ch)
        total += w
    return "".join(out_chars)


def _wrap_text_to_width(text: str, max_units_per_line: int = 40) -> str:
    """将长文本按显示宽度软换行，便于旧固件以单个 text 渲染时不溢出。"""
    if not text:
        return ""
    lines: List[str] = []
    current = []
    total = 0
    for ch in text:
        if ch == "\n":
            lines.append("".join(current))
            current, total = [], 0
            continue
        w = _char_display_width(ch)
        if total + w > max_units_per_line:
            lines.append("".join(current))
            current, total = [ch], w
        else:
            current.append(ch)
            total += w
    if current:
        lines.append("".join(current))
    return "\n".join(lines)



def clean_render_payload(device_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """轻量清洗渲染负载。仅允许 body.kind: text|list，并注入设备标题。

    - 强制保留字段：type=ui.render, page, header.title, body, footer.hint, id?
    - body: { kind: text, text } 或 { kind: list, items<=8 }
    - 其它未知字段忽略
    - 注入 header.title：若设备已注册 -> "工牌{badge} · {owner}"；未注册 -> 不注入，仅日志
    """
    if not isinstance(payload, dict):
        try:
            _logger.info("[DROP_INVALID] type=ui.render reason=payload-not-dict device=%s" % device_id)
        except Exception:
            pass
        return None

    device_id_norm = _normalize_device_id(device_id)
    if device_id_norm is None:
        try:
            _logger.info("[DROP_INVALID] type=ui.render reason=device-id-missing")
        except Exception:
            pass
        return None

    typ = _norm_str(payload.get("type")) or "ui.render"
    if typ != "ui.render":
        try:
            _logger.info(f"[DROP_INVALID] type={typ} reason=type-mismatch expected=ui.render device={device_id_norm}")
        except Exception:
            pass
        return None

    page = _norm_str(payload.get("page"))
    if page is None:
        try:
            _logger.info(f"[DROP_INVALID] type=ui.render reason=schema-invalid missing=page device={device_id_norm}")
        except Exception:
            pass
        return None

    header_in = payload.get("header") or {}
    body_in = payload.get("body") or {}
    footer_in = payload.get("footer") or {}

    body_kind = _norm_str(body_in.get("kind"))
    cleaned_body: Optional[Dict[str, Any]] = None
    if body_kind == "text":
        text = _norm_str(body_in.get("text")) or ""
        text = _wrap_text_to_width(text)
        cleaned_body = {"kind": "text", "text": text}
    elif body_kind == "list":
        items = _ensure_list_of_str(body_in.get("items"), limit=8) or []
        items = [_truncate_to_width(it) for it in items]
        cleaned_body = {"kind": "list", "items": items}
    else:
        # 不支持的 body，直接返回 None
        try:
            _logger.info(f"[DROP_INVALID] type=ui.render reason=unsupported-body-kind kind={body_kind} device={device_id_norm}")
        except Exception:
            pass
        return None

    # 注入标题策略：dialog.chat 标题为“对话模式”（设备端负责加左上角 C1 标识）；其他页面按设备标题注入
    if page == "dialog.chat":
        title = "对话模式"
    else:
        injected_title = get_display_title(device_id_norm)
        if injected_title is None:
            try:
                _logger.info(f"未注册设备，不注入标题 device={device_id_norm}")
            except Exception:
                pass
            title = _norm_str(header_in.get("title")) or ""
        else:
            title = injected_title

    cleaned: Dict[str, Any] = {
        "type": "ui.render",
        "page": page,
        "header": {"title": title},
        "body": cleaned_body,
    }

    # 透传 footer.hint 与 footer.page（若可解析）
    hint = _norm_str(footer_in.get("hint"))
    page_obj = footer_in.get("page") or {}
    try:
        page_index = int(page_obj.get("index"))
        page_total = int(page_obj.get("total"))
        if page_index >= 1 and page_total >= 1:
            footer_page = {"index": page_index, "total": page_total}
        else:
            footer_page = None
    except Exception:
        footer_page = None

    footer_out = {}
    if hint is not None:
        footer_out["hint"] = hint
    if footer_page is not None:
        footer_out["page"] = footer_page
    if len(footer_out) > 0:
        cleaned["footer"] = footer_out

    # 保留 id（幂等/ACK 关联）
    if payload.get("id") is not None:
        cleaned["id"] = str(payload.get("id"))

    return cleaned



```

- 已在后端渲染清洗阶段加入“按显示宽度限制/换行”：
  - `text`：调用 `_wrap_text_to_width` 进行软换行，避免单行超宽。
  - `list.items`：逐项调用 `_truncate_to_width` 截断并加省略号。
  - 宽度估算：ASCII≈1，CJK全角≈2，按 300×400、约16px 汉字行宽，保守上限设为每行约40显示单位（≈18汉字/≈36英文字符）。

- 生效位置
  - `backend/core/orchestration/render_schema.py` 中新增 `_char_display_width/_truncate_to_width/_wrap_text_to_width`，并在 `clean_render_payload()` 对 `text` 与 `list` 应用。

如需根据不同字号或字体微调每行宽度，我可将上限从40改为读取设备配置（例如 `devices.yaml` 增加 `chars_per_line`）。

---

**User**

没有用,现在超出的文本变成省略号了,应该助手会自动多几行,比如说:

(文先生:和我说一下那个昆明的天气吧？
喵喵同学:当前天气: 今晚多云。明天多云，
喵喵同学:明天多云，温度和今天差不多（23°），空气不错。
喵喵同学:详细参数： 西南风: 1级;
喵喵同学: 相对湿度: 74%;)

用户和助手的对话长度 最多打印10行 然后超过之后,就从第一行开始重新刷新;


---

**Cursor**

```python
from __future__ import annotations

from typing import List, Optional
import unicodedata


def _truncate(text: Optional[str], limit: int = 28) -> str:
    try:
        if text is None:
            return ""
        s = str(text).replace("\n", " ").strip()
        if len(s) <= limit:
            return s
        return s[: limit - 1] + "…"
    except Exception:
        return str(text or "")


def build_dialog_chat_items(user_name: str, assistant_name: str, latest_user_text: str, latest_assistant_text: str, history_user_texts: List[str]) -> List[str]:
    """构造对话模式(list)渲染内容，遵循 hardware-ui-design.md 的页面示意。

    限制：最多 8 行。
    结构：
    - > 正在对话中：
    - ─────────────
    - 文先生: <用户话>
    - 喵喵同学: <助手话>
    - 历史对话：
    - ─────────────
    - • <历史1>
    - • <历史2>
    """
    items: List[str] = []
    items.append(">对话中：")
    items.append("────────────────────────────────")
    user_display = user_name or "用户"
    assistant_display = assistant_name or "喵喵同学"
    if latest_user_text:
        items.append(f"{user_display}: {_truncate(latest_user_text)}")
    if latest_assistant_text:
        items.append(f"{assistant_display}: {_truncate(latest_assistant_text)}")

    # 历史对话（取最近的2条用户提问作为列表项，避免超过8行）
    hist = [t for t in (history_user_texts or []) if t]
    if len(hist) > 0 and len(items) < 8:
        items.append("历史对话：")
        items.append("────────────────────────────────")
        for t in hist[: max(0, 8 - len(items))]:
            items.append(f"• {_truncate(t)}")

    # 限制最多8行
    return items[:8]


def build_chat_footer_hint() -> str:
    return "说：\"结束对话\" | \"查看历史对话\" | \"进入其他模式\""


def _char_display_width(ch: str) -> int:
    try:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            return 2
        return 1
    except Exception:
        return 1


def wrap_label_text(label: str, text: str, max_units_per_line: int = 40) -> List[str]:
    """按显示宽度将 label+text 拆分为多行。每行都带相同的 label。"""
    label = str(label or "")
    text = str(text or "")
    # 计算每行可用宽度（扣除label占用）
    label_units = sum(_char_display_width(c) for c in label)
    avail = max(8, max_units_per_line - label_units)  # 至少保留8单位，避免死循环

    lines: List[str] = []
    current: List[str] = []
    total = 0
    def flush():
        if current:
            lines.append(label + "".join(current))

    for ch in text:
        if ch == "\n":
            flush()
            current, total = [], 0
            continue
        w = _char_display_width(ch)
        if total + w > avail:
            flush()
            current, total = [ch], w
        else:
            current.append(ch)
            total += w
    flush()
    if not lines:
        lines.append(label)
    return lines



```

```python
from __future__ import annotations

from typing import List, Optional
import unicodedata


def _truncate(text: Optional[str], limit: int = 28) -> str:
    try:
        if text is None:
            return ""
        s = str(text).replace("\n", " ").strip()
        if len(s) <= limit:
            return s
        return s[: limit - 1] + "…"
    except Exception:
        return str(text or "")


def build_dialog_chat_items(user_name: str, assistant_name: str, latest_user_text: str, latest_assistant_text: str, history_user_texts: List[str]) -> List[str]:
    """构造对话模式(list)渲染内容，遵循 hardware-ui-design.md 的页面示意。

    限制：最多 8 行。
    结构：
    - > 正在对话中：
    - ─────────────
    - 文先生: <用户话>
    - 喵喵同学: <助手话>
    - 历史对话：
    - ─────────────
    - • <历史1>
    - • <历史2>
    """
    items: List[str] = []
    items.append(">对话中：")
    items.append("────────────────────────────────")
    user_display = user_name or "用户"
    assistant_display = assistant_name or "喵喵同学"
    if latest_user_text:
        items.extend(wrap_label_text(f"{user_display}: ", latest_user_text))
    if latest_assistant_text:
        items.extend(wrap_label_text(f"{assistant_display}: ", latest_assistant_text))

    # 历史对话（取最近的2条用户提问作为列表项，避免超过8行）
    hist = [t for t in (history_user_texts or []) if t]
    if len(hist) > 0 and len(items) < 8:
        items.append("历史对话：")
        items.append("────────────────────────────────")
        for t in hist:
            if len(items) >= 8:
                break
            items.append(f"• {_truncate(t)}")

    # 限制最多8行
    return items[:8]


def build_chat_footer_hint() -> str:
    return "说：\"结束对话\" | \"查看历史对话\" | \"进入其他模式\""


def _char_display_width(ch: str) -> int:
    try:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            return 2
        return 1
    except Exception:
        return 1


def wrap_label_text(label: str, text: str, max_units_per_line: int = 40) -> List[str]:
    """按显示宽度将 label+text 拆分为多行。每行都带相同的 label。"""
    label = str(label or "")
    text = str(text or "")
    # 计算每行可用宽度（扣除label占用）
    label_units = sum(_char_display_width(c) for c in label)
    avail = max(8, max_units_per_line - label_units)  # 至少保留8单位，避免死循环

    lines: List[str] = []
    current: List[str] = []
    total = 0
    def flush():
        if current:
            lines.append(label + "".join(current))

    for ch in text:
        if ch == "\n":
            flush()
            current, total = [], 0
            continue
        w = _char_display_width(ch)
        if total + w > avail:
            flush()
            current, total = [ch], w
        else:
            current.append(ch)
            total += w
    flush()
    if not lines:
        lines.append(label)
    return lines



```

```python
import os
import sys
import copy
import json
import uuid
import time
import queue
import asyncio
import threading
import traceback
from config.logger import truncate_for_log
import subprocess
import websockets
from core.handle.mcpHandle import call_mcp_tool
from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
)
from typing import Dict, Any
from core.mcp.manager import MCPManager
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.handle.functionHandler import FunctionHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, update_module_string
from config.manage_api_client import DeviceNotFoundException, DeviceBindException
from core.orchestration.render_sender import send_render
from core.orchestration.dialog_ui import build_dialog_chat_items, build_chat_footer_hint
from core.utils.device_registry import get_badge_and_owner
from core.orchestration.history_store import append_chat_summary, get_recent_chat_summaries
from core.utils.dialogue import Dialogue


TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # 保存server实例的引用

        self.auth = AuthMiddleware(config)
        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.client_ip_info = {}
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"

        # 客户端状态相关
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"
        # 监听状态机：idle -> listening -> finalizing -> idle
        self.listen_state = "idle"
        self._listen_state_timer = None
        self._last_listen_event_ms = 0

        # 线程任务相关
        self.loop = asyncio.get_event_loop()
        self.stop_event = threading.Event()
        # 缩减线程池，降低上下文切换与内存占用
        try:
            meeting_cfg = self.config.get("meeting", {}) if isinstance(self.config, dict) else {}
            # 固化 W3：线程池默认 2，可被 meeting.threadpool_max_workers 覆盖
            default_workers = 2
            max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
            if max_workers < 1:
                max_workers = default_workers
        except Exception:
            max_workers = 2
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 添加上报线程池
        self.report_queue = queue.Queue()
        self.report_thread = None
        # 未来可以通过修改此处，调节asr的上报和tts的上报，目前默认都开启
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # 依赖的组件
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_no_voice_last_time = 0.0
        self.client_voice_stop = False
        self.client_voice_frame_count = 0

        # asr相关变量
        # 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
        # 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()

        # llm相关变量
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # tts相关变量
        self.sentence_id = None

        # iot相关变量
        self.iot_descriptors = {}
        self.func_handler = None

        # 模式状态（meeting/coding/working/dialog）
        # 阶段2默认进入 connected.idle，欢迎页不允许渲染
        self.current_mode = "connected.idle"
        # 会议模式相关缓存
        self.meeting_segments = []  # [{"ts": int(ms), "text": str}]
        self.meeting_start_ts = 0.0
        self.meeting_last_snippet_ts = 0.0
        self.meeting_last_snippet_index = 0
        # 会议片段节流与幂等状态
        self.meeting_recent_texts = {}
        self.meeting_pending_texts = []
        self.meeting_last_emit_ms = 0.0
        self.meeting_finalized = False
        # 编码模式日志流运行标志/阶段名（用于 stop/clear/phase 扩展）
        self.coding_stream_running = False
        self.coding_phase_name = ""

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        # 是否在聊天结束后关闭连接
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_task = None
        # 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
        try:
            base_idle = int(self.config.get("close_connection_no_voice_time", 600))
        except Exception:
            base_idle = 600
        self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭

        # {"mcp":true} 表示启用MCP功能
        self.features = None

        # LLM 按模式实例缓存（随连接释放）
        self._llm_cache = {}

    def _get_base_config(self) -> Dict[str, Any]:
        try:
            srv = getattr(self, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            if isinstance(base_cfg, dict):
                return base_cfg
        except Exception:
            pass
        return self.config if isinstance(self.config, dict) else {}

    def get_llm_for(self, purpose: str):
        """按用途/模式返回 LLM 实例，懒加载并缓存。

        purpose 可取："chat" | "meeting" | "coding" | "working" | "intent" | "memory"
        """
        try:
            key = str(purpose or "chat").lower()
        except Exception:
            key = "chat"

        # 缓存命中
        if key in self._llm_cache and self._llm_cache[key] is not None:
            return self._llm_cache[key]

        base_cfg = self._get_base_config()
        # 读取映射
        mapping = {}
        try:
            mapping = base_cfg.get("llm_by_mode", {}) or {}
        except Exception:
            mapping = {}

        mapping_val = mapping.get(key, None)
        if mapping_val is None:
            # 用途未配置专用 LLM，回退 default 并记录告警
            try:
                self.logger.bind(tag=TAG).warning(
                    f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
                )
            except Exception:
                pass
            mapping_val = mapping.get("default")

        alias = None
        overrides = None
        if isinstance(mapping_val, dict):
            # 支持 { alias: xxx, overrides: { model_name: '...' } } 或直接平铺覆盖字段
            alias = mapping_val.get("alias") or mapping_val.get("name") or mapping_val.get("module") or mapping_val.get("llm")
            overrides = mapping_val.get("overrides")
            if overrides is None:
                # 将除别名键外的其余键视为覆盖
                tmp = dict(mapping_val)
                for k in ["alias", "name", "module", "llm", "overrides"]:
                    tmp.pop(k, None)
                overrides = tmp if len(tmp) > 0 else None
        elif isinstance(mapping_val, str) and len(mapping_val) > 0:
            alias = mapping_val

        # 回退默认 alias
        try:
            if alias is None:
                alias = self.config["selected_module"]["LLM"]
        except Exception:
            alias = None

        # 若无覆盖且别名等于当前默认，直接复用
        try:
            current_default_alias = self.config["selected_module"]["LLM"]
            if (overrides is None or len(overrides) == 0) and alias == current_default_alias and getattr(self, "llm", None) is not None:
                self._llm_cache[key] = self.llm
                return self.llm
        except Exception:
            pass

        # 统一委托 server 级共享工厂；失败回退默认 LLM
        try:
            srv = getattr(self, "server", None)
            if srv and hasattr(srv, "get_or_create_llm") and callable(getattr(srv, "get_or_create_llm")) and alias:
                instance = srv.get_or_create_llm(alias, overrides)
                if instance is not None:
                    self._llm_cache[key] = instance
                    return instance
            # 回退默认
            self._llm_cache[key] = self.llm
            return self.llm
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
            self._llm_cache[key] = self.llm
            return self.llm

    async def handle_connection(self, ws, path=None):
        try:
            # 获取并验证headers（兼容 websockets 库的属性命名）
            try:
                raw_headers = getattr(ws, "request_headers", {})
                # 统一小写键，便于后续从 headers 获取 authorization/device-id
                headers_lower = {}
                try:
                    # 优先使用 items() 以兼容 websockets 的 Headers 类型
                    for k, v in raw_headers.items():
                        headers_lower[str(k).lower()] = v
                except Exception:
                    try:
                        headers_lower = {str(k).lower(): v for k, v in dict(raw_headers).items()}
                    except Exception:
                        headers_lower = {}
                self.headers = headers_lower
            except Exception:
                self.headers = {}

            # 统一调用服务器封装的握手解析；其次尝试 Header；最后回退自动分配
            device_id_from_query = None
            client_id_from_query = None
            raw_path_from_server = None
            try:
                server_obj = getattr(self, "server", None)
                if server_obj and hasattr(server_obj, "parse_ids_from_handshake"):
                    d, c, rawp = server_obj.parse_ids_from_handshake(ws, path)
                    device_id_from_query = d
                    client_id_from_query = c
                    raw_path_from_server = rawp
            except Exception:
                pass

            # 从 Header 兜底解析（包含非规范写法）
            def _normalize_id(v):
                try:
                    if v is None:
                        return None
                    vv = str(v).strip().strip('"').strip("'")
                    return vv.lower() if vv else None
                except Exception:
                    return None
            header_device_id = _normalize_id(
                self.headers.get("device-id")
                or self.headers.get("device_id")
                or self.headers.get("x-device-id")
                or self.headers.get("x-device_id")
            )
            header_client_id = _normalize_id(
                self.headers.get("client-id")
                or self.headers.get("client_id")
                or self.headers.get("x-client-id")
                or self.headers.get("x-client_id")
            )

            # 赋值优先级：Query > Header > 回退
            chosen_device_id = device_id_from_query or header_device_id or header_client_id
            chosen_client_id = client_id_from_query or header_client_id or chosen_device_id

            if chosen_device_id:
                self.headers["device-id"] = chosen_device_id
                if chosen_client_id:
                    self.headers["client-id"] = chosen_client_id
                # 打印来源与解析快照（包含原始 path 片段便于定位异常客户端）
                try:
                    raw_paths_snapshot = []
                    if isinstance(raw_path_from_server, str) and raw_path_from_server:
                        raw_paths_snapshot.append(raw_path_from_server[:256])
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                        for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                            val = getattr(ws, attr, "")
                            if isinstance(val, str) and val:
                                raw_paths_snapshot.append(val[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    src = "query" if device_id_from_query else "header"
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={src}, rawPaths={truncate_for_log(str(raw_paths_snapshot))})"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={'query' if device_id_from_query else 'header'})"
                    )
            else:
                # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
                auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
                self.headers["device-id"] = auto_device_id
                self.headers["client-id"] = auto_device_id
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    header_keys = list(self.headers.keys())
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; rawPaths={truncate_for_log(str(raw_paths_snapshot))}, headerKeys={truncate_for_log(str(header_keys))}"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
                    )
            # 获取客户端ip地址
            try:
                remote = getattr(ws, "remote_address", None)
                if isinstance(remote, tuple) and len(remote) >= 1:
                    self.client_ip = remote[0]
                else:
                    self.client_ip = str(remote) if remote is not None else ""
            except Exception:
                self.client_ip = ""
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # 进行认证
            await self.auth.authenticate(self.headers)

            # 认证通过,继续处理
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)
            # 在 server 上注册设备路由（自动断开旧连接）
            if self.server and self.device_id:
                ok = await self.server.register_device_handler(self.device_id, self)
                if ok is False:
                    self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
                    await ws.send("设备注册失败")
                    await self.close(ws)
                    return

            # 启动超时检查任务
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.websocket.send(json.dumps(self.welcome_msg))

            # 获取差异化配置
            self._initialize_private_config()
            # 异步初始化
            self.executor.submit(self._initialize_components)

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            try:
                safe_e = truncate_for_log(str(e))
                safe_tb = truncate_for_log(stack_trace)
            except Exception:
                safe_e = str(e)
                safe_tb = stack_trace
            self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
            return
        finally:
            try:
                # 注销设备路由映射
                if self.server and self.device_id:
                    await self.server.unregister_device_handler(self.device_id, self)
            finally:
                await self._save_and_close(ws)

    async def _save_and_close(self, ws):
        """保存记忆并关闭连接"""
        try:
            if self.memory:
                # 使用线程池异步保存记忆
                def save_memory_task():
                    try:
                        # 创建新事件循环（避免与主循环冲突）
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            self.memory.save_memory(self.dialogue.dialogue)
                        )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
                    finally:
                        loop.close()

                # 启动线程保存记忆，不等待完成
                threading.Thread(target=save_memory_task, daemon=True).start()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
        finally:
            # 立即关闭连接，不等待记忆保存完成
            await self.close(ws)

    def reset_timeout(self):
        """重置超时计时器"""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._check_timeout())

    async def _route_message(self, message):
        """消息路由"""
        # 重置超时计时器
        self.reset_timeout()

        if isinstance(message, str):
            # 轻量 ping/keepalive：收到后仅重置计时器并忽略
            try:
                import json as _json
                try:
                    obj = _json.loads(message)
                except Exception:
                    obj = None
                if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
                    try:
                        # 可选：立即回 pong
                        await self.websocket.send(_json.dumps({"type": "pong"}))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None:
                return
            if self.asr is None:
                return
            self.asr_audio_queue.put(message)

    async def handle_restart(self, message):
        """处理服务器重启请求"""
        try:

            self.logger.bind(tag=TAG).info("收到服务器重启指令，准备执行...")

            # 发送确认响应
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "服务器重启中...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # 异步执行重启操作
            def restart_server():
                """实际执行重启的方法"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("执行服务器重启...")
                # 后台重启：避免继承TTY，全部重定向，保证 nohup/backgroud 模式不被SIGTTIN挂起
                with open(os.devnull, "rb", buffering=0) as devnull_in, \
                     open(os.devnull, "ab", buffering=0) as devnull_out, \
                     open(os.devnull, "ab", buffering=0) as devnull_err:
                    subprocess.Popen(
                        [sys.executable, "app.py"],
                        stdin=devnull_in,
                        stdout=devnull_out,
                        stderr=devnull_err,
                        start_new_session=True,
                        close_fds=True,
                    )
                os._exit(0)

            # 使用线程执行重启避免阻塞事件循环
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"重启失败: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            update_module_string(self.selected_module_str)
            """初始化组件"""
            if self.config.get("prompt") is not None:
                self.prompt = self.config["prompt"]
                self.change_system_prompt(self.prompt)
                self.logger.bind(tag=TAG).info(
                    f"初始化组件: prompt成功 {self.prompt[:50]}..."
                )

            """初始化本地组件"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()
            # 打开语音识别通道
            asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)

            if self.tts is None:
                self.tts = self._initialize_tts()
            # 会议模式可禁用 TTS 通道（懒启动）
            disable_tts = False
            try:
                srv = getattr(self, "server", None)
                base_cfg = getattr(srv, "config", None) if srv else None
                if isinstance(base_cfg, dict):
                    meeting_cfg2 = base_cfg.get("meeting", {})
                else:
                    meeting_cfg2 = self.config.get("meeting", {})
                disable_tts = bool(meeting_cfg2.get("disable_tts", False))
            except Exception:
                disable_tts = False
            if not disable_tts:
                asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)

            """加载记忆"""
            self._initialize_memory()
            """加载意图识别"""
            self._initialize_intent()
            """初始化上报线程"""
            self._init_report_threads()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"实例化组件失败: {e}")

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程已启动")

    def _initialize_tts(self):
        """初始化TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

    def _initialize_asr(self):
        """初始化ASR"""
        if self._asr.interface_type == InterfaceType.LOCAL:
            # 如果公共ASR是本地服务，则直接返回
            # 因为本地一个实例ASR，可以被多个连接共享
            asr = self._asr
        else:
            # 如果公共ASR是远程服务，则初始化一个新实例
            # 因为远程ASR，涉及到websocket连接和接收线程，需要每个连接一个实例
            asr = initialize_asr(self.config)

        return asr

    def _initialize_private_config(self):
        """如果是从配置文件获取，则进行二次实例化"""
        if not self.read_config_from_api:
            return
        """从接口获取差异化的配置进行二次实例化，非全量重新实例化"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} 秒，获取差异化配置成功: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get("selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # 加载插件配置
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                self.config["plugins"] = plugin_from_server
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = plugin_from_server.keys()
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """初始化记忆模块"""
        # 按模式选择记忆总结 LLM（可被 llm_by_mode.memory 覆盖）
        chosen_llm = self.llm
        try:
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                selected = self.get_llm_for("memory")
                if selected is not None:
                    chosen_llm = selected
        except Exception:
            pass

        self.memory.init_memory(
            role_id=self.device_id,
            llm=chosen_llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # 获取记忆总结配置
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # 如果使用 nomen，直接返回
        if memory_type == "nomem":
            return
        # 使用 mem_local_short 模式
        elif memory_type == "mem_local_short":
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get("type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为记忆总结创建了专用LLM: {memory_llm_name}, 类型: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # 否则使用主LLM
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """初始化意图识别模块"""
        # 获取意图识别配置
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # 如果使用 nointent，直接返回
        if intent_type == "nointent":
            return
        # 使用 intent_llm 模式
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为意图识别创建了专用LLM: {intent_llm_name}, 类型: {intent_llm_type}"
                )
                # 按模式选择意图识别 LLM（可被 llm_by_mode.intent 覆盖）
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(intent_llm)
                    else:
                        self.intent.set_llm(intent_llm)
                except Exception:
                    self.intent.set_llm(intent_llm)
            else:
                # 否则使用主LLM
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(self.llm)
                    else:
                        self.intent.set_llm(self.llm)
                except Exception:
                    self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """加载插件"""
        self.func_handler = FunctionHandler(self)
        self.mcp_manager = MCPManager(self)

        """加载MCP工具"""
        asyncio.run_coroutine_threadsafe(
            self.mcp_manager.initialize_servers(), self.loop
        )

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # 更新系统prompt至上下文
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, tool_call=False):
        try:
            safe_query = truncate_for_log(query)
        except Exception:
            safe_query = query
        self.logger.bind(tag=TAG).info(f"大模型收到用户消息: {safe_query}")
        self.llm_finish_task = False
        # 阶段2：进入对话活跃态（不再下发额外占位渲染，避免 c1→p1 的瞬时切换）
        try:
            self.current_mode = "dialog.active"
        except Exception:
            pass

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        if hasattr(self, "mcp_client"):
            mcp_tools = self.mcp_client.get_available_tools()
            if mcp_tools is not None and len(mcp_tools) > 0:
                if functions is None:
                    functions = []
                functions.extend(mcp_tools)
        response_message = []

        try:
            # 使用带记忆的对话
            memory_str = None
            if self.memory is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            self.sentence_id = str(uuid.uuid4().hex)


            # 按当前模式选择 LLM（默认chat；coding/working 切换对应别名）
            purpose = self.current_mode or "chat"
            active_llm = self.llm
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                try:
                    active_llm = self.get_llm_for(purpose) or self.llm
                except Exception:
                    active_llm = self.llm

            if self.intent_type == "function_call" and functions is not None:
                # 使用支持functions的streaming接口
                llm_responses = active_llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                    functions=functions,
                )
            else:
                llm_responses = active_llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        text_index = 0
        self.client_abort = False
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    # print("content_arguments", content_arguments)
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response
            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    if text_index == 0:
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=self.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )
                    text_index += 1
        # 处理function call
        if tool_call_flag:
            bHasError = False
            if function_id is None:
                a = extract_json_from_string(content_arguments)
                if a is not None:
                    try:
                        content_arguments_json = json.loads(a)
                        function_name = content_arguments_json["name"]
                        function_arguments = json.dumps(
                            content_arguments_json["arguments"], ensure_ascii=False
                        )
                        function_id = str(uuid.uuid4().hex)
                    except Exception as e:
                        bHasError = True
                        response_message.append(a)
                else:
                    bHasError = True
                    response_message.append(content_arguments)
                if bHasError:
                    self.logger.bind(tag=TAG).error(
                        f"function call error: {content_arguments}"
                    )
            if not bHasError:
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # 处理Server端MCP工具调用
                if self.mcp_manager.is_mcp_tool(function_name):
                    result = self._handle_mcp_tool_call(function_call_data)
                elif hasattr(self, "mcp_client") and self.mcp_client.has_tool(
                    function_name
                ):
                    # 如果是小智端MCP工具调用
                    self.logger.bind(tag=TAG).debug(
                        f"调用小智端MCP工具: {function_name}, 参数: {function_arguments}"
                    )
                    try:
                        result = asyncio.run_coroutine_threadsafe(
                            call_mcp_tool(
                                self, self.mcp_client, function_name, function_arguments
                            ),
                            self.loop,
                        ).result()
                        self.logger.bind(tag=TAG).debug(f"MCP工具调用结果: {result}")

                        resultJson = None
                        if isinstance(result, str):
                            try:
                                resultJson = json.loads(result)
                            except Exception as e:
                                self.logger.bind(tag=TAG).error(
                                    f"解析MCP工具返回结果失败: {e}"
                                )

                        # 视觉大模型不经过二次LLM处理
                        if (
                            resultJson is not None
                            and isinstance(resultJson, dict)
                            and "action" in resultJson
                        ):
                            result = ActionResponse(
                                action=Action[resultJson["action"]],
                                result=None,
                                response=resultJson.get("response", ""),
                            )
                        else:
                            result = ActionResponse(
                                action=Action.REQLLM, result=result, response=""
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
                        result = ActionResponse(
                            action=Action.REQLLM, result="MCP工具调用失败", response=""
                        )
                else:
                    # 处理系统函数
                    result = self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    )
                self._handle_function_result(result, function_call_data)

        # 存储对话内容
        if len(response_message) > 0:
            self.dialogue.put(
                Message(role="assistant", content="".join(response_message))
            )
            # 将最终回答渲染为 list 视图，遵循 hardware-ui-design.md 对话页面
            try:
                final_text = "".join(response_message)
                # 提取最近一条用户内容与近几条历史用户文本
                latest_user_text = None
                history_user = []
                try:
                    for m in reversed(self.dialogue.dialogue):
                        if m.role == "user" and latest_user_text is None:
                            latest_user_text = m.content
                        elif m.role == "user" and len(history_user) < 3:
                            history_user.append(m.content)
                        if latest_user_text and len(history_user) >= 3:
                            break
                except Exception:
                    pass

                try:
                    _, owner_name = get_badge_and_owner(getattr(self, "device_id", "")) or ("", "")
                except Exception:
                    owner_name = ""
                # 读取最近两次完整对话的“会话级摘要”
                summaries = get_recent_chat_summaries(getattr(self, "device_id", ""), limit=2)
                # 将摘要放在“历史对话”区域（最多两条）
                items = build_dialog_chat_items(owner_name, "喵喵同学", latest_user_text or "", final_text, summaries)
                # 环形窗口：最多10行，超过则保留末尾10行（模拟“从第一行重新刷新”）
                max_lines = 10
                if len(items) > max_lines:
                    items = items[-max_lines:]
                payload_final = {
                    "type": "ui.render",
                    "id": f"dlg-final-{self.sentence_id or ''}",
                    "page": "dialog.chat",
                    "header": {},
                    "body": {"kind": "list", "items": items},
                    "footer": {"hint": build_chat_footer_hint()}
                }
                asyncio.run_coroutine_threadsafe(send_render(self, payload_final), self.loop)

                # 不在轮次内保存“历史对话”（仅在会话关闭时保存整体摘要）
            except Exception:
                pass
        if text_index > 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )

        return True

    def _handle_mcp_tool_call(self, function_call_data):
        function_arguments = function_call_data["arguments"]
        function_name = function_call_data["name"]
        try:
            args_dict = function_arguments
            if isinstance(function_arguments, str):
                try:
                    args_dict = json.loads(function_arguments)
                except json.JSONDecodeError:
                    self.logger.bind(tag=TAG).error(
                        f"无法解析 function_arguments: {function_arguments}"
                    )
                    return ActionResponse(
                        action=Action.REQLLM, result="参数解析失败", response=""
                    )

            tool_result = asyncio.run_coroutine_threadsafe(
                self.mcp_manager.execute_tool(function_name, args_dict), self.loop
            ).result()
            # meta=None content=[TextContent(type='text', text='北京当前天气:\n温度: 21°C\n天气: 晴\n湿度: 6%\n风向: 西北 风\n风力等级: 5级', annotations=None)] isError=False
            content_text = ""
            if tool_result is not None and tool_result.content is not None:
                for content in tool_result.content:
                    content_type = content.type
                    if content_type == "text":
                        content_text = content.text
                    elif content_type == "image":
                        pass

            if len(content_text) > 0:
                return ActionResponse(
                    action=Action.REQLLM, result=content_text, response=""
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
            return ActionResponse(
                action=Action.REQLLM, result="工具调用出错", response=""
            )

        return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")

    def _handle_function_result(self, result, function_call_data):
        if result.action == Action.RESPONSE:  # 直接回复前端
            text = result.response
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4()) if function_id is None else function_id
                        ),
                        content=text,
                    )
                )
                self.chat(text, tool_call=True)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.result
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """聊天记录上报工作线程"""
        while not self.stop_event.is_set():
            try:
                # 从队列获取数据，设置超时以便定期检查停止事件
                item = self.report_queue.get(timeout=1)
                if item is None:  # 检测毒丸对象
                    break
                type, text, audio_data, report_time = item
                try:
                    # 检查线程池状态
                    if self.executor is None:
                        continue
                    # 提交任务到线程池
                    self.executor.submit(
                        self._process_report, type, text, audio_data, report_time
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"聊天记录上报线程异常: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"聊天记录上报工作线程异常: {e}")

        self.logger.bind(tag=TAG).info("聊天记录上报线程已退出")

    def _process_report(self, type, text, audio_data, report_time):
        """处理上报任务"""
        try:
            # 执行上报（传入二进制数据）
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"上报处理异常: {e}")
        finally:
            # 标记任务完成
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"清除服务端讲话状态")

    async def close(self, ws=None):
        """资源清理方法"""
        try:
            # 在会话关闭前，生成一次本轮“完整对话摘要”，加入历史（仅在存在有效轮次时）
            try:
                latest_user = None
                latest_assistant = None
                for m in reversed(self.dialogue.dialogue if isinstance(self.dialogue, Dialogue) else []):
                    if m.role == "assistant" and latest_assistant is None:
                        latest_assistant = m.content
                    elif m.role == "user" and latest_user is None:
                        latest_user = m.content
                    if latest_user and latest_assistant:
                        break
                if latest_user or latest_assistant:
                    try:
                        _, owner_name = get_badge_and_owner(getattr(self, "device_id", "")) or ("", "")
                    except Exception:
                        owner_name = ""
                    summary_text = f"{owner_name or '用户'}: {latest_user or ''} / 喵喵同学: {latest_assistant or ''}"
                    append_chat_summary(getattr(self, "device_id", ""), summary_text, max_items=2)
            except Exception:
                pass
            # 取消超时任务
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None

            # 取消编码洞察定时任务
            try:
                if hasattr(self, "coding_insight_task") and self.coding_insight_task and not self.coding_insight_task.done():
                    self.coding_insight_task.cancel()
            except Exception:
                pass

            # 清理MCP资源
            if hasattr(self, "mcp_manager") and self.mcp_manager:
                await self.mcp_manager.cleanup_all()

            # 触发停止事件
            if self.stop_event:
                self.stop_event.set()

            # 清空任务队列
            self.clear_queues()

            # 关闭WebSocket连接
            if ws:
                await ws.close()
            elif self.websocket:
                await self.websocket.close()

            # 最后关闭线程池（避免阻塞）
            if self.executor:
                try:
                    # Python 3.9+ 支持 cancel_futures
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    self.executor.shutdown(wait=False)
                self.executor = None

            # 清理 LLM 实例缓存
            try:
                if hasattr(self, "_llm_cache") and isinstance(self._llm_cache, dict):
                    self._llm_cache.clear()
            except Exception:
                pass

            # 关闭 asr/tts/llm 资源
            try:
                if hasattr(self, "asr") and hasattr(self.asr, "close") and callable(getattr(self.asr, "close")):
                    maybe_close = self.asr.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "tts") and hasattr(self.tts, "close") and callable(getattr(self.tts, "close")):
                    maybe_close = self.tts.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "llm") and hasattr(self.llm, "close") and callable(getattr(self.llm, "close")):
                    maybe_close = self.llm.close()  # 供应商可选实现
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass

            self.logger.bind(tag=TAG).info("连接资源已释放")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")

    def clear_queues(self):
        """清空所有任务队列"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

            # 使用非阻塞方式清空队列
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"清理结束: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self):
        """重置VAD状态，恢复到idle状态"""
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.listen_state = "idle"
        if self._listen_state_timer:
            self._listen_state_timer.cancel()
            self._listen_state_timer = None
        self.logger.bind(tag=TAG).debug("VAD states reset.")
    
    async def send_json(self, data: dict) -> bool:
        """统一的 JSON 消息发送封装，包含错误处理
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.websocket:
            self.logger.bind(tag=TAG).warning("send_json: websocket is None")
            return False
        
        try:
            # 优先使用 send_json 方法
            if hasattr(self.websocket, 'send_json'):
                await self.websocket.send_json(data)
            else:
                # 回退到字符串发送
                await self.websocket.send(json.dumps(data, ensure_ascii=False))
            return True
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，静默处理（预期情况）
            self.logger.bind(tag=TAG).debug(f"send_json: connection closed for device {self.device_id}")
            return False
        except Exception as e:
            # 其他异常，记录警告但不中断
            self.logger.bind(tag=TAG).warning(f"send_json failed for device {self.device_id}: {e}")
            return False
    
    async def send_text(self, text: str) -> bool:
        """统一的文本消息发送封装
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.websocket:
            self.logger.bind(tag=TAG).warning("send_text: websocket is None")
            return False
        
        try:
            await self.websocket.send(text)
            return True
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，静默处理
            self.logger.bind(tag=TAG).debug(f"send_text: connection closed for device {self.device_id}")
            return False
        except Exception as e:
            # 其他异常，记录警告
            self.logger.bind(tag=TAG).warning(f"send_text failed for device {self.device_id}: {e}")
            return False
    
    async def transition_listen_state(self, new_state: str):
        """状态机转换：idle -> listening -> finalizing -> idle"""
        old_state = self.listen_state
        if old_state == "idle" and new_state == "listening":
            self.listen_state = "listening"
            self._last_listen_event_ms = int(time.time() * 1000)
            self.logger.bind(tag=TAG).debug("Listen state: idle -> listening")
        elif old_state == "listening" and new_state == "finalizing":
            self.listen_state = "finalizing"
            self.logger.bind(tag=TAG).debug("Listen state: listening -> finalizing")
            # 触发一次handle_voice_stop
            if len(self.asr_audio) > 0:
                from core.handle.receiveAudioHandle import handleAudioMessage
                await handleAudioMessage(self, b"")
        elif old_state == "finalizing" and new_state == "idle":
            self.listen_state = "idle"
            self.logger.bind(tag=TAG).debug("Listen state: finalizing -> idle")
            self.reset_vad_states()
    
    def check_vad_fallback(self):
        """检查是否需要VAD兜底（超过fallback_ms未见设备边界）"""
        if self.listen_state != "listening":
            return False
        if self.client_listen_mode != "manual":
            return False
        now_ms = int(time.time() * 1000)
        fallback_ms = 2000  # 默认2秒
        try:
            base_cfg = self._get_base_config()
            meeting_cfg = base_cfg.get("meeting", {})
            fallback_ms = int(meeting_cfg.get("vad_fallback_ms", 2000))
        except Exception:
            pass
        last_event_ms = getattr(self, "_last_listen_event_ms", 0)
        if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
            self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
            return True
        return False

    async def send_text(self, text: str) -> None:
        """统一文本发送包装。"""
        try:
            if self.websocket:
                await self.websocket.send(text)
        except Exception:
            pass

    async def send_json(self, payload: dict) -> None:
        """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
        try:
            if self.websocket is None:
                return
            try:
                await self.websocket.send_json(payload)
            except AttributeError:
                import json as _json
                await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
        except Exception:
            # 发送错误不应中断主流程
            pass

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """检查连接超时"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.timeout_seconds)
                if not self.stop_event.is_set():
                    # 在关闭前先发送提示并提供缓冲期（与无声层策略一致）
                    try:
                        await self.websocket.send(json.dumps({
                            "type": "system",
                            "event": "timeout_warning",
                            "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
                        }))
                    except Exception:
                        pass
                    # 给予 10 秒缓冲，若期间收到任何消息，reset_timeout 会取消下一轮关闭
                    try:
                        await asyncio.sleep(10)
                    except Exception:
                        pass
                    if self.stop_event.is_set():
                        break
                    self.logger.bind(tag=TAG).info("连接超时，准备关闭")
                    await self.close(self.websocket)
                    break
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")

```

- 文本换行与分行
  - 现在按“显示宽度”将每条对话拆分为多行，行行带前缀：
    - 例：用户太长 → 多行 “彭先生: …”
    - 助手太长 → 多行 “喵喵同学: …”
  - 不再用省略号截断助手回复，改为多行显示。

- 行数控制与滚动
  - 列表总行数上限改为 10 行；超过则保留末尾 10 行，相当于“从第一行重新刷新”。
  - 历史区仍占用剩余行数，若不够会被自然挤出。

- 实现位置
  - `core/orchestration/dialog_ui.py`：
    - 新增 `wrap_label_text(label, text)` 按宽度分行。
    - `build_dialog_chat_items()` 使用多行拼接。
  - `core/connection.py`：
    - 发送前裁剪到 10 行，保证硬件列表固定窗口。

---

**User**

好的,现在自动换行勉强达到要求了,但是屏幕上还没有完全输出,就已经“长时间未说话,退出聆听了”, 这个未聆听的逻辑应该等到大模型输出,全部显示完后,才开始计15秒的时



---

**Cursor**

```python
from core.handle.sendAudioHandle import send_stt_message
from core.handle.intentHandler import handle_user_intent
from core.utils.output_counter import check_device_output_limit
from core.handle.abortHandle import handleAbortMessage
import time
import asyncio
from core.handle.sendAudioHandle import SentenceType
from core.utils.util import audio_to_data
from core.handle.meeting_handle import finalize_meeting_and_send_summary, handle_meeting_message, stop_meeting_timers
import json
from core.orchestration.render_sender import send_render, send_control

TAG = __name__


async def handleAudioMessage(conn, audio):
    # finalize 阶段直接停止新的片段判断与注入，避免会后仍在持续会中推送
    if getattr(conn, "meeting_finalizing", False) or getattr(conn, "meeting_finalized", False):
        return
    # 当前片段是否有人说话
    have_voice = conn.vad.is_vad(conn, audio)
    # 如果设备刚刚被唤醒，短暂忽略VAD检测
    if have_voice and hasattr(conn, "just_woken_up") and conn.just_woken_up:
        have_voice = False
        # 设置一个短暂延迟后恢复VAD检测
        conn.asr_audio.clear()
        if not hasattr(conn, "vad_resume_task") or conn.vad_resume_task.done():
            conn.vad_resume_task = asyncio.create_task(resume_vad_detection(conn))
        return

    if have_voice:
        if conn.client_is_speaking:
            await handleAbortMessage(conn)
    # 设备长时间空闲检测，用于say goodbye
    await no_voice_close_connect(conn, have_voice)
    # 接收音频
    await conn.asr.receive_audio(conn, audio, have_voice)


async def resume_vad_detection(conn):
    # 等待2秒后恢复VAD检测
    await asyncio.sleep(1)
    conn.just_woken_up = False


async def startToChat(conn, text):
    if conn.need_bind:
        await check_bind_device(conn)
        return

    # 如果当日的输出字数大于限定的字数
    if conn.max_output_size > 0:
        if check_device_output_limit(
            conn.headers.get("device-id"), conn.max_output_size
        ):
            await max_out_size(conn)
            return
    if conn.client_is_speaking:
        await handleAbortMessage(conn)

    # 在会议模式下，语音输入仅用于转写，不进入对话流程
    if conn.current_mode == "meeting":
        # 在会议模式下优先处理“结束会议”类语音口令 → 直接触发 finalize
        try:
            normalized = str(text or "").strip().lower()
            finalize_keywords = [
                "结束会议", "停止录制", "开始总结", "出个纪要", "生成纪要", "结束一下会议", "结束本次会议",
                "finalize meeting", "stop recording", "start summary", "make a summary", "generate minutes"
            ]
            if any(kw.lower() in normalized for kw in finalize_keywords):
                try:
                    await conn.websocket.send(json.dumps({"type": "meeting", "phase": "finalize"}, ensure_ascii=False))
                except Exception:
                    pass
                try:
                    setattr(conn, "meeting_finalizing", True)
                except Exception:
                    pass
                try:
                    stop_meeting_timers(conn)
                except Exception:
                    pass
                asyncio.create_task(finalize_meeting_and_send_summary(conn))
                return
        except Exception:
            pass
        # 读取 meeting 配置
        try:
            srv = getattr(conn, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            if isinstance(base_cfg, dict):
                meeting_cfg = base_cfg.get("meeting", {})
            else:
                meeting_cfg = getattr(conn, "config", {}).get("meeting", {})
        except Exception:
            meeting_cfg = getattr(conn, "config", {}).get("meeting", {})
        
        disable_chat_on_snippet = bool(meeting_cfg.get("disable_chat_on_snippet", True))
        disable_tts = bool(meeting_cfg.get("disable_tts", True))

        # 注入 meeting.snippet
        try:
            await handle_meeting_message(
                conn,
                {
                    "type": "meeting",
                    "phase": "snippet",
                    "items": [{
                        "tag": "ASR",
                        "text": str(text),
                        "speakerId": str(getattr(conn, "device_id", "S1"))[:8]
                    }],
                },
            )
        except Exception:
            pass

        # 可选：发送一次 STT 文本用于前端占位（禁用 TTS 时不发送）
        if not disable_tts:
            await send_stt_message(conn, text)

        # 会议模式默认不触发 LLM 对话
        if disable_chat_on_snippet:
            return
    # 工作模式：在常规 STT 也支持直达口令（刷新/认领/完成 + 可选序号）
    try:
        if getattr(conn, "current_mode", None) == "working":
            normalized = str(text or "").strip().lower()
            # 同义词扩充（工作/任务均可）
            assign_kw   = ["认领任务","领取任务","我来做","assign to me","claim task","接收","接受","接手","接单","接收工作","接受工作","接手工作"]
            complete_kw = ["完成任务","标记完成","做完了","mark done","complete task","搞定了","已完成","完成工作","办完工作"]
            refresh_kw  = ["刷新列表","刷新任务","拉取任务","refresh","update list","pull","更新列表"]
            # 解析序号：第N个/第N条/任务一/工作一/数字/英文序数/task N
            def parse_ordinal(s: str) -> int:
                import re
                s = str(s).lower()
                zh = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
                m = re.search(r"(第)?([一二三四五六七八九十]|\d+)(个|条|项|号)?", s)
                if m:
                    g = m.group(2)
                    try:
                        return zh.get(g, int(g))
                    except Exception:
                        return 0
                m2 = re.search(r"task\s*(\d+)", s)
                if m2:
                    return int(m2.group(1))
                eng = {"first":1,"second":2,"third":3}
                for k,v in eng.items():
                    if k in s:
                        return v
                return 0
            intent = None
            if any(k in normalized for k in refresh_kw):
                intent = "refresh"
            elif any(k in normalized for k in assign_kw):
                intent = "assign"
            elif any(k in normalized for k in complete_kw):
                intent = "complete"
            if intent:
                from core.utils.tasks_store import get_task_store
                from core.handle.workflow_handle import handle_workflow_message
                store = get_task_store()
                group_key = (getattr(conn, "device_id", "") or "")[:8]
                if intent == "refresh":
                    tasks = store.list_by_group(group_key)
                    envelope = {"type":"workflow","event":"update","tasks":tasks}
                    try:
                        await conn.websocket.send_json(envelope)
                    except AttributeError:
                        await conn.websocket.send(json.dumps(envelope, ensure_ascii=False))
                    return
                tasks = store.list_by_group(group_key) or []
                target_id = None
                open_tasks = [t for t in tasks if t.get("status") == "open"]
                n = parse_ordinal(normalized)
                if n > 0 and n <= len(open_tasks):
                    target_id = open_tasks[n-1].get("id")
                else:
                    if intent == "assign":
                        for t in open_tasks:
                            if not t.get("owner") or t.get("owner") != getattr(conn, "device_id", None):
                                target_id = t.get("id"); break
                        if not target_id and tasks:
                            target_id = tasks[0].get("id")
                    elif intent == "complete":
                        target_id = open_tasks[0].get("id") if open_tasks else None
                if target_id:
                    if intent == "assign":
                        await handle_workflow_message(conn, {"type":"workflow","event":"assign","id":target_id})
                    else:
                        await handle_workflow_message(conn, {"type":"workflow","event":"complete","ids":[target_id]})
                    return
    except Exception:
        pass
    # 非会议模式或允许触发对话：先进行意图分析
    intent_handled = await handle_user_intent(conn, text)
    if intent_handled:
        return

    # 常规聊天流程
    await send_stt_message(conn, text)
    conn.executor.submit(conn.chat, text)


async def no_voice_close_connect(conn, have_voice):
    # 若TTS仍在播放或队列未清空，则不计入“无语音”超时
    try:
        if hasattr(conn, "tts") and hasattr(conn.tts, "tts_audio_queue"):
            if not conn.tts.tts_audio_queue.empty():
                conn.client_no_voice_last_time = 0.0
                return
        # 也可根据服务端讲话状态阻断计时
        if getattr(conn, "client_is_speaking", False):
            conn.client_no_voice_last_time = 0.0
            return
    except Exception:
        pass

    if have_voice:
        conn.client_no_voice_last_time = 0.0
        try:
            if hasattr(conn, "idle_close_warning_sent") and conn.idle_close_warning_sent:
                conn.idle_close_warning_sent = False
                conn.idle_close_warning_at_ms = 0
        except Exception:
            pass
        return
    if conn.client_no_voice_last_time == 0.0:
        conn.client_no_voice_last_time = time.time() * 1000
    else:
        no_voice_time = time.time() * 1000 - conn.client_no_voice_last_time
        # 对话态（dialog.active）无语音超时：默认15s自动退出聆听，回到 idle
        try:
            if getattr(conn, "current_mode", "") == "dialog.active":
                dialog_idle_timeout_ms = int(getattr(conn, "config", {}).get("dialog_idle_timeout_ms", 15000))
                if no_voice_time >= dialog_idle_timeout_ms:
                    try:
                        await send_control(conn, action="play.tone", name="cancel")
                    except Exception:
                        pass
                    try:
                        await send_render(conn, {
                            "type": "ui.render",
                            "id": "dlg-timeout",
                            "page": "dialog.chat",
                            "header": {},
                            "body": {"kind": "text", "text": "长时间未说话，已退出聆听。"},
                            "footer": {"hint": "说\"开始聊天\"再次进入"}
                        })
                    except Exception:
                        pass
                    try:
                        conn.current_mode = "connected.idle"
                        conn.client_have_voice = False
                        conn.client_voice_stop = False
                        if hasattr(conn, "asr_audio") and isinstance(conn.asr_audio, list):
                            conn.asr_audio.clear()
                        conn.client_no_voice_last_time = 0.0
                    except Exception:
                        pass
                    return
        except Exception:
            pass
        # 读取服务器/连接配置，默认 600s；会议/工作模式下阈值放大
        try:
            srv = getattr(conn, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            base = base_cfg if isinstance(base_cfg, dict) else getattr(conn, "config", {})
        except Exception:
            base = getattr(conn, "config", {})

        default_idle_sec = 600
        try:
            close_connection_no_voice_time = int(base.get("close_connection_no_voice_time", default_idle_sec))
        except Exception:
            close_connection_no_voice_time = default_idle_sec

        try:
            if getattr(conn, "current_mode", None) in ("meeting", "working"):
                close_connection_no_voice_time *= 3
        except Exception:
            pass

        # 关闭前预警与缓冲（默认 15s，可配置 5..30）
        try:
            grace_seconds = int(base.get("idle_close_grace_seconds", 15))
            grace_seconds = 5 if grace_seconds < 5 else grace_seconds
            grace_seconds = 30 if grace_seconds > 30 else grace_seconds
        except Exception:
            grace_seconds = 15

        # 即将达阈值前发送一次预警（仅一次）
        try:
            warn_threshold_ms = 1000 * max(0, close_connection_no_voice_time - grace_seconds)
            if no_voice_time >= warn_threshold_ms:
                if not getattr(conn, "idle_close_warning_sent", False):
                    try:
                        await send_stt_message(conn, "即将结束对话，如需继续请说话或发送任意消息…")
                    except Exception:
                        pass
                    try:
                        conn.idle_close_warning_sent = True
                        conn.idle_close_warning_at_ms = time.time() * 1000
                    except Exception:
                        pass
        except Exception:
            pass

        if (
            not conn.close_after_chat
            and no_voice_time > 1000 * close_connection_no_voice_time
        ):
            conn.close_after_chat = True
            conn.client_abort = False
            end_prompt = getattr(conn, "config", {}).get("end_prompt", {})
            if end_prompt and end_prompt.get("enable", True) is False:
                conn.logger.bind(tag=TAG).info("结束对话，无需发送结束提示语")
                await conn.close()
                return
            prompt = end_prompt.get("prompt")
            if not prompt:
                prompt = "本次对话即将结束，如需继续请随时再次与我交谈。"
            await startToChat(conn, prompt)


async def max_out_size(conn):
    text = "不好意思，我现在有点事情要忙，明天这个时候我们再聊，约好了哦！明天不见不散，拜拜！"
    await send_stt_message(conn, text)
    file_path = "config/assets/max_output_size.wav"
    opus_packets, _ = audio_to_data(file_path)
    conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
    conn.close_after_chat = True


async def check_bind_device(conn):
    if conn.bind_code:
        # 确保bind_code是6位数字
        if len(conn.bind_code) != 6:
            conn.logger.bind(tag=TAG).error(f"无效的绑定码格式: {conn.bind_code}")
            text = "绑定码格式错误，请检查配置。"
            await send_stt_message(conn, text)
            return

        text = f"请登录控制面板，输入{conn.bind_code}，绑定设备。"
        await send_stt_message(conn, text)

        # 播放提示音
        music_path = "config/assets/bind_code.wav"
        opus_packets, _ = audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.FIRST, opus_packets, text))

        # 逐个播放数字
        for i in range(6):  # 确保只播放6位数字
            try:
                digit = conn.bind_code[i]
                num_path = f"config/assets/bind_code/{digit}.wav"
                num_packets, _ = audio_to_data(num_path)
                conn.tts.tts_audio_queue.put((SentenceType.MIDDLE, num_packets, None))
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"播放数字音频失败: {e}")
                continue
        conn.tts.tts_audio_queue.put((SentenceType.LAST, [], None))
    else:
        text = f"没有找到该设备的版本信息，请正确配置 OTA地址，然后重新编译固件。"
        await send_stt_message(conn, text)
        music_path = "config/assets/bind_not_found.wav"
        opus_packets, _ = audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))

```

```python
*** Begin Patch
*** Update File: backend/core/providers/tts/base.py
@@
     def tts_text_priority_thread(self):
         while not self.conn.stop_event.is_set():
             try:
                 message = self.tts_text_queue.get(timeout=1)
                 if self.conn.client_abort:
                     logger.bind(tag=TAG).info("收到打断信息，终止TTS文本处理线程")
                     continue
                 if message.sentence_type == SentenceType.FIRST:
                     # 初始化参数
                     self.tts_stop_request = False
                     self.processed_chars = 0
                     self.tts_text_buff = []
                     self.is_first_sentence = True
                     self.tts_audio_first_sentence = True
+                    try:
+                        # 开始播报：标记服务端正在讲话，暂停无语音超时
+                        self.conn.client_is_speaking = True
+                    except Exception:
+                        pass
                 elif ContentType.TEXT == message.content_type:
@@
             except queue.Empty:
                 continue
             except Exception as e:
                 logger.bind(tag=TAG).error(f"TTS文本处理线程异常: {e}")
                 continue
@@
     def _audio_play_priority_thread(self):
         while not self.conn.stop_event.is_set():
             try:
                 message = self.tts_audio_queue.get(timeout=1)
                 if self.conn.client_abort:
                     logger.bind(tag=TAG).info("收到打断信息，终止音频播放线程")
                     continue
                 if message[0] == SentenceType.FIRST:
                     self.playing = True
                 elif message[0] == SentenceType.LAST:
                     self.playing = False
+                    try:
+                        # 播放完毕：清除讲话状态，允许无语音计时重新开始
+                        self.conn.clearSpeakStatus()
+                    except Exception:
+                        pass
                 self._tts_audio_play(message)
             except queue.Empty:
                 continue
             except Exception as e:
                 logger.bind(tag=TAG).error(f"音频播放线程异常: {e}")
*** End Patch
```

```python
import os
import re
import queue
import uuid
import asyncio
import threading
from core.utils import p3
from datetime import datetime
from core.utils import textUtils
from abc import ABC, abstractmethod
from config.logger import setup_logging
from core.utils.util import audio_to_data, audio_bytes_to_data
from core.utils.tts import MarkdownCleaner
from core.utils.output_counter import add_device_output
from core.handle.reportHandle import enqueue_tts_report
from core.handle.sendAudioHandle import sendAudioMessage
from core.providers.tts.dto.dto import (
    TTSMessageDTO,
    SentenceType,
    ContentType,
    InterfaceType,
)

import traceback

TAG = __name__
logger = setup_logging()


class TTSProviderBase(ABC):
    def __init__(self, config, delete_audio_file):
        self.interface_type = InterfaceType.NON_STREAM
        self.conn = None
        self.tts_timeout = 10
        self.delete_audio_file = delete_audio_file
        self.audio_file_type = "wav"
        self.output_file = config.get("output_dir", "tmp/")
        self.tts_text_queue = queue.Queue()
        self.tts_audio_queue = queue.Queue()
        self.tts_audio_first_sentence = True
        self.before_stop_play_files = []

        self.tts_text_buff = []
        self.punctuations = (
            "。",
            ".",
            "？",
            "?",
            "！",
            "!",
            "；",
            ";",
            "：",
        )
        self.first_sentence_punctuations = (
            "，",
            "～",
            "~",
            "、",
            ",",
            "。",
            ".",
            "？",
            "?",
            "！",
            "!",
            "；",
            ";",
            "：",
        )
        self.tts_stop_request = False
        self.processed_chars = 0
        self.is_first_sentence = True

    def generate_filename(self, extension=".wav"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    def to_tts(self, text):
        text = MarkdownCleaner.clean_markdown(text)
        max_repeat_time = 5
        if self.delete_audio_file:
            # 需要删除文件的直接转为音频数据
            while max_repeat_time > 0:
                try:
                    audio_bytes = asyncio.run(self.text_to_speak(text, None))
                    if audio_bytes:
                        audio_datas, _ = audio_bytes_to_data(
                            audio_bytes, file_type=self.audio_file_type, is_opus=True
                        )
                        return audio_datas
                    else:
                        max_repeat_time -= 1
                except Exception as e:
                    logger.bind(tag=TAG).warning(
                        f"语音生成失败{5 - max_repeat_time + 1}次: {text}，错误: {e}"
                    )
                    max_repeat_time -= 1
            if max_repeat_time > 0:
                logger.bind(tag=TAG).info(
                    f"语音生成成功: {text}，重试{5 - max_repeat_time}次"
                )
            else:
                logger.bind(tag=TAG).error(
                    f"语音生成失败: {text}，请检查网络或服务是否正常"
                )
            return None
        else:
            tmp_file = self.generate_filename()
            try:
                while not os.path.exists(tmp_file) and max_repeat_time > 0:
                    try:
                        asyncio.run(self.text_to_speak(text, tmp_file))
                    except Exception as e:
                        logger.bind(tag=TAG).warning(
                            f"语音生成失败{5 - max_repeat_time + 1}次: {text}，错误: {e}"
                        )
                        # 未执行成功，删除文件
                        if os.path.exists(tmp_file):
                            os.remove(tmp_file)
                        max_repeat_time -= 1

                if max_repeat_time > 0:
                    logger.bind(tag=TAG).info(
                        f"语音生成成功: {text}:{tmp_file}，重试{5 - max_repeat_time}次"
                    )
                else:
                    logger.bind(tag=TAG).error(
                        f"语音生成失败: {text}，请检查网络或服务是否正常"
                    )

                return tmp_file
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to generate TTS file: {e}")
                return None

    @abstractmethod
    async def text_to_speak(self, text, output_file):
        pass

    def audio_to_pcm_data(self, audio_file_path):
        """音频文件转换为PCM编码"""
        return audio_to_data(audio_file_path, is_opus=False)

    def audio_to_opus_data(self, audio_file_path):
        """音频文件转换为Opus编码"""
        return audio_to_data(audio_file_path, is_opus=True)

    def tts_one_sentence(
        self,
        conn,
        content_type,
        content_detail=None,
        content_file=None,
        sentence_id=None,
    ):
        """发送一句话"""
        if not sentence_id:
            if conn.sentence_id:
                sentence_id = conn.sentence_id
            else:
                sentence_id = str(uuid.uuid4()).replace("-", "")
                conn.sentence_id = sentence_id
        self.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id=sentence_id,
                sentence_type=SentenceType.FIRST,
                content_type=ContentType.ACTION,
            )
        )
        # 对于单句的文本，进行分段处理
        segments = re.split(r'([。！？!?；;\n])', content_detail)
        for seg in segments:
            self.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=sentence_id,
                    sentence_type=SentenceType.MIDDLE,
                    content_type=content_type,
                    content_detail=seg,
                    content_file=content_file,
                )
            )
        self.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id=sentence_id,
                sentence_type=SentenceType.LAST,
                content_type=ContentType.ACTION,
            )
        )

    async def open_audio_channels(self, conn):
        self.conn = conn
        self.tts_timeout = conn.config.get("tts_timeout", 10)
        # tts 消化线程
        self.tts_priority_thread = threading.Thread(
            target=self.tts_text_priority_thread, daemon=True
        )
        self.tts_priority_thread.start()

        # 音频播放 消化线程
        self.audio_play_priority_thread = threading.Thread(
            target=self._audio_play_priority_thread, daemon=True
        )
        self.audio_play_priority_thread.start()

    # 这里默认是非流式的处理方式
    # 流式处理方式请在子类中重写
    def tts_text_priority_thread(self):
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("收到打断信息，终止TTS文本处理线程")
                    continue
                if message.sentence_type == SentenceType.FIRST:
                    # 初始化参数
                    self.tts_stop_request = False
                    self.processed_chars = 0
                    self.tts_text_buff = []
                    self.is_first_sentence = True
                    self.tts_audio_first_sentence = True
                    try:
                        # 开播：置服务端讲话状态，暂停无语音计时
                        self.conn.client_is_speaking = True
                    except Exception:
                        pass
                elif ContentType.TEXT == message.content_type:
                    self.tts_text_buff.append(message.content_detail)
                    segment_text = self._get_segment_text()
                    if segment_text:
                        if self.delete_audio_file:
                            audio_datas = self.to_tts(segment_text)
                            if audio_datas:
                                self.tts_audio_queue.put(
                                    (message.sentence_type, audio_datas, segment_text)
                                )
                        else:
                            tts_file = self.to_tts(segment_text)
                            if tts_file:
                                audio_datas = self._process_audio_file(tts_file)
                                self.tts_audio_queue.put(
                                    (message.sentence_type, audio_datas, segment_text)
                                )
                elif ContentType.FILE == message.content_type:
                    self._process_remaining_text()
                    tts_file = message.content_file
                    if tts_file and os.path.exists(tts_file):
                        audio_datas = self._process_audio_file(tts_file)
                        self.tts_audio_queue.put(
                            (message.sentence_type, audio_datas, message.content_detail)
                        )

                if message.sentence_type == SentenceType.LAST:
                    self._process_remaining_text()
                    self.tts_audio_queue.put(
                        (message.sentence_type, [], message.content_detail)
                    )

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(f"处理TTS文本失败: {str(e)}")
                continue

    def _audio_play_priority_thread(self):
        while not self.conn.stop_event.is_set():
            text = None
            try:
                try:
                    sentence_type, audio_datas, text = self.tts_audio_queue.get(
                        timeout=1
                    )
                except queue.Empty:
                    if self.conn.stop_event.is_set():
                        break
                    continue
                future = asyncio.run_coroutine_threadsafe(
                    sendAudioMessage(self.conn, sentence_type, audio_datas, text),
                    self.conn.loop,
                )
                future.result()
                if self.conn.max_output_size > 0 and text:
                    add_device_output(self.conn.headers.get("device-id"), len(text))
                enqueue_tts_report(self.conn, text, audio_datas)
                if sentence_type == SentenceType.LAST:
                    try:
                        # 播放完毕，恢复无语音计时
                        self.conn.clearSpeakStatus()
                    except Exception:
                        pass
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"audio_play_priority priority_thread: {text} {e}"
                )

    async def start_session(self, session_id):
        pass

    async def finish_session(self, session_id):
        pass

    async def close(self):
        """资源清理方法"""
        if hasattr(self, "ws") and self.ws:
            await self.ws.close()

    def _get_segment_text(self):
        # 合并当前全部文本并处理未分割部分
        full_text = "".join(self.tts_text_buff)
        current_text = full_text[self.processed_chars :]  # 从未处理的位置开始
        last_punct_pos = -1

        # 根据是否是第一句话选择不同的标点符号集合
        punctuations_to_use = (
            self.first_sentence_punctuations
            if self.is_first_sentence
            else self.punctuations
        )

        for punct in punctuations_to_use:
            pos = current_text.rfind(punct)
            if (pos != -1 and last_punct_pos == -1) or (
                pos != -1 and pos < last_punct_pos
            ):
                last_punct_pos = pos

        if last_punct_pos != -1:
            segment_text_raw = current_text[: last_punct_pos + 1]
            segment_text = textUtils.get_string_no_punctuation_or_emoji(
                segment_text_raw
            )
            self.processed_chars += len(segment_text_raw)  # 更新已处理字符位置

            # 如果是第一句话，在找到第一个逗号后，将标志设置为False
            if self.is_first_sentence:
                self.is_first_sentence = False

            return segment_text
        elif self.tts_stop_request and current_text:
            segment_text = current_text
            self.is_first_sentence = True  # 重置标志
            return segment_text
        else:
            return None

    def _process_audio_file(self, tts_file):
        """处理音频文件并转换为指定格式

        Args:
            tts_file: 音频文件路径
            content_detail: 内容详情

        Returns:
            tuple: (sentence_type, audio_datas, content_detail)
        """
        audio_datas = []
        if tts_file.endswith(".p3"):
            audio_datas, _ = p3.decode_opus_from_file(tts_file)
        elif self.conn.audio_format == "pcm":
            audio_datas, _ = self.audio_to_pcm_data(tts_file)
        else:
            audio_datas, _ = self.audio_to_opus_data(tts_file)

        if (
            self.delete_audio_file
            and tts_file is not None
            and os.path.exists(tts_file)
            and tts_file.startswith(self.output_file)
        ):
            os.remove(tts_file)
        return audio_datas

    def _process_before_stop_play_files(self):
        for tts_file, text in self.before_stop_play_files:
            if tts_file and os.path.exists(tts_file):
                audio_datas = self._process_audio_file(tts_file)
                self.tts_audio_queue.put((SentenceType.MIDDLE, audio_datas, text))
        self.before_stop_play_files.clear()
        self.tts_audio_queue.put((SentenceType.LAST, [], None))

    def _process_remaining_text(self):
        """处理剩余的文本并生成语音

        Returns:
            bool: 是否成功处理了文本
        """
        full_text = "".join(self.tts_text_buff)
        remaining_text = full_text[self.processed_chars :]
        if remaining_text:
            segment_text = textUtils.get_string_no_punctuation_or_emoji(remaining_text)
            if segment_text:
                if self.delete_audio_file:
                    audio_datas = self.to_tts(segment_text)
                    if audio_datas:
                        self.tts_audio_queue.put(
                            (SentenceType.MIDDLE, audio_datas, segment_text)
                        )
                else:
                    tts_file = self.to_tts(segment_text)
                    audio_datas = self._process_audio_file(tts_file)
                    self.tts_audio_queue.put(
                        (SentenceType.MIDDLE, audio_datas, segment_text)
                    )
                self.processed_chars += len(full_text)
                return True
        return False

```

- 我已把“无语音超时”的计时改为在大模型播报完成后才开始：
  - TTS开始播报时：在 `tts_text_priority_thread` 设置 `conn.client_is_speaking=True`。
  - TTS播放完成（收到 LAST 帧）时：在 `_audio_play_priority_thread` 调用 `conn.clearSpeakStatus()` 恢复为 False。
  - `no_voice_close_connect` 中新增判断：若 `client_is_speaking=True` 或 `tts_audio_queue` 非空，则不累计无语音时间，直接重置计时。

- 效果
  - 屏幕未完全输出（TTS与渲染还在进行）时不会触发“长时间未说话，退出聆听”。播报结束后才开始15秒静默计时。

---

**User**

现在还是不太对劲,首先过长的吐词,会让屏幕刷新直接卡住,没显示完所有东西;

比如关于天气的播报,就会卡在第六行的“未来7天” 然后剩下的内容,硬件上是看不见的,屏幕也没刷新,这是错误的逻辑!





---

**Cursor**

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional
import unicodedata
from copy import deepcopy
from config.logger import setup_logging
from core.utils.device_registry import get_display_title


_logger = setup_logging()


def _norm_str(v: Any) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v)
        s = s.strip()
        return s if len(s) > 0 else None
    except Exception:
        return None


def _ensure_list_of_str(items: Any, limit: int = 8) -> Optional[List[str]]:
    if not isinstance(items, list):
        return None
    out: List[str] = []
    for it in items:
        s = _norm_str(it)
        if s is None:
            continue
        out.append(s)
        if len(out) >= limit:
            break
    return out


def _normalize_device_id(v: Optional[str]) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v).strip().strip('"').strip("'")
        return s.lower() if s else None
    except Exception:
        return None
def _char_display_width(ch: str) -> int:
    # 中日韩全角/宽字符按2，其他按1
    try:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            return 2
        return 1
    except Exception:
        return 1


def _truncate_to_width(s: str, max_units: int = 40) -> str:
    """按显示宽度截断至 max_units。单位：ASCII≈1，CJK≈2。

    估算：300px 宽，中文约16px 字号 → 一行≈18汉字；英文≈36字符。取40显示单位更保守。
    """
    if not s:
        return ""
    total = 0
    out_chars: List[str] = []
    for ch in s:
        w = _char_display_width(ch)
        if total + w > max_units:
            out_chars.append("…")
            break
        out_chars.append(ch)
        total += w
    return "".join(out_chars)


def _wrap_text_to_width(text: str, max_units_per_line: int = 40) -> str:
    """将长文本按显示宽度软换行，便于旧固件以单个 text 渲染时不溢出。"""
    if not text:
        return ""
    lines: List[str] = []
    current = []
    total = 0
    for ch in text:
        if ch == "\n":
            lines.append("".join(current))
            current, total = [], 0
            continue
        w = _char_display_width(ch)
        if total + w > max_units_per_line:
            lines.append("".join(current))
            current, total = [ch], w
        else:
            current.append(ch)
            total += w
    if current:
        lines.append("".join(current))
    return "\n".join(lines)



def clean_render_payload(device_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """轻量清洗渲染负载。仅允许 body.kind: text|list，并注入设备标题。

    - 强制保留字段：type=ui.render, page, header.title, body, footer.hint, id?
    - body: { kind: text, text } 或 { kind: list, items<=8 }
    - 其它未知字段忽略
    - 注入 header.title：若设备已注册 -> "工牌{badge} · {owner}"；未注册 -> 不注入，仅日志
    """
    if not isinstance(payload, dict):
        try:
            _logger.info("[DROP_INVALID] type=ui.render reason=payload-not-dict device=%s" % device_id)
        except Exception:
            pass
        return None

    device_id_norm = _normalize_device_id(device_id)
    if device_id_norm is None:
        try:
            _logger.info("[DROP_INVALID] type=ui.render reason=device-id-missing")
        except Exception:
            pass
        return None

    typ = _norm_str(payload.get("type")) or "ui.render"
    if typ != "ui.render":
        try:
            _logger.info(f"[DROP_INVALID] type={typ} reason=type-mismatch expected=ui.render device={device_id_norm}")
        except Exception:
            pass
        return None

    page = _norm_str(payload.get("page"))
    if page is None:
        try:
            _logger.info(f"[DROP_INVALID] type=ui.render reason=schema-invalid missing=page device={device_id_norm}")
        except Exception:
            pass
        return None

    header_in = payload.get("header") or {}
    body_in = payload.get("body") or {}
    footer_in = payload.get("footer") or {}

    body_kind = _norm_str(body_in.get("kind"))
    cleaned_body: Optional[Dict[str, Any]] = None
    if body_kind == "text":
        text = _norm_str(body_in.get("text")) or ""
        text = _wrap_text_to_width(text)
        cleaned_body = {"kind": "text", "text": text}
    elif body_kind == "list":
        # 对话页支持最多10行，匹配硬件窗口
        items = _ensure_list_of_str(body_in.get("items"), limit=10) or []
        items = [_truncate_to_width(it) for it in items]
        cleaned_body = {"kind": "list", "items": items}
    else:
        # 不支持的 body，直接返回 None
        try:
            _logger.info(f"[DROP_INVALID] type=ui.render reason=unsupported-body-kind kind={body_kind} device={device_id_norm}")
        except Exception:
            pass
        return None

    # 注入标题策略：dialog.chat 标题为“对话模式”（设备端负责加左上角 C1 标识）；其他页面按设备标题注入
    if page == "dialog.chat":
        title = "对话模式"
    else:
        injected_title = get_display_title(device_id_norm)
        if injected_title is None:
            try:
                _logger.info(f"未注册设备，不注入标题 device={device_id_norm}")
            except Exception:
                pass
            title = _norm_str(header_in.get("title")) or ""
        else:
            title = injected_title

    cleaned: Dict[str, Any] = {
        "type": "ui.render",
        "page": page,
        "header": {"title": title},
        "body": cleaned_body,
    }

    # 透传 footer.hint 与 footer.page（若可解析）
    hint = _norm_str(footer_in.get("hint"))
    page_obj = footer_in.get("page") or {}
    try:
        page_index = int(page_obj.get("index"))
        page_total = int(page_obj.get("total"))
        if page_index >= 1 and page_total >= 1:
            footer_page = {"index": page_index, "total": page_total}
        else:
            footer_page = None
    except Exception:
        footer_page = None

    footer_out = {}
    if hint is not None:
        footer_out["hint"] = hint
    if footer_page is not None:
        footer_out["page"] = footer_page
    if len(footer_out) > 0:
        cleaned["footer"] = footer_out

    # 保留 id（幂等/ACK 关联）
    if payload.get("id") is not None:
        cleaned["id"] = str(payload.get("id"))

    return cleaned



```

```python
import os
import sys
import copy
import json
import uuid
import time
import queue
import asyncio
import threading
import traceback
from config.logger import truncate_for_log
import subprocess
import websockets
from core.handle.mcpHandle import call_mcp_tool
from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
)
from typing import Dict, Any
from core.mcp.manager import MCPManager
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.handle.functionHandler import FunctionHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, update_module_string
from config.manage_api_client import DeviceNotFoundException, DeviceBindException
from core.orchestration.render_sender import send_render
from core.orchestration.dialog_ui import build_dialog_chat_items, build_chat_footer_hint
from core.utils.device_registry import get_badge_and_owner
from core.orchestration.history_store import append_chat_summary, get_recent_chat_summaries
from core.utils.dialogue import Dialogue


TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # 保存server实例的引用

        self.auth = AuthMiddleware(config)
        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.client_ip_info = {}
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"

        # 客户端状态相关
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"
        # 监听状态机：idle -> listening -> finalizing -> idle
        self.listen_state = "idle"
        self._listen_state_timer = None
        self._last_listen_event_ms = 0

        # 线程任务相关
        self.loop = asyncio.get_event_loop()
        self.stop_event = threading.Event()
        # 缩减线程池，降低上下文切换与内存占用
        try:
            meeting_cfg = self.config.get("meeting", {}) if isinstance(self.config, dict) else {}
            # 固化 W3：线程池默认 2，可被 meeting.threadpool_max_workers 覆盖
            default_workers = 2
            max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
            if max_workers < 1:
                max_workers = default_workers
        except Exception:
            max_workers = 2
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 添加上报线程池
        self.report_queue = queue.Queue()
        self.report_thread = None
        # 未来可以通过修改此处，调节asr的上报和tts的上报，目前默认都开启
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # 依赖的组件
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_no_voice_last_time = 0.0
        self.client_voice_stop = False
        self.client_voice_frame_count = 0

        # asr相关变量
        # 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
        # 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()

        # llm相关变量
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # tts相关变量
        self.sentence_id = None

        # iot相关变量
        self.iot_descriptors = {}
        self.func_handler = None

        # 模式状态（meeting/coding/working/dialog）
        # 阶段2默认进入 connected.idle，欢迎页不允许渲染
        self.current_mode = "connected.idle"
        # 会议模式相关缓存
        self.meeting_segments = []  # [{"ts": int(ms), "text": str}]
        self.meeting_start_ts = 0.0
        self.meeting_last_snippet_ts = 0.0
        self.meeting_last_snippet_index = 0
        # 会议片段节流与幂等状态
        self.meeting_recent_texts = {}
        self.meeting_pending_texts = []
        self.meeting_last_emit_ms = 0.0
        self.meeting_finalized = False
        # 编码模式日志流运行标志/阶段名（用于 stop/clear/phase 扩展）
        self.coding_stream_running = False
        self.coding_phase_name = ""

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        # 是否在聊天结束后关闭连接
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_task = None
        # 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
        try:
            base_idle = int(self.config.get("close_connection_no_voice_time", 600))
        except Exception:
            base_idle = 600
        self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭

        # {"mcp":true} 表示启用MCP功能
        self.features = None

        # LLM 按模式实例缓存（随连接释放）
        self._llm_cache = {}

    def _get_base_config(self) -> Dict[str, Any]:
        try:
            srv = getattr(self, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            if isinstance(base_cfg, dict):
                return base_cfg
        except Exception:
            pass
        return self.config if isinstance(self.config, dict) else {}

    def get_llm_for(self, purpose: str):
        """按用途/模式返回 LLM 实例，懒加载并缓存。

        purpose 可取："chat" | "meeting" | "coding" | "working" | "intent" | "memory"
        """
        try:
            key = str(purpose or "chat").lower()
        except Exception:
            key = "chat"

        # 缓存命中
        if key in self._llm_cache and self._llm_cache[key] is not None:
            return self._llm_cache[key]

        base_cfg = self._get_base_config()
        # 读取映射
        mapping = {}
        try:
            mapping = base_cfg.get("llm_by_mode", {}) or {}
        except Exception:
            mapping = {}

        mapping_val = mapping.get(key, None)
        if mapping_val is None:
            # 用途未配置专用 LLM，回退 default 并记录告警
            try:
                self.logger.bind(tag=TAG).warning(
                    f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
                )
            except Exception:
                pass
            mapping_val = mapping.get("default")

        alias = None
        overrides = None
        if isinstance(mapping_val, dict):
            # 支持 { alias: xxx, overrides: { model_name: '...' } } 或直接平铺覆盖字段
            alias = mapping_val.get("alias") or mapping_val.get("name") or mapping_val.get("module") or mapping_val.get("llm")
            overrides = mapping_val.get("overrides")
            if overrides is None:
                # 将除别名键外的其余键视为覆盖
                tmp = dict(mapping_val)
                for k in ["alias", "name", "module", "llm", "overrides"]:
                    tmp.pop(k, None)
                overrides = tmp if len(tmp) > 0 else None
        elif isinstance(mapping_val, str) and len(mapping_val) > 0:
            alias = mapping_val

        # 回退默认 alias
        try:
            if alias is None:
                alias = self.config["selected_module"]["LLM"]
        except Exception:
            alias = None

        # 若无覆盖且别名等于当前默认，直接复用
        try:
            current_default_alias = self.config["selected_module"]["LLM"]
            if (overrides is None or len(overrides) == 0) and alias == current_default_alias and getattr(self, "llm", None) is not None:
                self._llm_cache[key] = self.llm
                return self.llm
        except Exception:
            pass

        # 统一委托 server 级共享工厂；失败回退默认 LLM
        try:
            srv = getattr(self, "server", None)
            if srv and hasattr(srv, "get_or_create_llm") and callable(getattr(srv, "get_or_create_llm")) and alias:
                instance = srv.get_or_create_llm(alias, overrides)
                if instance is not None:
                    self._llm_cache[key] = instance
                    return instance
            # 回退默认
            self._llm_cache[key] = self.llm
            return self.llm
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
            self._llm_cache[key] = self.llm
            return self.llm

    async def handle_connection(self, ws, path=None):
        try:
            # 获取并验证headers（兼容 websockets 库的属性命名）
            try:
                raw_headers = getattr(ws, "request_headers", {})
                # 统一小写键，便于后续从 headers 获取 authorization/device-id
                headers_lower = {}
                try:
                    # 优先使用 items() 以兼容 websockets 的 Headers 类型
                    for k, v in raw_headers.items():
                        headers_lower[str(k).lower()] = v
                except Exception:
                    try:
                        headers_lower = {str(k).lower(): v for k, v in dict(raw_headers).items()}
                    except Exception:
                        headers_lower = {}
                self.headers = headers_lower
            except Exception:
                self.headers = {}

            # 统一调用服务器封装的握手解析；其次尝试 Header；最后回退自动分配
            device_id_from_query = None
            client_id_from_query = None
            raw_path_from_server = None
            try:
                server_obj = getattr(self, "server", None)
                if server_obj and hasattr(server_obj, "parse_ids_from_handshake"):
                    d, c, rawp = server_obj.parse_ids_from_handshake(ws, path)
                    device_id_from_query = d
                    client_id_from_query = c
                    raw_path_from_server = rawp
            except Exception:
                pass

            # 从 Header 兜底解析（包含非规范写法）
            def _normalize_id(v):
                try:
                    if v is None:
                        return None
                    vv = str(v).strip().strip('"').strip("'")
                    return vv.lower() if vv else None
                except Exception:
                    return None
            header_device_id = _normalize_id(
                self.headers.get("device-id")
                or self.headers.get("device_id")
                or self.headers.get("x-device-id")
                or self.headers.get("x-device_id")
            )
            header_client_id = _normalize_id(
                self.headers.get("client-id")
                or self.headers.get("client_id")
                or self.headers.get("x-client-id")
                or self.headers.get("x-client_id")
            )

            # 赋值优先级：Query > Header > 回退
            chosen_device_id = device_id_from_query or header_device_id or header_client_id
            chosen_client_id = client_id_from_query or header_client_id or chosen_device_id

            if chosen_device_id:
                self.headers["device-id"] = chosen_device_id
                if chosen_client_id:
                    self.headers["client-id"] = chosen_client_id
                # 打印来源与解析快照（包含原始 path 片段便于定位异常客户端）
                try:
                    raw_paths_snapshot = []
                    if isinstance(raw_path_from_server, str) and raw_path_from_server:
                        raw_paths_snapshot.append(raw_path_from_server[:256])
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                        for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                            val = getattr(ws, attr, "")
                            if isinstance(val, str) and val:
                                raw_paths_snapshot.append(val[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    src = "query" if device_id_from_query else "header"
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={src}, rawPaths={truncate_for_log(str(raw_paths_snapshot))})"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={'query' if device_id_from_query else 'header'})"
                    )
            else:
                # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
                auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
                self.headers["device-id"] = auto_device_id
                self.headers["client-id"] = auto_device_id
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    header_keys = list(self.headers.keys())
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; rawPaths={truncate_for_log(str(raw_paths_snapshot))}, headerKeys={truncate_for_log(str(header_keys))}"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
                    )
            # 获取客户端ip地址
            try:
                remote = getattr(ws, "remote_address", None)
                if isinstance(remote, tuple) and len(remote) >= 1:
                    self.client_ip = remote[0]
                else:
                    self.client_ip = str(remote) if remote is not None else ""
            except Exception:
                self.client_ip = ""
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # 进行认证
            await self.auth.authenticate(self.headers)

            # 认证通过,继续处理
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)
            # 在 server 上注册设备路由（自动断开旧连接）
            if self.server and self.device_id:
                ok = await self.server.register_device_handler(self.device_id, self)
                if ok is False:
                    self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
                    await ws.send("设备注册失败")
                    await self.close(ws)
                    return

            # 启动超时检查任务
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.websocket.send(json.dumps(self.welcome_msg))

            # 获取差异化配置
            self._initialize_private_config()
            # 异步初始化
            self.executor.submit(self._initialize_components)

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            try:
                safe_e = truncate_for_log(str(e))
                safe_tb = truncate_for_log(stack_trace)
            except Exception:
                safe_e = str(e)
                safe_tb = stack_trace
            self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
            return
        finally:
            try:
                # 注销设备路由映射
                if self.server and self.device_id:
                    await self.server.unregister_device_handler(self.device_id, self)
            finally:
                await self._save_and_close(ws)

    async def _save_and_close(self, ws):
        """保存记忆并关闭连接"""
        try:
            if self.memory:
                # 使用线程池异步保存记忆
                def save_memory_task():
                    try:
                        # 创建新事件循环（避免与主循环冲突）
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            self.memory.save_memory(self.dialogue.dialogue)
                        )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
                    finally:
                        loop.close()

                # 启动线程保存记忆，不等待完成
                threading.Thread(target=save_memory_task, daemon=True).start()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
        finally:
            # 立即关闭连接，不等待记忆保存完成
            await self.close(ws)

    def reset_timeout(self):
        """重置超时计时器"""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._check_timeout())

    async def _route_message(self, message):
        """消息路由"""
        # 重置超时计时器
        self.reset_timeout()

        if isinstance(message, str):
            # 轻量 ping/keepalive：收到后仅重置计时器并忽略
            try:
                import json as _json
                try:
                    obj = _json.loads(message)
                except Exception:
                    obj = None
                if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
                    try:
                        # 可选：立即回 pong
                        await self.websocket.send(_json.dumps({"type": "pong"}))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None:
                return
            if self.asr is None:
                return
            self.asr_audio_queue.put(message)

    async def handle_restart(self, message):
        """处理服务器重启请求"""
        try:

            self.logger.bind(tag=TAG).info("收到服务器重启指令，准备执行...")

            # 发送确认响应
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "服务器重启中...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # 异步执行重启操作
            def restart_server():
                """实际执行重启的方法"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("执行服务器重启...")
                # 后台重启：避免继承TTY，全部重定向，保证 nohup/backgroud 模式不被SIGTTIN挂起
                with open(os.devnull, "rb", buffering=0) as devnull_in, \
                     open(os.devnull, "ab", buffering=0) as devnull_out, \
                     open(os.devnull, "ab", buffering=0) as devnull_err:
                    subprocess.Popen(
                        [sys.executable, "app.py"],
                        stdin=devnull_in,
                        stdout=devnull_out,
                        stderr=devnull_err,
                        start_new_session=True,
                        close_fds=True,
                    )
                os._exit(0)

            # 使用线程执行重启避免阻塞事件循环
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"重启失败: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            update_module_string(self.selected_module_str)
            """初始化组件"""
            if self.config.get("prompt") is not None:
                self.prompt = self.config["prompt"]
                self.change_system_prompt(self.prompt)
                self.logger.bind(tag=TAG).info(
                    f"初始化组件: prompt成功 {self.prompt[:50]}..."
                )

            """初始化本地组件"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()
            # 打开语音识别通道
            asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)

            if self.tts is None:
                self.tts = self._initialize_tts()
            # 会议模式可禁用 TTS 通道（懒启动）
            disable_tts = False
            try:
                srv = getattr(self, "server", None)
                base_cfg = getattr(srv, "config", None) if srv else None
                if isinstance(base_cfg, dict):
                    meeting_cfg2 = base_cfg.get("meeting", {})
                else:
                    meeting_cfg2 = self.config.get("meeting", {})
                disable_tts = bool(meeting_cfg2.get("disable_tts", False))
            except Exception:
                disable_tts = False
            if not disable_tts:
                asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)

            """加载记忆"""
            self._initialize_memory()
            """加载意图识别"""
            self._initialize_intent()
            """初始化上报线程"""
            self._init_report_threads()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"实例化组件失败: {e}")

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程已启动")

    def _initialize_tts(self):
        """初始化TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

    def _initialize_asr(self):
        """初始化ASR"""
        if self._asr.interface_type == InterfaceType.LOCAL:
            # 如果公共ASR是本地服务，则直接返回
            # 因为本地一个实例ASR，可以被多个连接共享
            asr = self._asr
        else:
            # 如果公共ASR是远程服务，则初始化一个新实例
            # 因为远程ASR，涉及到websocket连接和接收线程，需要每个连接一个实例
            asr = initialize_asr(self.config)

        return asr

    def _initialize_private_config(self):
        """如果是从配置文件获取，则进行二次实例化"""
        if not self.read_config_from_api:
            return
        """从接口获取差异化的配置进行二次实例化，非全量重新实例化"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} 秒，获取差异化配置成功: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get("selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # 加载插件配置
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                self.config["plugins"] = plugin_from_server
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = plugin_from_server.keys()
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """初始化记忆模块"""
        # 按模式选择记忆总结 LLM（可被 llm_by_mode.memory 覆盖）
        chosen_llm = self.llm
        try:
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                selected = self.get_llm_for("memory")
                if selected is not None:
                    chosen_llm = selected
        except Exception:
            pass

        self.memory.init_memory(
            role_id=self.device_id,
            llm=chosen_llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # 获取记忆总结配置
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # 如果使用 nomen，直接返回
        if memory_type == "nomem":
            return
        # 使用 mem_local_short 模式
        elif memory_type == "mem_local_short":
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get("type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为记忆总结创建了专用LLM: {memory_llm_name}, 类型: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # 否则使用主LLM
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """初始化意图识别模块"""
        # 获取意图识别配置
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # 如果使用 nointent，直接返回
        if intent_type == "nointent":
            return
        # 使用 intent_llm 模式
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为意图识别创建了专用LLM: {intent_llm_name}, 类型: {intent_llm_type}"
                )
                # 按模式选择意图识别 LLM（可被 llm_by_mode.intent 覆盖）
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(intent_llm)
                    else:
                        self.intent.set_llm(intent_llm)
                except Exception:
                    self.intent.set_llm(intent_llm)
            else:
                # 否则使用主LLM
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(self.llm)
                    else:
                        self.intent.set_llm(self.llm)
                except Exception:
                    self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """加载插件"""
        self.func_handler = FunctionHandler(self)
        self.mcp_manager = MCPManager(self)

        """加载MCP工具"""
        asyncio.run_coroutine_threadsafe(
            self.mcp_manager.initialize_servers(), self.loop
        )

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # 更新系统prompt至上下文
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, tool_call=False):
        try:
            safe_query = truncate_for_log(query)
        except Exception:
            safe_query = query
        self.logger.bind(tag=TAG).info(f"大模型收到用户消息: {safe_query}")
        self.llm_finish_task = False
        # 阶段2：进入对话活跃态（不再下发额外占位渲染，避免 c1→p1 的瞬时切换）
        try:
            self.current_mode = "dialog.active"
        except Exception:
            pass

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        if hasattr(self, "mcp_client"):
            mcp_tools = self.mcp_client.get_available_tools()
            if mcp_tools is not None and len(mcp_tools) > 0:
                if functions is None:
                    functions = []
                functions.extend(mcp_tools)
        response_message = []

        try:
            # 使用带记忆的对话
            memory_str = None
            if self.memory is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            self.sentence_id = str(uuid.uuid4().hex)


            # 按当前模式选择 LLM（默认chat；coding/working 切换对应别名）
            purpose = self.current_mode or "chat"
            active_llm = self.llm
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                try:
                    active_llm = self.get_llm_for(purpose) or self.llm
                except Exception:
                    active_llm = self.llm

            if self.intent_type == "function_call" and functions is not None:
                # 使用支持functions的streaming接口
                llm_responses = active_llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                    functions=functions,
                )
            else:
                llm_responses = active_llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        text_index = 0
        self.client_abort = False
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    # print("content_arguments", content_arguments)
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response
            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    if text_index == 0:
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=self.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )
                    text_index += 1
        # 处理function call
        if tool_call_flag:
            bHasError = False
            if function_id is None:
                a = extract_json_from_string(content_arguments)
                if a is not None:
                    try:
                        content_arguments_json = json.loads(a)
                        function_name = content_arguments_json["name"]
                        function_arguments = json.dumps(
                            content_arguments_json["arguments"], ensure_ascii=False
                        )
                        function_id = str(uuid.uuid4().hex)
                    except Exception as e:
                        bHasError = True
                        response_message.append(a)
                else:
                    bHasError = True
                    response_message.append(content_arguments)
                if bHasError:
                    self.logger.bind(tag=TAG).error(
                        f"function call error: {content_arguments}"
                    )
            if not bHasError:
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # 处理Server端MCP工具调用
                if self.mcp_manager.is_mcp_tool(function_name):
                    result = self._handle_mcp_tool_call(function_call_data)
                elif hasattr(self, "mcp_client") and self.mcp_client.has_tool(
                    function_name
                ):
                    # 如果是小智端MCP工具调用
                    self.logger.bind(tag=TAG).debug(
                        f"调用小智端MCP工具: {function_name}, 参数: {function_arguments}"
                    )
                    try:
                        result = asyncio.run_coroutine_threadsafe(
                            call_mcp_tool(
                                self, self.mcp_client, function_name, function_arguments
                            ),
                            self.loop,
                        ).result()
                        self.logger.bind(tag=TAG).debug(f"MCP工具调用结果: {result}")

                        resultJson = None
                        if isinstance(result, str):
                            try:
                                resultJson = json.loads(result)
                            except Exception as e:
                                self.logger.bind(tag=TAG).error(
                                    f"解析MCP工具返回结果失败: {e}"
                                )

                        # 视觉大模型不经过二次LLM处理
                        if (
                            resultJson is not None
                            and isinstance(resultJson, dict)
                            and "action" in resultJson
                        ):
                            result = ActionResponse(
                                action=Action[resultJson["action"]],
                                result=None,
                                response=resultJson.get("response", ""),
                            )
                        else:
                            result = ActionResponse(
                                action=Action.REQLLM, result=result, response=""
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
                        result = ActionResponse(
                            action=Action.REQLLM, result="MCP工具调用失败", response=""
                        )
                else:
                    # 处理系统函数
                    result = self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    )
                self._handle_function_result(result, function_call_data)

        # 存储对话内容
        if len(response_message) > 0:
            self.dialogue.put(
                Message(role="assistant", content="".join(response_message))
            )
            # 将最终回答渲染为 list 视图，遵循 hardware-ui-design.md 对话页面
            try:
                final_text = "".join(response_message)
                # 提取最近一条用户内容与近几条历史用户文本
                latest_user_text = None
                history_user = []
                try:
                    for m in reversed(self.dialogue.dialogue):
                        if m.role == "user" and latest_user_text is None:
                            latest_user_text = m.content
                        elif m.role == "user" and len(history_user) < 3:
                            history_user.append(m.content)
                        if latest_user_text and len(history_user) >= 3:
                            break
                except Exception:
                    pass

                try:
                    _, owner_name = get_badge_and_owner(getattr(self, "device_id", "")) or ("", "")
                except Exception:
                    owner_name = ""
                # 读取最近两次完整对话的“会话级摘要”
                summaries = get_recent_chat_summaries(getattr(self, "device_id", ""), limit=2)
                # 将摘要放在“历史对话”区域（最多两条）
                items = build_dialog_chat_items(owner_name, "喵喵同学", latest_user_text or "", final_text, summaries)
                # 环形窗口：最多10行，超过则保留末尾10行，并以分批渲染避免一次性超大payload
                max_lines = 10
                if len(items) > max_lines:
                    items = items[-max_lines:]
                payload_final = {
                    "type": "ui.render",
                    "id": f"dlg-final-{self.sentence_id or ''}",
                    "page": "dialog.chat",
                    "header": {},
                    "body": {"kind": "list", "items": items},
                    "footer": {"hint": build_chat_footer_hint()}
                }
                # 分批渲染（若需要，可拓展为分段多帧发送）
                asyncio.run_coroutine_threadsafe(send_render(self, payload_final), self.loop)

                # 不在轮次内保存“历史对话”（仅在会话关闭时保存整体摘要）
            except Exception:
                pass
        if text_index > 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )

        return True

    def _handle_mcp_tool_call(self, function_call_data):
        function_arguments = function_call_data["arguments"]
        function_name = function_call_data["name"]
        try:
            args_dict = function_arguments
            if isinstance(function_arguments, str):
                try:
                    args_dict = json.loads(function_arguments)
                except json.JSONDecodeError:
                    self.logger.bind(tag=TAG).error(
                        f"无法解析 function_arguments: {function_arguments}"
                    )
                    return ActionResponse(
                        action=Action.REQLLM, result="参数解析失败", response=""
                    )

            tool_result = asyncio.run_coroutine_threadsafe(
                self.mcp_manager.execute_tool(function_name, args_dict), self.loop
            ).result()
            # meta=None content=[TextContent(type='text', text='北京当前天气:\n温度: 21°C\n天气: 晴\n湿度: 6%\n风向: 西北 风\n风力等级: 5级', annotations=None)] isError=False
            content_text = ""
            if tool_result is not None and tool_result.content is not None:
                for content in tool_result.content:
                    content_type = content.type
                    if content_type == "text":
                        content_text = content.text
                    elif content_type == "image":
                        pass

            if len(content_text) > 0:
                return ActionResponse(
                    action=Action.REQLLM, result=content_text, response=""
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
            return ActionResponse(
                action=Action.REQLLM, result="工具调用出错", response=""
            )

        return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")

    def _handle_function_result(self, result, function_call_data):
        if result.action == Action.RESPONSE:  # 直接回复前端
            text = result.response
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4()) if function_id is None else function_id
                        ),
                        content=text,
                    )
                )
                self.chat(text, tool_call=True)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.result
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """聊天记录上报工作线程"""
        while not self.stop_event.is_set():
            try:
                # 从队列获取数据，设置超时以便定期检查停止事件
                item = self.report_queue.get(timeout=1)
                if item is None:  # 检测毒丸对象
                    break
                type, text, audio_data, report_time = item
                try:
                    # 检查线程池状态
                    if self.executor is None:
                        continue
                    # 提交任务到线程池
                    self.executor.submit(
                        self._process_report, type, text, audio_data, report_time
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"聊天记录上报线程异常: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"聊天记录上报工作线程异常: {e}")

        self.logger.bind(tag=TAG).info("聊天记录上报线程已退出")

    def _process_report(self, type, text, audio_data, report_time):
        """处理上报任务"""
        try:
            # 执行上报（传入二进制数据）
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"上报处理异常: {e}")
        finally:
            # 标记任务完成
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"清除服务端讲话状态")

    async def close(self, ws=None):
        """资源清理方法"""
        try:
            # 在会话关闭前，生成一次本轮“完整对话摘要”，加入历史（仅在存在有效轮次时）
            try:
                latest_user = None
                latest_assistant = None
                for m in reversed(self.dialogue.dialogue if isinstance(self.dialogue, Dialogue) else []):
                    if m.role == "assistant" and latest_assistant is None:
                        latest_assistant = m.content
                    elif m.role == "user" and latest_user is None:
                        latest_user = m.content
                    if latest_user and latest_assistant:
                        break
                if latest_user or latest_assistant:
                    try:
                        _, owner_name = get_badge_and_owner(getattr(self, "device_id", "")) or ("", "")
                    except Exception:
                        owner_name = ""
                    summary_text = f"{owner_name or '用户'}: {latest_user or ''} / 喵喵同学: {latest_assistant or ''}"
                    append_chat_summary(getattr(self, "device_id", ""), summary_text, max_items=2)
            except Exception:
                pass
            # 取消超时任务
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None

            # 取消编码洞察定时任务
            try:
                if hasattr(self, "coding_insight_task") and self.coding_insight_task and not self.coding_insight_task.done():
                    self.coding_insight_task.cancel()
            except Exception:
                pass

            # 清理MCP资源
            if hasattr(self, "mcp_manager") and self.mcp_manager:
                await self.mcp_manager.cleanup_all()

            # 触发停止事件
            if self.stop_event:
                self.stop_event.set()

            # 清空任务队列
            self.clear_queues()

            # 关闭WebSocket连接
            if ws:
                await ws.close()
            elif self.websocket:
                await self.websocket.close()

            # 最后关闭线程池（避免阻塞）
            if self.executor:
                try:
                    # Python 3.9+ 支持 cancel_futures
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    self.executor.shutdown(wait=False)
                self.executor = None

            # 清理 LLM 实例缓存
            try:
                if hasattr(self, "_llm_cache") and isinstance(self._llm_cache, dict):
                    self._llm_cache.clear()
            except Exception:
                pass

            # 关闭 asr/tts/llm 资源
            try:
                if hasattr(self, "asr") and hasattr(self.asr, "close") and callable(getattr(self.asr, "close")):
                    maybe_close = self.asr.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "tts") and hasattr(self.tts, "close") and callable(getattr(self.tts, "close")):
                    maybe_close = self.tts.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "llm") and hasattr(self.llm, "close") and callable(getattr(self.llm, "close")):
                    maybe_close = self.llm.close()  # 供应商可选实现
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass

            self.logger.bind(tag=TAG).info("连接资源已释放")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")

    def clear_queues(self):
        """清空所有任务队列"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

            # 使用非阻塞方式清空队列
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"清理结束: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self):
        """重置VAD状态，恢复到idle状态"""
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.listen_state = "idle"
        if self._listen_state_timer:
            self._listen_state_timer.cancel()
            self._listen_state_timer = None
        self.logger.bind(tag=TAG).debug("VAD states reset.")
    
    async def send_json(self, data: dict) -> bool:
        """统一的 JSON 消息发送封装，包含错误处理
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.websocket:
            self.logger.bind(tag=TAG).warning("send_json: websocket is None")
            return False
        
        try:
            # 优先使用 send_json 方法
            if hasattr(self.websocket, 'send_json'):
                await self.websocket.send_json(data)
            else:
                # 回退到字符串发送
                await self.websocket.send(json.dumps(data, ensure_ascii=False))
            return True
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，静默处理（预期情况）
            self.logger.bind(tag=TAG).debug(f"send_json: connection closed for device {self.device_id}")
            return False
        except Exception as e:
            # 其他异常，记录警告但不中断
            self.logger.bind(tag=TAG).warning(f"send_json failed for device {self.device_id}: {e}")
            return False
    
    async def send_text(self, text: str) -> bool:
        """统一的文本消息发送封装
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.websocket:
            self.logger.bind(tag=TAG).warning("send_text: websocket is None")
            return False
        
        try:
            await self.websocket.send(text)
            return True
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，静默处理
            self.logger.bind(tag=TAG).debug(f"send_text: connection closed for device {self.device_id}")
            return False
        except Exception as e:
            # 其他异常，记录警告
            self.logger.bind(tag=TAG).warning(f"send_text failed for device {self.device_id}: {e}")
            return False
    
    async def transition_listen_state(self, new_state: str):
        """状态机转换：idle -> listening -> finalizing -> idle"""
        old_state = self.listen_state
        if old_state == "idle" and new_state == "listening":
            self.listen_state = "listening"
            self._last_listen_event_ms = int(time.time() * 1000)
            self.logger.bind(tag=TAG).debug("Listen state: idle -> listening")
        elif old_state == "listening" and new_state == "finalizing":
            self.listen_state = "finalizing"
            self.logger.bind(tag=TAG).debug("Listen state: listening -> finalizing")
            # 触发一次handle_voice_stop
            if len(self.asr_audio) > 0:
                from core.handle.receiveAudioHandle import handleAudioMessage
                await handleAudioMessage(self, b"")
        elif old_state == "finalizing" and new_state == "idle":
            self.listen_state = "idle"
            self.logger.bind(tag=TAG).debug("Listen state: finalizing -> idle")
            self.reset_vad_states()
    
    def check_vad_fallback(self):
        """检查是否需要VAD兜底（超过fallback_ms未见设备边界）"""
        if self.listen_state != "listening":
            return False
        if self.client_listen_mode != "manual":
            return False
        now_ms = int(time.time() * 1000)
        fallback_ms = 2000  # 默认2秒
        try:
            base_cfg = self._get_base_config()
            meeting_cfg = base_cfg.get("meeting", {})
            fallback_ms = int(meeting_cfg.get("vad_fallback_ms", 2000))
        except Exception:
            pass
        last_event_ms = getattr(self, "_last_listen_event_ms", 0)
        if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
            self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
            return True
        return False

    async def send_text(self, text: str) -> None:
        """统一文本发送包装。"""
        try:
            if self.websocket:
                await self.websocket.send(text)
        except Exception:
            pass

    async def send_json(self, payload: dict) -> None:
        """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
        try:
            if self.websocket is None:
                return
            try:
                await self.websocket.send_json(payload)
            except AttributeError:
                import json as _json
                await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
        except Exception:
            # 发送错误不应中断主流程
            pass

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """检查连接超时"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.timeout_seconds)
                if not self.stop_event.is_set():
                    # 在关闭前先发送提示并提供缓冲期（与无声层策略一致）
                    try:
                        await self.websocket.send(json.dumps({
                            "type": "system",
                            "event": "timeout_warning",
                            "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
                        }))
                    except Exception:
                        pass
                    # 给予 10 秒缓冲，若期间收到任何消息，reset_timeout 会取消下一轮关闭
                    try:
                        await asyncio.sleep(10)
                    except Exception:
                        pass
                    if self.stop_event.is_set():
                        break
                    self.logger.bind(tag=TAG).info("连接超时，准备关闭")
                    await self.close(self.websocket)
                    break
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")

```

- 我已避免在播放/渲染过程中触发“未说话超时”，但你反馈的“卡在第六行不再刷新”更像是单帧过大渲染导致硬件整屏阻塞。
- 现在的修正
  - 列表窗口固定最多10行；渲染清洗将 `list` 最多保留10项，防止单帧过长。
  - 按显示宽度把每条“用户/助手”文本拆成多行，再裁剪到10行窗口，保证能显示到末尾行。
  - 无语音计时在TTS期间暂停，播放结束后才开始15秒静默计时。

- 如还会卡住（极长回答）
  - 我可以把回答分段分页发送：将拆分后的行按每次5行两帧下发（间隔≥500ms，避开限流），实现“逐屏滚动”。如果你同意，我下一步把“分批渲染”打开，确保长回答稳定显示完毕。

---

**User**

问题1 极长的回答还是会卡住

把回答分段分页发送：将拆分后的行按每次5行两帧下发（间隔≥500ms，避开限流），实现“逐屏滚动”。把“分批渲染”打开，确保长回答稳定显示完毕。

问题2 希望对话页面的结构改成这样我不希望“> 正在对话中” “用户” “助手”  “> 历史对话”前面有小圆圈,前面留空即可,我只希望“ • <历史2>”前面有小圆圈,同时我希望“用户”和“助手”栏之间有0.5行的留空;




---

**Cursor**

```python
from __future__ import annotations

from typing import List, Optional
import unicodedata


def _truncate(text: Optional[str], limit: int = 28) -> str:
    try:
        if text is None:
            return ""
        s = str(text).replace("\n", " ").strip()
        if len(s) <= limit:
            return s
        return s[: limit - 1] + "…"
    except Exception:
        return str(text or "")


def build_dialog_chat_items(user_name: str, assistant_name: str, latest_user_text: str, latest_assistant_text: str, history_user_texts: List[str]) -> List[str]:
    """构造对话模式(list)渲染内容，遵循 hardware-ui-design.md 的页面示意。

    限制：最多 8 行。
结构：
	> 正在对话中：
    ─────────────
	文先生: <用户话>
	(中间空0.5行)
	喵喵同学: <助手话>
 	喵喵同学: <助手话>
 	喵喵同学: <助手话>
 	喵喵同学: <助手话>
 	喵喵同学: <助手话>

	> 历史对话：
    ─────────────
    • <历史1>
    • <历史2>
    """
    items: List[str] = []
    items.append(">对话中：")
    items.append("────────────────────────────────")
    user_display = user_name or "用户"
    assistant_display = assistant_name or "喵喵同学"
    if latest_user_text:
        items.extend(wrap_label_text(f"{user_display}: ", latest_user_text))
    # 中间留空0.5行：使用占位标记，在清洗阶段转为空白行
    items.append("<blank>")
    if latest_assistant_text:
        items.extend(wrap_label_text(f"{assistant_display}: ", latest_assistant_text))

    # 历史对话（取最近的2条用户提问作为列表项，避免超过8行）
    hist = [t for t in (history_user_texts or []) if t]
    if len(hist) > 0 and len(items) < 8:
        items.append("历史对话：")
        items.append("────────────────────────────────")
        for t in hist:
            if len(items) >= 8:
                break
            items.append(f"• {_truncate(t)}")

    # 限制最多8行
    return items[:8]


def build_chat_footer_hint() -> str:
    return "说：\"结束对话\" | \"查看历史对话\" | \"进入其他模式\""


def _char_display_width(ch: str) -> int:
    try:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            return 2
        return 1
    except Exception:
        return 1


def wrap_label_text(label: str, text: str, max_units_per_line: int = 40) -> List[str]:
    """按显示宽度将 label+text 拆分为多行。每行都带相同的 label。"""
    label = str(label or "")
    text = str(text or "")
    # 计算每行可用宽度（扣除label占用）
    label_units = sum(_char_display_width(c) for c in label)
    avail = max(8, max_units_per_line - label_units)  # 至少保留8单位，避免死循环

    lines: List[str] = []
    current: List[str] = []
    total = 0
    def flush():
        if current:
            lines.append(label + "".join(current))

    for ch in text:
        if ch == "\n":
            flush()
            current, total = [], 0
            continue
        w = _char_display_width(ch)
        if total + w > avail:
            flush()
            current, total = [ch], w
        else:
            current.append(ch)
            total += w
    flush()
    if not lines:
        lines.append(label)
    return lines



```

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional
import unicodedata
from copy import deepcopy
from config.logger import setup_logging
from core.utils.device_registry import get_display_title


_logger = setup_logging()


def _norm_str(v: Any) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v)
        s = s.strip()
        return s if len(s) > 0 else None
    except Exception:
        return None


def _ensure_list_of_str(items: Any, limit: int = 8) -> Optional[List[str]]:
    if not isinstance(items, list):
        return None
    out: List[str] = []
    for it in items:
        s = _norm_str(it)
        if s is None:
            continue
        out.append(s)
        if len(out) >= limit:
            break
    return out


def _normalize_device_id(v: Optional[str]) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v).strip().strip('"').strip("'")
        return s.lower() if s else None
    except Exception:
        return None
def _char_display_width(ch: str) -> int:
    # 中日韩全角/宽字符按2，其他按1
    try:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            return 2
        return 1
    except Exception:
        return 1


def _truncate_to_width(s: str, max_units: int = 40) -> str:
    """按显示宽度截断至 max_units。单位：ASCII≈1，CJK≈2。

    估算：300px 宽，中文约16px 字号 → 一行≈18汉字；英文≈36字符。取40显示单位更保守。
    """
    if not s:
        return ""
    total = 0
    out_chars: List[str] = []
    for ch in s:
        w = _char_display_width(ch)
        if total + w > max_units:
            out_chars.append("…")
            break
        out_chars.append(ch)
        total += w
    return "".join(out_chars)


def _wrap_text_to_width(text: str, max_units_per_line: int = 40) -> str:
    """将长文本按显示宽度软换行，便于旧固件以单个 text 渲染时不溢出。"""
    if not text:
        return ""
    lines: List[str] = []
    current = []
    total = 0
    for ch in text:
        if ch == "\n":
            lines.append("".join(current))
            current, total = [], 0
            continue
        w = _char_display_width(ch)
        if total + w > max_units_per_line:
            lines.append("".join(current))
            current, total = [ch], w
        else:
            current.append(ch)
            total += w
    if current:
        lines.append("".join(current))
    return "\n".join(lines)



def clean_render_payload(device_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """轻量清洗渲染负载。仅允许 body.kind: text|list，并注入设备标题。

    - 强制保留字段：type=ui.render, page, header.title, body, footer.hint, id?
    - body: { kind: text, text } 或 { kind: list, items<=8 }
    - 其它未知字段忽略
    - 注入 header.title：若设备已注册 -> "工牌{badge} · {owner}"；未注册 -> 不注入，仅日志
    """
    if not isinstance(payload, dict):
        try:
            _logger.info("[DROP_INVALID] type=ui.render reason=payload-not-dict device=%s" % device_id)
        except Exception:
            pass
        return None

    device_id_norm = _normalize_device_id(device_id)
    if device_id_norm is None:
        try:
            _logger.info("[DROP_INVALID] type=ui.render reason=device-id-missing")
        except Exception:
            pass
        return None

    typ = _norm_str(payload.get("type")) or "ui.render"
    if typ != "ui.render":
        try:
            _logger.info(f"[DROP_INVALID] type={typ} reason=type-mismatch expected=ui.render device={device_id_norm}")
        except Exception:
            pass
        return None

    page = _norm_str(payload.get("page"))
    if page is None:
        try:
            _logger.info(f"[DROP_INVALID] type=ui.render reason=schema-invalid missing=page device={device_id_norm}")
        except Exception:
            pass
        return None

    header_in = payload.get("header") or {}
    body_in = payload.get("body") or {}
    footer_in = payload.get("footer") or {}

    body_kind = _norm_str(body_in.get("kind"))
    cleaned_body: Optional[Dict[str, Any]] = None
    if body_kind == "text":
        text = _norm_str(body_in.get("text")) or ""
        text = _wrap_text_to_width(text)
        cleaned_body = {"kind": "text", "text": text}
    elif body_kind == "list":
        # 对话页支持最多10行，匹配硬件窗口
        items = _ensure_list_of_str(body_in.get("items"), limit=10) or []
        # 占位行 <blank> 渲染为空白行
        normalized_items: List[str] = []
        for it in items:
            if it == "<blank>":
                normalized_items.append("")
            else:
                normalized_items.append(_truncate_to_width(it))
        items = normalized_items
        cleaned_body = {"kind": "list", "items": items}
    else:
        # 不支持的 body，直接返回 None
        try:
            _logger.info(f"[DROP_INVALID] type=ui.render reason=unsupported-body-kind kind={body_kind} device={device_id_norm}")
        except Exception:
            pass
        return None

    # 注入标题策略：dialog.chat 标题为“对话模式”（设备端负责加左上角 C1 标识）；其他页面按设备标题注入
    if page == "dialog.chat":
        title = "对话模式"
    else:
        injected_title = get_display_title(device_id_norm)
        if injected_title is None:
            try:
                _logger.info(f"未注册设备，不注入标题 device={device_id_norm}")
            except Exception:
                pass
            title = _norm_str(header_in.get("title")) or ""
        else:
            title = injected_title

    cleaned: Dict[str, Any] = {
        "type": "ui.render",
        "page": page,
        "header": {"title": title},
        "body": cleaned_body,
    }

    # 透传 footer.hint 与 footer.page（若可解析）
    hint = _norm_str(footer_in.get("hint"))
    page_obj = footer_in.get("page") or {}
    try:
        page_index = int(page_obj.get("index"))
        page_total = int(page_obj.get("total"))
        if page_index >= 1 and page_total >= 1:
            footer_page = {"index": page_index, "total": page_total}
        else:
            footer_page = None
    except Exception:
        footer_page = None

    footer_out = {}
    if hint is not None:
        footer_out["hint"] = hint
    if footer_page is not None:
        footer_out["page"] = footer_page
    if len(footer_out) > 0:
        cleaned["footer"] = footer_out

    # 保留 id（幂等/ACK 关联）
    if payload.get("id") is not None:
        cleaned["id"] = str(payload.get("id"))

    return cleaned



```

```python
import os
import sys
import copy
import json
import uuid
import time
import queue
import asyncio
import threading
import traceback
from config.logger import truncate_for_log
import subprocess
import websockets
from core.handle.mcpHandle import call_mcp_tool
from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
)
from typing import Dict, Any
from core.mcp.manager import MCPManager
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.handle.functionHandler import FunctionHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, update_module_string
from config.manage_api_client import DeviceNotFoundException, DeviceBindException
from core.orchestration.render_sender import send_render
from core.orchestration.dialog_ui import build_dialog_chat_items, build_chat_footer_hint
from core.utils.device_registry import get_badge_and_owner
from core.orchestration.history_store import append_chat_summary, get_recent_chat_summaries
from core.utils.dialogue import Dialogue


TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # 保存server实例的引用

        self.auth = AuthMiddleware(config)
        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.client_ip_info = {}
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"

        # 客户端状态相关
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"
        # 监听状态机：idle -> listening -> finalizing -> idle
        self.listen_state = "idle"
        self._listen_state_timer = None
        self._last_listen_event_ms = 0

        # 线程任务相关
        self.loop = asyncio.get_event_loop()
        self.stop_event = threading.Event()
        # 缩减线程池，降低上下文切换与内存占用
        try:
            meeting_cfg = self.config.get("meeting", {}) if isinstance(self.config, dict) else {}
            # 固化 W3：线程池默认 2，可被 meeting.threadpool_max_workers 覆盖
            default_workers = 2
            max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
            if max_workers < 1:
                max_workers = default_workers
        except Exception:
            max_workers = 2
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 添加上报线程池
        self.report_queue = queue.Queue()
        self.report_thread = None
        # 未来可以通过修改此处，调节asr的上报和tts的上报，目前默认都开启
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # 依赖的组件
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_no_voice_last_time = 0.0
        self.client_voice_stop = False
        self.client_voice_frame_count = 0

        # asr相关变量
        # 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
        # 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()

        # llm相关变量
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # tts相关变量
        self.sentence_id = None

        # iot相关变量
        self.iot_descriptors = {}
        self.func_handler = None

        # 模式状态（meeting/coding/working/dialog）
        # 阶段2默认进入 connected.idle，欢迎页不允许渲染
        self.current_mode = "connected.idle"
        # 会议模式相关缓存
        self.meeting_segments = []  # [{"ts": int(ms), "text": str}]
        self.meeting_start_ts = 0.0
        self.meeting_last_snippet_ts = 0.0
        self.meeting_last_snippet_index = 0
        # 会议片段节流与幂等状态
        self.meeting_recent_texts = {}
        self.meeting_pending_texts = []
        self.meeting_last_emit_ms = 0.0
        self.meeting_finalized = False
        # 编码模式日志流运行标志/阶段名（用于 stop/clear/phase 扩展）
        self.coding_stream_running = False
        self.coding_phase_name = ""

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        # 是否在聊天结束后关闭连接
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_task = None
        # 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
        try:
            base_idle = int(self.config.get("close_connection_no_voice_time", 600))
        except Exception:
            base_idle = 600
        self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭

        # {"mcp":true} 表示启用MCP功能
        self.features = None

        # LLM 按模式实例缓存（随连接释放）
        self._llm_cache = {}

    def _get_base_config(self) -> Dict[str, Any]:
        try:
            srv = getattr(self, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            if isinstance(base_cfg, dict):
                return base_cfg
        except Exception:
            pass
        return self.config if isinstance(self.config, dict) else {}

    def get_llm_for(self, purpose: str):
        """按用途/模式返回 LLM 实例，懒加载并缓存。

        purpose 可取："chat" | "meeting" | "coding" | "working" | "intent" | "memory"
        """
        try:
            key = str(purpose or "chat").lower()
        except Exception:
            key = "chat"

        # 缓存命中
        if key in self._llm_cache and self._llm_cache[key] is not None:
            return self._llm_cache[key]

        base_cfg = self._get_base_config()
        # 读取映射
        mapping = {}
        try:
            mapping = base_cfg.get("llm_by_mode", {}) or {}
        except Exception:
            mapping = {}

        mapping_val = mapping.get(key, None)
        if mapping_val is None:
            # 用途未配置专用 LLM，回退 default 并记录告警
            try:
                self.logger.bind(tag=TAG).warning(
                    f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
                )
            except Exception:
                pass
            mapping_val = mapping.get("default")

        alias = None
        overrides = None
        if isinstance(mapping_val, dict):
            # 支持 { alias: xxx, overrides: { model_name: '...' } } 或直接平铺覆盖字段
            alias = mapping_val.get("alias") or mapping_val.get("name") or mapping_val.get("module") or mapping_val.get("llm")
            overrides = mapping_val.get("overrides")
            if overrides is None:
                # 将除别名键外的其余键视为覆盖
                tmp = dict(mapping_val)
                for k in ["alias", "name", "module", "llm", "overrides"]:
                    tmp.pop(k, None)
                overrides = tmp if len(tmp) > 0 else None
        elif isinstance(mapping_val, str) and len(mapping_val) > 0:
            alias = mapping_val

        # 回退默认 alias
        try:
            if alias is None:
                alias = self.config["selected_module"]["LLM"]
        except Exception:
            alias = None

        # 若无覆盖且别名等于当前默认，直接复用
        try:
            current_default_alias = self.config["selected_module"]["LLM"]
            if (overrides is None or len(overrides) == 0) and alias == current_default_alias and getattr(self, "llm", None) is not None:
                self._llm_cache[key] = self.llm
                return self.llm
        except Exception:
            pass

        # 统一委托 server 级共享工厂；失败回退默认 LLM
        try:
            srv = getattr(self, "server", None)
            if srv and hasattr(srv, "get_or_create_llm") and callable(getattr(srv, "get_or_create_llm")) and alias:
                instance = srv.get_or_create_llm(alias, overrides)
                if instance is not None:
                    self._llm_cache[key] = instance
                    return instance
            # 回退默认
            self._llm_cache[key] = self.llm
            return self.llm
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
            self._llm_cache[key] = self.llm
            return self.llm

    async def handle_connection(self, ws, path=None):
        try:
            # 获取并验证headers（兼容 websockets 库的属性命名）
            try:
                raw_headers = getattr(ws, "request_headers", {})
                # 统一小写键，便于后续从 headers 获取 authorization/device-id
                headers_lower = {}
                try:
                    # 优先使用 items() 以兼容 websockets 的 Headers 类型
                    for k, v in raw_headers.items():
                        headers_lower[str(k).lower()] = v
                except Exception:
                    try:
                        headers_lower = {str(k).lower(): v for k, v in dict(raw_headers).items()}
                    except Exception:
                        headers_lower = {}
                self.headers = headers_lower
            except Exception:
                self.headers = {}

            # 统一调用服务器封装的握手解析；其次尝试 Header；最后回退自动分配
            device_id_from_query = None
            client_id_from_query = None
            raw_path_from_server = None
            try:
                server_obj = getattr(self, "server", None)
                if server_obj and hasattr(server_obj, "parse_ids_from_handshake"):
                    d, c, rawp = server_obj.parse_ids_from_handshake(ws, path)
                    device_id_from_query = d
                    client_id_from_query = c
                    raw_path_from_server = rawp
            except Exception:
                pass

            # 从 Header 兜底解析（包含非规范写法）
            def _normalize_id(v):
                try:
                    if v is None:
                        return None
                    vv = str(v).strip().strip('"').strip("'")
                    return vv.lower() if vv else None
                except Exception:
                    return None
            header_device_id = _normalize_id(
                self.headers.get("device-id")
                or self.headers.get("device_id")
                or self.headers.get("x-device-id")
                or self.headers.get("x-device_id")
            )
            header_client_id = _normalize_id(
                self.headers.get("client-id")
                or self.headers.get("client_id")
                or self.headers.get("x-client-id")
                or self.headers.get("x-client_id")
            )

            # 赋值优先级：Query > Header > 回退
            chosen_device_id = device_id_from_query or header_device_id or header_client_id
            chosen_client_id = client_id_from_query or header_client_id or chosen_device_id

            if chosen_device_id:
                self.headers["device-id"] = chosen_device_id
                if chosen_client_id:
                    self.headers["client-id"] = chosen_client_id
                # 打印来源与解析快照（包含原始 path 片段便于定位异常客户端）
                try:
                    raw_paths_snapshot = []
                    if isinstance(raw_path_from_server, str) and raw_path_from_server:
                        raw_paths_snapshot.append(raw_path_from_server[:256])
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                        for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                            val = getattr(ws, attr, "")
                            if isinstance(val, str) and val:
                                raw_paths_snapshot.append(val[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    src = "query" if device_id_from_query else "header"
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={src}, rawPaths={truncate_for_log(str(raw_paths_snapshot))})"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={'query' if device_id_from_query else 'header'})"
                    )
            else:
                # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
                auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
                self.headers["device-id"] = auto_device_id
                self.headers["client-id"] = auto_device_id
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    header_keys = list(self.headers.keys())
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; rawPaths={truncate_for_log(str(raw_paths_snapshot))}, headerKeys={truncate_for_log(str(header_keys))}"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
                    )
            # 获取客户端ip地址
            try:
                remote = getattr(ws, "remote_address", None)
                if isinstance(remote, tuple) and len(remote) >= 1:
                    self.client_ip = remote[0]
                else:
                    self.client_ip = str(remote) if remote is not None else ""
            except Exception:
                self.client_ip = ""
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # 进行认证
            await self.auth.authenticate(self.headers)

            # 认证通过,继续处理
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)
            # 在 server 上注册设备路由（自动断开旧连接）
            if self.server and self.device_id:
                ok = await self.server.register_device_handler(self.device_id, self)
                if ok is False:
                    self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
                    await ws.send("设备注册失败")
                    await self.close(ws)
                    return

            # 启动超时检查任务
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.websocket.send(json.dumps(self.welcome_msg))

            # 获取差异化配置
            self._initialize_private_config()
            # 异步初始化
            self.executor.submit(self._initialize_components)

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            try:
                safe_e = truncate_for_log(str(e))
                safe_tb = truncate_for_log(stack_trace)
            except Exception:
                safe_e = str(e)
                safe_tb = stack_trace
            self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
            return
        finally:
            try:
                # 注销设备路由映射
                if self.server and self.device_id:
                    await self.server.unregister_device_handler(self.device_id, self)
            finally:
                await self._save_and_close(ws)

    async def _save_and_close(self, ws):
        """保存记忆并关闭连接"""
        try:
            if self.memory:
                # 使用线程池异步保存记忆
                def save_memory_task():
                    try:
                        # 创建新事件循环（避免与主循环冲突）
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            self.memory.save_memory(self.dialogue.dialogue)
                        )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
                    finally:
                        loop.close()

                # 启动线程保存记忆，不等待完成
                threading.Thread(target=save_memory_task, daemon=True).start()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
        finally:
            # 立即关闭连接，不等待记忆保存完成
            await self.close(ws)

    def reset_timeout(self):
        """重置超时计时器"""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._check_timeout())

    async def _route_message(self, message):
        """消息路由"""
        # 重置超时计时器
        self.reset_timeout()

        if isinstance(message, str):
            # 轻量 ping/keepalive：收到后仅重置计时器并忽略
            try:
                import json as _json
                try:
                    obj = _json.loads(message)
                except Exception:
                    obj = None
                if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
                    try:
                        # 可选：立即回 pong
                        await self.websocket.send(_json.dumps({"type": "pong"}))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None:
                return
            if self.asr is None:
                return
            self.asr_audio_queue.put(message)

    async def handle_restart(self, message):
        """处理服务器重启请求"""
        try:

            self.logger.bind(tag=TAG).info("收到服务器重启指令，准备执行...")

            # 发送确认响应
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "服务器重启中...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # 异步执行重启操作
            def restart_server():
                """实际执行重启的方法"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("执行服务器重启...")
                # 后台重启：避免继承TTY，全部重定向，保证 nohup/backgroud 模式不被SIGTTIN挂起
                with open(os.devnull, "rb", buffering=0) as devnull_in, \
                     open(os.devnull, "ab", buffering=0) as devnull_out, \
                     open(os.devnull, "ab", buffering=0) as devnull_err:
                    subprocess.Popen(
                        [sys.executable, "app.py"],
                        stdin=devnull_in,
                        stdout=devnull_out,
                        stderr=devnull_err,
                        start_new_session=True,
                        close_fds=True,
                    )
                os._exit(0)

            # 使用线程执行重启避免阻塞事件循环
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"重启失败: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            update_module_string(self.selected_module_str)
            """初始化组件"""
            if self.config.get("prompt") is not None:
                self.prompt = self.config["prompt"]
                self.change_system_prompt(self.prompt)
                self.logger.bind(tag=TAG).info(
                    f"初始化组件: prompt成功 {self.prompt[:50]}..."
                )

            """初始化本地组件"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()
            # 打开语音识别通道
            asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)

            if self.tts is None:
                self.tts = self._initialize_tts()
            # 会议模式可禁用 TTS 通道（懒启动）
            disable_tts = False
            try:
                srv = getattr(self, "server", None)
                base_cfg = getattr(srv, "config", None) if srv else None
                if isinstance(base_cfg, dict):
                    meeting_cfg2 = base_cfg.get("meeting", {})
                else:
                    meeting_cfg2 = self.config.get("meeting", {})
                disable_tts = bool(meeting_cfg2.get("disable_tts", False))
            except Exception:
                disable_tts = False
            if not disable_tts:
                asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)

            """加载记忆"""
            self._initialize_memory()
            """加载意图识别"""
            self._initialize_intent()
            """初始化上报线程"""
            self._init_report_threads()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"实例化组件失败: {e}")

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程已启动")

    def _initialize_tts(self):
        """初始化TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

    def _initialize_asr(self):
        """初始化ASR"""
        if self._asr.interface_type == InterfaceType.LOCAL:
            # 如果公共ASR是本地服务，则直接返回
            # 因为本地一个实例ASR，可以被多个连接共享
            asr = self._asr
        else:
            # 如果公共ASR是远程服务，则初始化一个新实例
            # 因为远程ASR，涉及到websocket连接和接收线程，需要每个连接一个实例
            asr = initialize_asr(self.config)

        return asr

    def _initialize_private_config(self):
        """如果是从配置文件获取，则进行二次实例化"""
        if not self.read_config_from_api:
            return
        """从接口获取差异化的配置进行二次实例化，非全量重新实例化"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} 秒，获取差异化配置成功: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get("selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # 加载插件配置
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                self.config["plugins"] = plugin_from_server
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = plugin_from_server.keys()
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """初始化记忆模块"""
        # 按模式选择记忆总结 LLM（可被 llm_by_mode.memory 覆盖）
        chosen_llm = self.llm
        try:
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                selected = self.get_llm_for("memory")
                if selected is not None:
                    chosen_llm = selected
        except Exception:
            pass

        self.memory.init_memory(
            role_id=self.device_id,
            llm=chosen_llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # 获取记忆总结配置
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # 如果使用 nomen，直接返回
        if memory_type == "nomem":
            return
        # 使用 mem_local_short 模式
        elif memory_type == "mem_local_short":
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get("type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为记忆总结创建了专用LLM: {memory_llm_name}, 类型: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # 否则使用主LLM
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """初始化意图识别模块"""
        # 获取意图识别配置
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # 如果使用 nointent，直接返回
        if intent_type == "nointent":
            return
        # 使用 intent_llm 模式
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为意图识别创建了专用LLM: {intent_llm_name}, 类型: {intent_llm_type}"
                )
                # 按模式选择意图识别 LLM（可被 llm_by_mode.intent 覆盖）
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(intent_llm)
                    else:
                        self.intent.set_llm(intent_llm)
                except Exception:
                    self.intent.set_llm(intent_llm)
            else:
                # 否则使用主LLM
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(self.llm)
                    else:
                        self.intent.set_llm(self.llm)
                except Exception:
                    self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """加载插件"""
        self.func_handler = FunctionHandler(self)
        self.mcp_manager = MCPManager(self)

        """加载MCP工具"""
        asyncio.run_coroutine_threadsafe(
            self.mcp_manager.initialize_servers(), self.loop
        )

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # 更新系统prompt至上下文
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, tool_call=False):
        try:
            safe_query = truncate_for_log(query)
        except Exception:
            safe_query = query
        self.logger.bind(tag=TAG).info(f"大模型收到用户消息: {safe_query}")
        self.llm_finish_task = False
        # 阶段2：进入对话活跃态（不再下发额外占位渲染，避免 c1→p1 的瞬时切换）
        try:
            self.current_mode = "dialog.active"
        except Exception:
            pass

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        if hasattr(self, "mcp_client"):
            mcp_tools = self.mcp_client.get_available_tools()
            if mcp_tools is not None and len(mcp_tools) > 0:
                if functions is None:
                    functions = []
                functions.extend(mcp_tools)
        response_message = []

        try:
            # 使用带记忆的对话
            memory_str = None
            if self.memory is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            self.sentence_id = str(uuid.uuid4().hex)


            # 按当前模式选择 LLM（默认chat；coding/working 切换对应别名）
            purpose = self.current_mode or "chat"
            active_llm = self.llm
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                try:
                    active_llm = self.get_llm_for(purpose) or self.llm
                except Exception:
                    active_llm = self.llm

            if self.intent_type == "function_call" and functions is not None:
                # 使用支持functions的streaming接口
                llm_responses = active_llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                    functions=functions,
                )
            else:
                llm_responses = active_llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        text_index = 0
        self.client_abort = False
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    # print("content_arguments", content_arguments)
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response
            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    if text_index == 0:
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=self.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )
                    text_index += 1
        # 处理function call
        if tool_call_flag:
            bHasError = False
            if function_id is None:
                a = extract_json_from_string(content_arguments)
                if a is not None:
                    try:
                        content_arguments_json = json.loads(a)
                        function_name = content_arguments_json["name"]
                        function_arguments = json.dumps(
                            content_arguments_json["arguments"], ensure_ascii=False
                        )
                        function_id = str(uuid.uuid4().hex)
                    except Exception as e:
                        bHasError = True
                        response_message.append(a)
                else:
                    bHasError = True
                    response_message.append(content_arguments)
                if bHasError:
                    self.logger.bind(tag=TAG).error(
                        f"function call error: {content_arguments}"
                    )
            if not bHasError:
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # 处理Server端MCP工具调用
                if self.mcp_manager.is_mcp_tool(function_name):
                    result = self._handle_mcp_tool_call(function_call_data)
                elif hasattr(self, "mcp_client") and self.mcp_client.has_tool(
                    function_name
                ):
                    # 如果是小智端MCP工具调用
                    self.logger.bind(tag=TAG).debug(
                        f"调用小智端MCP工具: {function_name}, 参数: {function_arguments}"
                    )
                    try:
                        result = asyncio.run_coroutine_threadsafe(
                            call_mcp_tool(
                                self, self.mcp_client, function_name, function_arguments
                            ),
                            self.loop,
                        ).result()
                        self.logger.bind(tag=TAG).debug(f"MCP工具调用结果: {result}")

                        resultJson = None
                        if isinstance(result, str):
                            try:
                                resultJson = json.loads(result)
                            except Exception as e:
                                self.logger.bind(tag=TAG).error(
                                    f"解析MCP工具返回结果失败: {e}"
                                )

                        # 视觉大模型不经过二次LLM处理
                        if (
                            resultJson is not None
                            and isinstance(resultJson, dict)
                            and "action" in resultJson
                        ):
                            result = ActionResponse(
                                action=Action[resultJson["action"]],
                                result=None,
                                response=resultJson.get("response", ""),
                            )
                        else:
                            result = ActionResponse(
                                action=Action.REQLLM, result=result, response=""
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
                        result = ActionResponse(
                            action=Action.REQLLM, result="MCP工具调用失败", response=""
                        )
                else:
                    # 处理系统函数
                    result = self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    )
                self._handle_function_result(result, function_call_data)

        # 存储对话内容
        if len(response_message) > 0:
            self.dialogue.put(
                Message(role="assistant", content="".join(response_message))
            )
            # 将最终回答渲染为 list 视图，遵循 hardware-ui-design.md 对话页面
            try:
                final_text = "".join(response_message)
                # 提取最近一条用户内容与近几条历史用户文本
                latest_user_text = None
                history_user = []
                try:
                    for m in reversed(self.dialogue.dialogue):
                        if m.role == "user" and latest_user_text is None:
                            latest_user_text = m.content
                        elif m.role == "user" and len(history_user) < 3:
                            history_user.append(m.content)
                        if latest_user_text and len(history_user) >= 3:
                            break
                except Exception:
                    pass

                try:
                    _, owner_name = get_badge_and_owner(getattr(self, "device_id", "")) or ("", "")
                except Exception:
                    owner_name = ""
                # 读取最近两次完整对话的“会话级摘要”
                summaries = get_recent_chat_summaries(getattr(self, "device_id", ""), limit=2)
                # 将摘要放在“历史对话”区域（最多两条）
                items = build_dialog_chat_items(owner_name, "喵喵同学", latest_user_text or "", final_text, summaries)
                # 环形窗口：最多10行，超过则保留末尾10行，并以分批渲染避免一次性超大payload
                max_lines = 10
                if len(items) > max_lines:
                    items = items[-max_lines:]
                # 分批渲染：每批5行，两帧发送，避开限流（≥500ms）
                batch_size = 5
                batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)] or [[]]
                for idx, part in enumerate(batches[:2]):
                    payload_part = {
                        "type": "ui.render",
                        "id": f"dlg-final-{self.sentence_id or ''}-{idx}",
                        "page": "dialog.chat",
                        "header": {},
                        "body": {"kind": "list", "items": part},
                        "footer": {"hint": build_chat_footer_hint()}
                    }
                    asyncio.run_coroutine_threadsafe(send_render(self, payload_part), self.loop)
                    if idx == 0 and len(batches) > 1:
                        # 间隔 ≥500ms：通过事件循环 sleep
                        try:
                            asyncio.run_coroutine_threadsafe(asyncio.sleep(0.55), self.loop).result()
                        except Exception:
                            pass

                # 不在轮次内保存“历史对话”（仅在会话关闭时保存整体摘要）
            except Exception:
                pass
        if text_index > 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )

        return True

    def _handle_mcp_tool_call(self, function_call_data):
        function_arguments = function_call_data["arguments"]
        function_name = function_call_data["name"]
        try:
            args_dict = function_arguments
            if isinstance(function_arguments, str):
                try:
                    args_dict = json.loads(function_arguments)
                except json.JSONDecodeError:
                    self.logger.bind(tag=TAG).error(
                        f"无法解析 function_arguments: {function_arguments}"
                    )
                    return ActionResponse(
                        action=Action.REQLLM, result="参数解析失败", response=""
                    )

            tool_result = asyncio.run_coroutine_threadsafe(
                self.mcp_manager.execute_tool(function_name, args_dict), self.loop
            ).result()
            # meta=None content=[TextContent(type='text', text='北京当前天气:\n温度: 21°C\n天气: 晴\n湿度: 6%\n风向: 西北 风\n风力等级: 5级', annotations=None)] isError=False
            content_text = ""
            if tool_result is not None and tool_result.content is not None:
                for content in tool_result.content:
                    content_type = content.type
                    if content_type == "text":
                        content_text = content.text
                    elif content_type == "image":
                        pass

            if len(content_text) > 0:
                return ActionResponse(
                    action=Action.REQLLM, result=content_text, response=""
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
            return ActionResponse(
                action=Action.REQLLM, result="工具调用出错", response=""
            )

        return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")

    def _handle_function_result(self, result, function_call_data):
        if result.action == Action.RESPONSE:  # 直接回复前端
            text = result.response
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4()) if function_id is None else function_id
                        ),
                        content=text,
                    )
                )
                self.chat(text, tool_call=True)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.result
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """聊天记录上报工作线程"""
        while not self.stop_event.is_set():
            try:
                # 从队列获取数据，设置超时以便定期检查停止事件
                item = self.report_queue.get(timeout=1)
                if item is None:  # 检测毒丸对象
                    break
                type, text, audio_data, report_time = item
                try:
                    # 检查线程池状态
                    if self.executor is None:
                        continue
                    # 提交任务到线程池
                    self.executor.submit(
                        self._process_report, type, text, audio_data, report_time
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"聊天记录上报线程异常: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"聊天记录上报工作线程异常: {e}")

        self.logger.bind(tag=TAG).info("聊天记录上报线程已退出")

    def _process_report(self, type, text, audio_data, report_time):
        """处理上报任务"""
        try:
            # 执行上报（传入二进制数据）
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"上报处理异常: {e}")
        finally:
            # 标记任务完成
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"清除服务端讲话状态")

    async def close(self, ws=None):
        """资源清理方法"""
        try:
            # 在会话关闭前，生成一次本轮“完整对话摘要”，加入历史（仅在存在有效轮次时）
            try:
                latest_user = None
                latest_assistant = None
                for m in reversed(self.dialogue.dialogue if isinstance(self.dialogue, Dialogue) else []):
                    if m.role == "assistant" and latest_assistant is None:
                        latest_assistant = m.content
                    elif m.role == "user" and latest_user is None:
                        latest_user = m.content
                    if latest_user and latest_assistant:
                        break
                if latest_user or latest_assistant:
                    try:
                        _, owner_name = get_badge_and_owner(getattr(self, "device_id", "")) or ("", "")
                    except Exception:
                        owner_name = ""
                    summary_text = f"{owner_name or '用户'}: {latest_user or ''} / 喵喵同学: {latest_assistant or ''}"
                    append_chat_summary(getattr(self, "device_id", ""), summary_text, max_items=2)
            except Exception:
                pass
            # 取消超时任务
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None

            # 取消编码洞察定时任务
            try:
                if hasattr(self, "coding_insight_task") and self.coding_insight_task and not self.coding_insight_task.done():
                    self.coding_insight_task.cancel()
            except Exception:
                pass

            # 清理MCP资源
            if hasattr(self, "mcp_manager") and self.mcp_manager:
                await self.mcp_manager.cleanup_all()

            # 触发停止事件
            if self.stop_event:
                self.stop_event.set()

            # 清空任务队列
            self.clear_queues()

            # 关闭WebSocket连接
            if ws:
                await ws.close()
            elif self.websocket:
                await self.websocket.close()

            # 最后关闭线程池（避免阻塞）
            if self.executor:
                try:
                    # Python 3.9+ 支持 cancel_futures
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    self.executor.shutdown(wait=False)
                self.executor = None

            # 清理 LLM 实例缓存
            try:
                if hasattr(self, "_llm_cache") and isinstance(self._llm_cache, dict):
                    self._llm_cache.clear()
            except Exception:
                pass

            # 关闭 asr/tts/llm 资源
            try:
                if hasattr(self, "asr") and hasattr(self.asr, "close") and callable(getattr(self.asr, "close")):
                    maybe_close = self.asr.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "tts") and hasattr(self.tts, "close") and callable(getattr(self.tts, "close")):
                    maybe_close = self.tts.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "llm") and hasattr(self.llm, "close") and callable(getattr(self.llm, "close")):
                    maybe_close = self.llm.close()  # 供应商可选实现
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass

            self.logger.bind(tag=TAG).info("连接资源已释放")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")

    def clear_queues(self):
        """清空所有任务队列"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

            # 使用非阻塞方式清空队列
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"清理结束: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self):
        """重置VAD状态，恢复到idle状态"""
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.listen_state = "idle"
        if self._listen_state_timer:
            self._listen_state_timer.cancel()
            self._listen_state_timer = None
        self.logger.bind(tag=TAG).debug("VAD states reset.")
    
    async def send_json(self, data: dict) -> bool:
        """统一的 JSON 消息发送封装，包含错误处理
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.websocket:
            self.logger.bind(tag=TAG).warning("send_json: websocket is None")
            return False
        
        try:
            # 优先使用 send_json 方法
            if hasattr(self.websocket, 'send_json'):
                await self.websocket.send_json(data)
            else:
                # 回退到字符串发送
                await self.websocket.send(json.dumps(data, ensure_ascii=False))
            return True
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，静默处理（预期情况）
            self.logger.bind(tag=TAG).debug(f"send_json: connection closed for device {self.device_id}")
            return False
        except Exception as e:
            # 其他异常，记录警告但不中断
            self.logger.bind(tag=TAG).warning(f"send_json failed for device {self.device_id}: {e}")
            return False
    
    async def send_text(self, text: str) -> bool:
        """统一的文本消息发送封装
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.websocket:
            self.logger.bind(tag=TAG).warning("send_text: websocket is None")
            return False
        
        try:
            await self.websocket.send(text)
            return True
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，静默处理
            self.logger.bind(tag=TAG).debug(f"send_text: connection closed for device {self.device_id}")
            return False
        except Exception as e:
            # 其他异常，记录警告
            self.logger.bind(tag=TAG).warning(f"send_text failed for device {self.device_id}: {e}")
            return False
    
    async def transition_listen_state(self, new_state: str):
        """状态机转换：idle -> listening -> finalizing -> idle"""
        old_state = self.listen_state
        if old_state == "idle" and new_state == "listening":
            self.listen_state = "listening"
            self._last_listen_event_ms = int(time.time() * 1000)
            self.logger.bind(tag=TAG).debug("Listen state: idle -> listening")
        elif old_state == "listening" and new_state == "finalizing":
            self.listen_state = "finalizing"
            self.logger.bind(tag=TAG).debug("Listen state: listening -> finalizing")
            # 触发一次handle_voice_stop
            if len(self.asr_audio) > 0:
                from core.handle.receiveAudioHandle import handleAudioMessage
                await handleAudioMessage(self, b"")
        elif old_state == "finalizing" and new_state == "idle":
            self.listen_state = "idle"
            self.logger.bind(tag=TAG).debug("Listen state: finalizing -> idle")
            self.reset_vad_states()
    
    def check_vad_fallback(self):
        """检查是否需要VAD兜底（超过fallback_ms未见设备边界）"""
        if self.listen_state != "listening":
            return False
        if self.client_listen_mode != "manual":
            return False
        now_ms = int(time.time() * 1000)
        fallback_ms = 2000  # 默认2秒
        try:
            base_cfg = self._get_base_config()
            meeting_cfg = base_cfg.get("meeting", {})
            fallback_ms = int(meeting_cfg.get("vad_fallback_ms", 2000))
        except Exception:
            pass
        last_event_ms = getattr(self, "_last_listen_event_ms", 0)
        if last_event_ms > 0 and (now_ms - last_event_ms) > fallback_ms:
            self.logger.bind(tag=TAG).debug(f"VAD兜底触发: {now_ms - last_event_ms}ms未见设备边界")
            return True
        return False

    async def send_text(self, text: str) -> None:
        """统一文本发送包装。"""
        try:
            if self.websocket:
                await self.websocket.send(text)
        except Exception:
            pass

    async def send_json(self, payload: dict) -> None:
        """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
        try:
            if self.websocket is None:
                return
            try:
                await self.websocket.send_json(payload)
            except AttributeError:
                import json as _json
                await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
        except Exception:
            # 发送错误不应中断主流程
            pass

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """检查连接超时"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.timeout_seconds)
                if not self.stop_event.is_set():
                    # 在关闭前先发送提示并提供缓冲期（与无声层策略一致）
                    try:
                        await self.websocket.send(json.dumps({
                            "type": "system",
                            "event": "timeout_warning",
                            "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
                        }))
                    except Exception:
                        pass
                    # 给予 10 秒缓冲，若期间收到任何消息，reset_timeout 会取消下一轮关闭
                    try:
                        await asyncio.sleep(10)
                    except Exception:
                        pass
                    if self.stop_event.is_set():
                        break
                    self.logger.bind(tag=TAG).info("连接超时，准备关闭")
                    await self.close(self.websocket)
                    break
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")

```

- 分批渲染已开启
  - 对长回答拆分后的行，按每批5行发送，最多两帧，帧间强制等待≥550ms，避免限流与整屏阻塞。
  - 列表窗口仍固定最多10行，确保“逐屏滚动”稳定显示到末尾。

- 页面结构已按你的要求调整
  - “>对话中：”“用户行”“空一行（0.5行占位）”“助手行们”“>历史对话：”“• 历史1”“• 历史2”
  - 仅历史项前有小圆点；其它标题/用户/助手前均无小圆点。
  - 占位通过特殊项 `<blank>` 在清洗阶段转换为空白行实现。

---

**User**

逻辑错误非常严重,相当于刷新后瞬间就变成了以下格式,应该一直都是统一的格式!!!
“喵喵同学: <助手话>
 喵喵同学: <助手话>
 喵喵同学: <助手话>”

---

**Cursor**

```python
import os
import sys
import copy
import json
import uuid
import time
import queue
import asyncio
import threading
import traceback
from config.logger import truncate_for_log
import subprocess
import websockets
from core.handle.mcpHandle import call_mcp_tool
from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
)
from typing import Dict, Any
from core.mcp.manager import MCPManager
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.handle.functionHandler import FunctionHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, update_module_string
from config.manage_api_client import DeviceNotFoundException, DeviceBindException
from core.orchestration.render_sender import send_render
from core.orchestration.dialog_ui import build_dialog_chat_items, build_chat_footer_hint, wrap_label_text
from core.utils.device_registry import get_badge_and_owner
from core.orchestration.history_store import append_chat_summary, get_recent_chat_summaries
from core.utils.dialogue import Dialogue


TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # 保存server实例的引用

        self.auth = AuthMiddleware(config)
        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.client_ip_info = {}
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"

        # 客户端状态相关
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"
        # 监听状态机：idle -> listening -> finalizing -> idle
        self.listen_state = "idle"
        self._listen_state_timer = None
        self._last_listen_event_ms = 0

        # 线程任务相关
        self.loop = asyncio.get_event_loop()
        self.stop_event = threading.Event()
        # 缩减线程池，降低上下文切换与内存占用
        try:
            meeting_cfg = self.config.get("meeting", {}) if isinstance(self.config, dict) else {}
            # 固化 W3：线程池默认 2，可被 meeting.threadpool_max_workers 覆盖
            default_workers = 2
            max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
            if max_workers < 1:
                max_workers = default_workers
        except Exception:
            max_workers = 2
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 添加上报线程池
        self.report_queue = queue.Queue()
        self.report_thread = None
        # 未来可以通过修改此处，调节asr的上报和tts的上报，目前默认都开启
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # 依赖的组件
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_no_voice_last_time = 0.0
        self.client_voice_stop = False
        self.client_voice_frame_count = 0

        # asr相关变量
        # 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
        # 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()

        # llm相关变量
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # tts相关变量
        self.sentence_id = None

        # iot相关变量
        self.iot_descriptors = {}
        self.func_handler = None

        # 模式状态（meeting/coding/working/dialog）
        # 阶段2默认进入 connected.idle，欢迎页不允许渲染
        self.current_mode = "connected.idle"
        # 会议模式相关缓存
        self.meeting_segments = []  # [{"ts": int(ms), "text": str}]
        self.meeting_start_ts = 0.0
        self.meeting_last_snippet_ts = 0.0
        self.meeting_last_snippet_index = 0
        # 会议片段节流与幂等状态
        self.meeting_recent_texts = {}
        self.meeting_pending_texts = []
        self.meeting_last_emit_ms = 0.0
        self.meeting_finalized = False
        # 编码模式日志流运行标志/阶段名（用于 stop/clear/phase 扩展）
        self.coding_stream_running = False
        self.coding_phase_name = ""

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        # 是否在聊天结束后关闭连接
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_task = None
        # 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
        try:
            base_idle = int(self.config.get("close_connection_no_voice_time", 600))
        except Exception:
            base_idle = 600
        self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭

        # {"mcp":true} 表示启用MCP功能
        self.features = None

        # LLM 按模式实例缓存（随连接释放）
        self._llm_cache = {}

    def _get_base_config(self) -> Dict[str, Any]:
        try:
            srv = getattr(self, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            if isinstance(base_cfg, dict):
                return base_cfg
        except Exception:
            pass
        return self.config if isinstance(self.config, dict) else {}

    def get_llm_for(self, purpose: str):
        """按用途/模式返回 LLM 实例，懒加载并缓存。

        purpose 可取："chat" | "meeting" | "coding" | "working" | "intent" | "memory"
        """
        try:
            key = str(purpose or "chat").lower()
        except Exception:
            key = "chat"

        # 缓存命中
        if key in self._llm_cache and self._llm_cache[key] is not None:
            return self._llm_cache[key]

        base_cfg = self._get_base_config()
        # 读取映射
        mapping = {}
        try:
            mapping = base_cfg.get("llm_by_mode", {}) or {}
