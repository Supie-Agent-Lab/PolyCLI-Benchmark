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

                # 统一页面结构：标题/分隔/用户/空行/助手若干/历史标题与条目
                header_lines = [">对话中：", "────────────────────────────────"]
                user_lines = wrap_label_text(f"{owner_name}: ", latest_user_text or "") if latest_user_text else []
                blank_line = ["<blank>"]
                assistant_lines = wrap_label_text("喵喵同学: ", final_text)
                history_lines: list[str] = []
                if summaries:
                    history_lines.extend(["> 历史对话：", "────────────────────────────────"])
                    for s in summaries:
                        history_lines.append(f"• {s}")

                # 分批：助手内容每批最多5行；每帧保持统一结构（重复标题/用户/空行），避免“只剩助手行”的错觉
                max_lines = 10
                assistant_batch_size = 5
                batches: list[list[str]] = []
                for i in range(0, len(assistant_lines) or 1, assistant_batch_size):
                    batches.append(assistant_lines[i:i+assistant_batch_size])
                if not batches:
                    batches = [[]]

                for idx, asst_part in enumerate(batches[:2]):
                    items_page: list[str] = []
                    items_page.extend(header_lines)
                    items_page.extend(user_lines)
                    items_page.extend(blank_line)
                    # 填入本批助手行
                    items_page.extend(asst_part)
                    # 若为最后一批且有空间，补充历史区
                    if idx == len(batches[:2]) - 1 and history_lines:
                        remain = max_lines - len(items_page)
                        if remain > 0:
                            items_page.extend(history_lines[:remain])
                    # 截断至最大行
                    if len(items_page) > max_lines:
                        items_page = items_page[:max_lines]

                    payload_part = {
                        "type": "ui.render",
                        "id": f"dlg-final-{self.sentence_id or ''}-{idx}",
                        "page": "dialog.chat",
                        "header": {},
                        "body": {"kind": "list", "items": items_page},
                        "footer": {"hint": build_chat_footer_hint()}
                    }
                    asyncio.run_coroutine_threadsafe(send_render(self, payload_part), self.loop)
                    if idx == 0 and len(batches) > 1:
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

收到，我已修正为“每一帧都保持统一的页面结构”，不会出现只有“喵喵同学”行的格式跳变：

- 分批渲染逻辑更新
  - 每帧都包含相同的结构顺序：
    1) 标题与分隔
    2) 用户行（可能多行）
    3) 空白行（0.5行占位）
    4) 本批的助手行（最多5行/帧）
    5) 最后一帧若有余量再补“历史对话”与分隔及“• 历史”条目
  - 这样即便是第二帧，也会保留标题/用户/空白等，视觉结构不变。
  - 帧间等待≥550ms，避免限流与整屏阻塞。

- 其它保持
  - 总行数固定10行；超出按窗口裁剪。
  - 仅“• 历史”前有圆点；其余标题/用户/助手前不加圆点。
  - 空白行通过占位 `<blank>` 在清洗阶段变成空字符串实现。

---

**User**

现在前面还是有小圆圈!!! 请删除小圆圈;
然后前面的“>对话中”改成“> 正在对话中：” 加一个空格!!!

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
    items.append("> 正在对话中：")
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
            items.append(f"{_truncate(t)}")

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

已调整：
- 标题改为“> 正在对话中：”（前面加空格）。
- 移除历史项前的小圆圈；历史区现在显示为纯文本行。

如需对历史项再加统一前缀（如“- ”），告诉我具体字符即可。

---

**User**

现在硬件屏幕还是会显示小圆圈!!!

现在硬件页面还是显示“>对话中” 而不是 “> 正在对话中” 请仔细检查后端发给硬件的渲染函数!

---

**Cursor**

我先修正发送渲染时的标题与历史项格式：1) 将 `>对话中：` 改为 `> 正在对话中：`；2) 去掉历史项前的小圆圈。随后检查静态错误。

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

                # 统一页面结构：标题/分隔/用户/空行/助手若干/历史标题与条目
                header_lines = ["> 正在对话中：", "────────────────────────────────"]
                user_lines = wrap_label_text(f"{owner_name}: ", latest_user_text or "") if latest_user_text else []
                blank_line = ["<blank>"]
                assistant_lines = wrap_label_text("喵喵同学: ", final_text)
                history_lines: list[str] = []
                if summaries:
                    history_lines.extend(["> 历史对话：", "────────────────────────────────"])
                    for s in summaries:
                        history_lines.append(f"{s}")

                # 分批：助手内容每批最多5行；每帧保持统一结构（重复标题/用户/空行），避免“只剩助手行”的错觉
                max_lines = 10
                assistant_batch_size = 5
                batches: list[list[str]] = []
                for i in range(0, len(assistant_lines) or 1, assistant_batch_size):
                    batches.append(assistant_lines[i:i+assistant_batch_size])
                if not batches:
                    batches = [[]]

                for idx, asst_part in enumerate(batches[:2]):
                    items_page: list[str] = []
                    items_page.extend(header_lines)
                    items_page.extend(user_lines)
                    items_page.extend(blank_line)
                    # 填入本批助手行
                    items_page.extend(asst_part)
                    # 若为最后一批且有空间，补充历史区
                    if idx == len(batches[:2]) - 1 and history_lines:
                        remain = max_lines - len(items_page)
                        if remain > 0:
                            items_page.extend(history_lines[:remain])
                    # 截断至最大行
                    if len(items_page) > max_lines:
                        items_page = items_page[:max_lines]

                    payload_part = {
                        "type": "ui.render",
                        "id": f"dlg-final-{self.sentence_id or ''}-{idx}",
                        "page": "dialog.chat",
                        "header": {},
                        "body": {"kind": "list", "items": items_page},
                        "footer": {"hint": build_chat_footer_hint()}
                    }
                    asyncio.run_coroutine_threadsafe(send_render(self, payload_part), self.loop)
                    if idx == 0 and len(batches) > 1:
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

已修正后端实际下发的列表内容：
- 统一使用“> 正在对话中：”作为页首标题。
- 历史条目前不再添加小圆圈，直接输出文本。

请再试一次唤醒→对话，确认页首是否已更新为带空格的“> 正在对话中：”。

---

**User**

历史对话显示不需要包含“用户”和“喵喵助手”

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

                # 统一页面结构：标题/分隔/用户/空行/助手若干/历史标题与条目
                header_lines = ["> 正在对话中：", "────────────────────────────────"]
                user_lines = wrap_label_text(f"{owner_name}: ", latest_user_text or "") if latest_user_text else []
                blank_line = ["<blank>"]
                assistant_lines = wrap_label_text("喵喵同学: ", final_text)
                history_lines: list[str] = []
                if summaries:
                    history_lines.extend(["> 历史对话：", "────────────────────────────────"])
                    for s in summaries:
                        history_lines.append(f"{s}")

                # 分批：助手内容每批最多5行；每帧保持统一结构（重复标题/用户/空行），避免“只剩助手行”的错觉
                max_lines = 10
                assistant_batch_size = 5
                batches: list[list[str]] = []
                for i in range(0, len(assistant_lines) or 1, assistant_batch_size):
                    batches.append(assistant_lines[i:i+assistant_batch_size])
                if not batches:
                    batches = [[]]

                for idx, asst_part in enumerate(batches[:2]):
                    items_page: list[str] = []
                    items_page.extend(header_lines)
                    items_page.extend(user_lines)
                    items_page.extend(blank_line)
                    # 填入本批助手行
                    items_page.extend(asst_part)
                    # 若为最后一批且有空间，补充历史区
                    if idx == len(batches[:2]) - 1 and history_lines:
                        remain = max_lines - len(items_page)
                        if remain > 0:
                            items_page.extend(history_lines[:remain])
                    # 截断至最大行
                    if len(items_page) > max_lines:
                        items_page = items_page[:max_lines]

                    payload_part = {
                        "type": "ui.render",
                        "id": f"dlg-final-{self.sentence_id or ''}-{idx}",
                        "page": "dialog.chat",
                        "header": {},
                        "body": {"kind": "list", "items": items_page},
                        "footer": {"hint": build_chat_footer_hint()}
                    }
                    asyncio.run_coroutine_threadsafe(send_render(self, payload_part), self.loop)
                    if idx == 0 and len(batches) > 1:
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
                        # 历史摘要不包含“用户/喵喵”前缀，仅保留关键信息（优先助手最终回答）
                        summary_text = (latest_assistant or latest_user or "")
                    except Exception:
                        summary_text = (latest_assistant or latest_user or "")
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

---

**User**

问题1 : 为什么对话模式只有6行? 应该是自动动态调整的!
问题2 : 而且超长对话的刷新太快了, 用户还没看完内容就瞬间刷新了!

---

**Cursor**

```python
import os
import threading
from typing import Optional, Tuple
from ruamel.yaml import YAML


_yaml = YAML(typ="safe")
_LOCK = threading.RLock()
_CACHE = {
    "path": None,
    "mtime": 0.0,
    "data": {},
}


def _data_file_path() -> str:
    # backend/core/utils/ -> backend/data/devices.yaml
    base_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(base_dir, "../../data/devices.yaml"))
    return path


def _load_if_needed() -> None:
    path = _data_file_path()
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = 0.0
    with _LOCK:
        if _CACHE["path"] != path or float(_CACHE["mtime"]) != float(mtime):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = _yaml.load(f) or {}
            except Exception:
                data = {}
            _CACHE["path"] = path
            _CACHE["mtime"] = float(mtime)
            _CACHE["data"] = data


def _normalize_device_id(device_id: Optional[str]) -> Optional[str]:
    try:
        if device_id is None:
            return None
        v = str(device_id).strip().strip('"').strip("'")
        return v.lower() if v else None
    except Exception:
        return None


def get_badge_and_owner(device_id: str) -> Optional[Tuple[str, str]]:
    """返回 (badge, owner) 或 None。"""
    _load_if_needed()
    did = _normalize_device_id(device_id)
    if did is None:
        return None
    try:
        devices = (_CACHE.get("data") or {}).get("devices") or {}
        meta = devices.get(did)
        if not isinstance(meta, dict):
            return None
        badge = str(meta.get("badge", "")).strip()
        owner = str(meta.get("owner", "")).strip()
        if not badge or not owner:
            return None
        return badge, owner
    except Exception:
        return None


def get_display_title(device_id: str) -> Optional[str]:
    """组装显示标题：工牌{badge} · {owner}。未注册返回 None。"""
    pair = get_badge_and_owner(device_id)
    if pair is None:
        return None
    badge, owner = pair
    return f"工牌{badge} · {owner}"



def get_lines_per_page(device_id: str, default_value: int = 8) -> int:
    """返回设备对话页可显示的最大行数。缺省 8，可在 devices.yaml 中按设备配置：
    devices:
      "aa:bb:...":
        lines_per_page: 10
    """
    _load_if_needed()
    did = _normalize_device_id(device_id)
    if did is None:
        return int(default_value)
    try:
        devices = (_CACHE.get("data") or {}).get("devices") or {}
        meta = devices.get(did) or {}
        v = int(meta.get("lines_per_page", default_value))
        return v if v > 0 else int(default_value)
    except Exception:
        return int(default_value)


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
from core.orchestration.dialog_ui import build_dialog_chat_items, build_chat_footer_hint, wrap_label_text
from core.utils.device_registry import get_badge_and_owner, get_lines_per_page
from core.orchestration.history_store import append_chat_summary, get_recent_chat_summaries
from core.utils.dialogue import Dialogue


TAG = __name__

auto_import_modules("plugins_func.functions")

