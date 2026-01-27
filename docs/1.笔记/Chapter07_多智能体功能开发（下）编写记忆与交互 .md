# ITS 智能客服系统 —— 多智能体开发实战 (下)

**主题**: 基于 OpenAI Agents SDK 构建企业级多智能体客服系统（记忆会话与流式通信）

**时长**: 1-2 天

**讲师**：胡中奎

**版本**：v1.0 

## 1、任务目标

在完成了智能体核心逻辑（大脑）和基础设施（手脚）的构建后，本篇我们将重点关注系统的**记忆能力**与**交互能力**。我们将实现一个能够记住用户历史对话，并能以流式（打字机效果）实时响应用户请求的 Web 服务。



**1.1 理论知识**

**1. 理解会话管理 (Session Management)**:

  \- **持久化**: 如何将用户的对话历史保存到磁盘，确保重启服务后记忆不丢失。

  \- **上下文窗口**: 为什么需要截断过长的历史记录（Token 限制与成本控制）。

**2. 掌握 Server-Sent Events (SSE)**:

  \- 一种轻量级的服务器向客户端推送消息的技术。

  \- 相比 WebSocket 更简单，非常适合大模型流式输出场景。

**3. 理解 Pydantic 数据验证**:

  \- 如何定义请求和响应的数据结构，确保前后端交互的数据类型安全。



**1.2 动手实战**

1. **构建记忆系统**: 实现 `SessionManager`，管理用户会话文件的增删改查。

2. **实现流式处理**: 编写 `StreamProcessor`，将 Agents SDK 的复杂事件转换为前端易读的格式。

3. **开发 API 接口**: 使用 FastAPI 暴露 HTTP 接口，联调整个系统。



##  2、关键技术栈

\-  **FastAPI**: 高性能 Web 框架，用于构建 API。

\-  **Pydantic**: 数据验证库，定义 API 的输入输出模型。

\-  **Async Generator (异步生成器)**: Python 的 `yield` 语法，用于实现流式数据传输。

\-  **JSON File Storage**: 使用本地文件系统存储 JSON 格式的会话历史（生产环境可替换为 Redis/MySQL）。





## 3、构建记忆与会话系统

记忆系统是多智能体对话的基础，它使智能体能够理解上下文、记住用户偏好和历史问题，实现真正连贯的多轮对话体验。

### 1. 目标

创建"记忆管家"——智能记忆系统，负责安全、可靠地存储和管理用户对话历史，为智能体提供准确的上下文记忆支持。

**模块位置**: `backend/app/application/session_manager.py`

### 2. 需求分析

1. **记忆系统的核心职责是什么？**
   - **历史对话存储**：完整保存用户与智能体的对话记录，包括用户输入和智能体响应
   - **上下文管理**：为智能体提供准确的对话上下文，确保多轮对话的连贯性
   - **记忆优化**：智能管理历史记忆，平衡上下文长度与系统性能
   - **数据安全**：确保用户数据的安全存储和访问控制
2. **如何设计高效的数据存储结构？**
   - **分层存储**：用户级 → 会话级 → 消息级三级存储结构
   - **文件系统存储**：使用JSON文件格式，便于读写和维护
   - **目录结构**：按用户ID组织，会话文件独立存储
   - **元数据管理**：每条消息包含角色、内容、时间戳、来源等完整信息
3. **如何保证记忆的准确性和智能性？**
   - **内容清理**：自动清理幻觉数据和异常格式
   - **智能截断**：保留关键对话，去除冗余信息
   - **异常恢复**：文件损坏时自动恢复并重建
   - **性能优化**：异步保存，避免阻塞主线程

### 3. 实现流程

1. **初始化会话管理器**：
   - 确定记忆存储的根目录（如`user_memories`）
   - 创建目录结构，按用户ID组织子目录
2. **用户会话文件管理**：
   - 为每个用户创建独立的存储目录
   - 每个会话对应一个独立的JSON文件
   - 提供灵活的文件路径获取方法
3. **记忆加载与初始化**：
   - 根据用户ID和会话ID加载历史记录
   - 如果文件不存在，创建带系统消息的初始化记忆
   - 处理文件损坏等异常情况
4. **记忆保存与持久化**：
   - 将对话历史保存到JSON文件
   - 支持格式化输出，便于阅读和调试
   - 确保中文内容正确编码
5. **智能记忆优化**：
   - 分离系统消息和对话内容
   - 清洗幻觉数据（如`end_conversation`标记）
   - 智能截断，保留最近N轮对话
   - 平衡上下文长度与信息完整性
6. **会话管理与查询**：
   - 获取用户的所有会话列表
   - 按创建时间排序，最新会话优先
   - 提供会话摘要信息（消息数量、创建时间等）



### 4. 代码实现

#### 1. 关键代码解析

**1. 初始化与目录管理**：

```python
def __init__(self):
    # 确定基础目录和记忆存储目录
    self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    self.MEMORY_DIR = os.path.join(self.BASE_DIR, "user_memories")

    # 确保记忆目录存在
    if not os.path.exists(self.MEMORY_DIR):
        os.makedirs(self.MEMORY_DIR)
```

**2. 用户会话文件路径管理**：

```python
def _get_user_directory(self, user_id: str) -> str:
    """获取用户专属的记忆存储目录"""
    user_dir = os.path.join(self.MEMORY_DIR, user_id)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

def _get_user_memory_file(self, user_id: str, session_id: Optional[str] = None) -> str:
    """获取用户特定会话的记忆文件路径"""
    user_dir = self._get_user_directory(user_id)
    if session_id is None:
        session_id = "default"
    return os.path.join(user_dir, f"{session_id}.json")
```

**3. 记忆加载与初始化**：

```python
def load_history(self, user_id: str, session_id: Optional[str] = None) -> List[Dict]:
    """加载用户的对话历史记录"""
    file_path = self._get_user_memory_file(user_id, session_id)

    # 如果文件不存在，创建带系统消息的初始化记忆
    if not os.path.exists(file_path):
        session_info = f"（会话ID: {session_id}）" if session_id else "（默认会话）"
        return [
            {"role": "system", "content": f"你是一个有记忆的助手，会基于历史对话解决用户问题。{session_info}"}
        ]

    try:
        # 正常加载JSON格式的记忆文件
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # 文件损坏时的优雅处理
        session_name = session_id or "默认"
        logger.warning(f"用户 {user_id} 的{session_name}会话记忆文件损坏，已重置")
        return [{"role": "system", "content": "记忆文件损坏，已重置"}]
```

**4. 智能记忆截断与清洗:**

```python
def _truncate_memory(self, chat_history: List[Dict], max_rounds: int = 10) -> List[Dict]:
    """智能截断记忆，保留最近的关键对话"""
    # 分离系统消息（始终保留）和内容消息
    system_msg = [msg for msg in chat_history if msg["role"] == "system"]
    content_msgs = [msg for msg in chat_history if msg["role"] != "system"]

    # 清洗幻觉数据和异常格式
    import re
    cleaned_content_msgs = []
    for msg in content_msgs:
        content = msg.get("content", "")
        if isinstance(content, str) and "end_conversation" in content:
            # 提取有效消息内容，清理幻觉标记
            match = re.search(r'[\'"]message[\'"]:\s*[\'"](.*?)[\'"]', content)
            if match:
                clean_text = match.group(1)
                clean_text = clean_text.replace('\\"', '"').replace("\\'", "'")
                msg["content"] = clean_text
            else:
                # 无法提取有效内容，直接替换
                if "{" in content and "}" in content:
                    msg["content"] = "对话已结束。"
        cleaned_content_msgs.append(msg)
    
    content_msgs = cleaned_content_msgs

    # 保留最近max_rounds*2条内容消息（每轮对话2条）
    truncated_content = content_msgs[-2 * max_rounds:] if len(content_msgs) > 2 * max_rounds else content_msgs
    return system_msg + truncated_content
```



#### 2. 完整代码实现

```python
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from backend.app.infrastructure.logger import logger

class SessionManager:
    """
    智能记忆系统 - 记忆管家
    负责安全、可靠地存储和管理用户对话历史，为智能体提供准确的上下文记忆支持
    """
    
    def __init__(self):
        """
        初始化记忆系统
        创建记忆存储目录，确保数据持久化基础
        """
        # 确定基础目录：假设本文件在backend/app/application/session_manager.py
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 记忆存储目录：backend/app/user_memories
        self.MEMORY_DIR = os.path.join(self.BASE_DIR, "user_memories")
        
        # 确保记忆目录存在
        if not os.path.exists(self.MEMORY_DIR):
            os.makedirs(self.MEMORY_DIR)
            logger.info(f"创建记忆存储目录: {self.MEMORY_DIR}")

    def _get_user_directory(self, user_id: str) -> str:
        """
        [内部方法] 获取用户专属的记忆存储目录
        
        参数:
            user_id: 用户唯一标识符
            
        返回:
            str: 用户目录路径
        """
        user_dir = os.path.join(self.MEMORY_DIR, user_id)
        # 确保用户目录存在
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            logger.debug(f"创建用户目录: {user_dir}")
        return user_dir

    def _get_user_memory_file(self, user_id: str, session_id: Optional[str] = None) -> str:
        """
        [内部方法] 获取用户特定会话的记忆文件路径
        
        参数:
            user_id: 用户唯一标识符
            session_id: 会话标识符，None时使用"default"
            
        返回:
            str: 记忆文件完整路径
        """
        user_dir = self._get_user_directory(user_id)
        if session_id is None:
            session_id = "default"
        # 确保文件扩展名为.json
        return os.path.join(user_dir, f"{session_id}.json")

    def load_history(self, user_id: str, session_id: Optional[str] = None) -> List[Dict]:
        """
        加载用户的对话历史记录
        
        参数:
            user_id: 用户唯一标识符
            session_id: 会话标识符
            
        返回:
            List[Dict]: 对话历史记录列表，包含系统消息、用户消息和助手消息
            
        异常处理:
            - 文件不存在：创建初始化记忆
            - JSON解析失败：重置记忆文件
        """
        file_path = self._get_user_memory_file(user_id, session_id)

        # 如果文件不存在，创建初始化记忆
        if not os.path.exists(file_path):
            session_info = f"（会话ID: {session_id}）" if session_id else "（默认会话）"
            logger.info(f"创建新会话: 用户 {user_id}, 会话 {session_info}")
            return [
                {"role": "system", "content": f"你是一个有记忆的助手，会基于历史对话解决用户问题。{session_info}"}
            ]

        try:
            # 正常加载JSON格式的记忆文件
            with open(file_path, "r", encoding="utf-8") as f:
                history = json.load(f)
                logger.debug(f"加载用户 {user_id} 的会话记忆，共 {len(history)} 条记录")
                return history
                
        except json.JSONDecodeError as e:
            # 文件损坏时的优雅处理
            session_name = session_id or "默认"
            logger.warning(f"用户 {user_id} 的{session_name}会话记忆文件损坏，已重置。错误: {str(e)}")
            return [{"role": "system", "content": "记忆文件损坏，已重置"}]
            
        except Exception as e:
            logger.error(f"加载用户 {user_id} 记忆时发生未知错误: {str(e)}")
            return [{"role": "system", "content": "记忆加载失败，请重新开始对话"}]

    def save_history(self, user_id: str, chat_history: List[Dict], session_id: Optional[str] = None) -> None:
        """
        保存用户的对话历史记录到本地文件
        
        参数:
            user_id: 用户唯一标识符
            chat_history: 最新的对话历史记录列表
            session_id: 会话标识符
            
        说明:
            - 使用JSON格式保存，便于阅读和调试
            - 确保中文字符正确编码
            - 格式化输出，便于人工检查
        """
        file_path = self._get_user_memory_file(user_id, session_id)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(chat_history, f, ensure_ascii=False, indent=2)
            logger.debug(f"保存用户 {user_id} 的会话记忆到: {file_path}")
            
        except Exception as e:
            logger.error(f"保存用户 {user_id} 记忆时发生错误: {str(e)}")
            raise

    def _truncate_memory(self, chat_history: List[Dict], max_rounds: int = 10) -> List[Dict]:
        """
        [内部方法] 智能截断记忆：保留最近的关键对话
        
        参数:
            chat_history: 原始对话历史
            max_rounds: 最大保留轮数（1轮 = 用户消息 + 助手消息）
            
        返回:
            List[Dict]: 截断后的对话历史
            
        处理逻辑:
            1. 分离系统消息（始终保留）
            2. 清洗幻觉数据和异常格式
            3. 保留最近max_rounds轮对话
        """
        # 分离系统消息（始终保留）和内容消息
        system_msg = [msg for msg in chat_history if msg["role"] == "system"]
        content_msgs = [msg for msg in chat_history if msg["role"] != "system"]

        # --- 数据清洗：修复智能体幻觉产生的无效数据 ---
        import re
        cleaned_content_msgs = []
        for msg in content_msgs:
            content = msg.get("content", "")
            if isinstance(content, str) and "end_conversation" in content:
                # 尝试提取有效的消息内容
                # 匹配模式： "message": "..." 或 'message': '...'
                match = re.search(r'[\'"]message[\'"]:\s*[\'"](.*?)[\'"]', content)
                if match:
                    clean_text = match.group(1)
                    # 清理转义字符
                    clean_text = clean_text.replace('\\"', '"').replace("\\'", "'")
                    msg["content"] = clean_text
                else:
                    # 如果匹配失败但包含end_conversation，说明是无效数据
                    if "{" in content and "}" in content:  # 看起来像JSON但格式错误
                        msg["content"] = "对话已结束。"
            cleaned_content_msgs.append(msg)
        
        content_msgs = cleaned_content_msgs
        # ------------------------------------------------

        # 保留最近 max_rounds*2 条内容消息（每轮对话2条）
        if len(content_msgs) > 2 * max_rounds:
            truncated_content = content_msgs[-2 * max_rounds:]
            logger.debug(f"记忆截断: 从 {len(content_msgs)} 条消息截断到 {len(truncated_content)} 条")
        else:
            truncated_content = content_msgs
            
        return system_msg + truncated_content

    def get_all_sessions_memory(self, user_id: str) -> List[Dict]:
        """
        获取用户的所有会话记忆数据
        
        参数:
            user_id: 用户唯一标识符
            
        返回:
            List[Dict]: 包含所有会话信息的列表，格式:
                [
                    {
                        "session_id": "会话ID",
                        "create_time": "创建时间",
                        "memory": [...],  # 会话内容（不含系统消息）
                        "total_messages": 消息数量
                    },
                    ...
                ]
        """
        user_dir = self._get_user_directory(user_id)
        all_sessions = []
        
        try:
            # 遍历用户目录下的所有JSON文件
            for filename in os.listdir(user_dir):
                if filename.endswith(".json"):
                    session_id = filename[:-5]  # 移除.json扩展名
                    file_path = os.path.join(user_dir, filename)

                    # 获取文件创建时间
                    try:
                        create_time = datetime.fromtimestamp(
                            os.path.getctime(file_path)
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        create_time = "未知时间"

                    # 读取会话记忆
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            memory = json.load(f)
                            # 过滤掉系统消息，只保留对话内容
                            conversation_memory = [
                                msg for msg in memory if msg["role"] != "system"
                            ]

                            all_sessions.append({
                                "session_id": session_id,
                                "create_time": create_time,
                                "memory": conversation_memory,
                                "total_messages": len(conversation_memory)
                            })
                    except Exception as e:
                        logger.warning(f"读取用户 {user_id} 的会话 {session_id} 时出错: {str(e)}")
                        all_sessions.append({
                            "session_id": session_id,
                            "create_time": create_time,
                            "memory": [],
                            "error": str(e),
                            "total_messages": 0
                        })

            # 按创建时间倒序排序（最新的在前面）
            all_sessions.sort(key=lambda x: x["create_time"], reverse=True)
            logger.info(f"获取用户 {user_id} 的 {len(all_sessions)} 个会话")

        except FileNotFoundError:
            logger.info(f"用户 {user_id} 还没有任何会话记录")
        except Exception as e:
            logger.error(f"获取用户 {user_id} 的所有会话时出错: {str(e)}")

        return all_sessions

    def prepare_history(self, user_id: str, session_id: str, user_input: str, max_rounds: int = 3) -> List[Dict]:
        """
        准备聊天历史记录：加载、添加新输入、智能截断
        
        参数:
            user_id: 用户ID
            session_id: 会话ID
            user_input: 用户当前输入
            max_rounds: 保留的最大对话轮数
            
        返回:
            List[Dict]: 处理后的聊天历史列表
            
        处理流程:
            1. 加载用户历史聊天记录
            2. 添加当前用户输入
            3. 智能截断，保留最近的关键对话
        """
        # 加载用户历史聊天记录
        chat_history = self.load_history(user_id, session_id)

        # 将当前用户输入添加到聊天历史中
        chat_history.append({"role": "user", "content": user_input})

        # 智能截断聊天历史
        chat_history = self._truncate_memory(chat_history, max_rounds=max_rounds)

        # 记录处理后的聊天历史长度
        logger.debug(f"用户 {user_id} 会话 {session_id}: 加载并截断后的聊天历史长度: {len(chat_history)}")

        return chat_history

# 全局实例，供整个应用使用
session_manager = SessionManager()
```



## 4、构建流式API与前端SSE通信

为了提供更好的用户体验，我们需要将智能体的思考过程和答案以流式（Streaming）的方式返回给前端。本章将构建基于FastAPI的流式API，并通过Server-Sent Events（SSE）协议与前端通信，实现实时、动态的智能体对话展示。

### 1. 目标

创建"流式通信引擎"——实时消息传递系统，负责将智能体的思考过程、工具调用和最终答案以流式方式推送到前端，实现多智能体协同的实时可视化。

**模块位置**:

- `backend/app/application/agent_service.py`
- `backend/app/application/stream_processor.py`
- `backend/app/presentation/routes.py`
- `backend/app/presentation/response_utils.py`

### 2. 需求分析

1. **流式通信系统的核心职责是什么？**
   - **实时事件推送**：将智能体的思考过程、工具调用、交接事件实时推送到前端
   - **消息分类处理**：区分思考过程、处理事件和最终答案，实现差异化展示
   - **流式传输优化**：确保SSE连接的稳定性和低延迟
   - **错误处理与重试**：处理网络中断、超时等异常情况，提供重试机制
2. **如何设计高效的事件处理管道？**
   - **事件源接入**：连接OpenAI Agents SDK的事件流
   - **事件分类器**：识别不同类型的事件（文本生成、推理、工具调用、交接等）
   - **消息转换器**：将原始事件转换为前端友好的SSE消息格式
   - **流控制器**：管理子智能体响应的缓存和释放时机
3. **如何保证流式通信的稳定性和兼容性？**
   - **连接管理**：处理SSE连接的生命周期，包括建立、维持和关闭
   - **兼容性处理**：适配不同版本的OpenAI SDK事件类型
   - **缓冲区管理**：智能缓存子智能体响应，避免中断思考过程
   - **兜底机制**：确保所有内容最终都能正确推送到前端



### 3. 实现流程

1. **设计SSE消息格式**：

   我们定义三种消息类型：THINKING（思考过程）、PROCESS（处理过程，如工具调用、交接）、ANSWER（最终答案）。每种消息类型都有对应的前端展示区域。

2. **构建流式响应处理管道**：

   - 使用OpenAI Agents SDK的`Runner.run_streamed`方法获取事件流
   - 编写`process_stream_response_events`函数，将原始事件转换为SSE消息

3. **事件分类处理**：

   - 文本生成事件（ResponseTextDeltaEvent）：根据当前智能体类型决定消息类型（调度智能体→ANSWER，子智能体→缓存后统一发送）
   - 推理事件（ResponseReasoningTextDeltaEvent）：转换为THINKING类型
   - 智能体交接事件（handoff_occured）：转换为PROCESS类型
   - 工具调用事件（tool_called）：转换为PROCESS类型，并显示工具名称
   - 智能体状态更新事件（agent_updated_stream_event）：转换为PROCESS类型

4. **构建FastAPI流式端点**：

   - 使用FastAPI的`StreamingResponse`返回SSE流
   - 在端点中调用`AgentService.process_query`方法，并将其返回的异步生成器传递给`StreamingResponse`

5. **前端SSE连接与事件处理**：

   - 前端使用`EventSource`连接SSE端点
   - 根据消息类型将内容渲染到不同的UI组件中



### 4. 代码实现

#### 1.关键代码解析

**1. SSE消息格式定义（schemas.py）**：

```python
class TypeEnum(str, Enum):
    """
    内容语义分类：用于前端决定渲染到主答案区域还是思考过程区域。
    """
    THINKING = 'THINKING'  # 子智能体的自然语言输出或推理中间步骤，显示在"思考过程"可折叠区块中
    PROCESS = 'PROCESS'    # 系统级流程事件（如智能体交接、工具调用），也归入"思考过程"区域展示
    ANSWER = 'ANSWER'      # 调度智能体生成的最终用户可见回答，显示在主聊天区域（assistant 消息）

class MessageResponse(BaseModel):
    """
    标准化的 SSE 流式响应消息结构，前端通过解析此结构进行渲染和状态管理。
    """
    id: str                                               # 消息唯一 ID（UUID），用于去重或追踪
    content: AllMessagesType | List[AllMessagesType]      # 消息主体内容
    status: StatusEnum                                    # 传输状态：IN_PROGRESS（流中）或 FINISHED（结束）
    metadata: Metadata                                    # 元信息，包含时间、结束原因等
```

**2. 流式事件处理器核心逻辑（stream_processor.py）**

```python
async def process_stream_response_events(result):
    """
    处理智能体流式响应事件的核心处理器
    
    处理逻辑：
    1. 文本与推理事件：根据当前智能体类型决定消息类型
    2. 交接与工具事件：转换为PROCESS类型消息
    3. 智能体状态更新：更新当前智能体跟踪
    4. 缓存管理：智能管理子智能体响应缓存
    """
    current_agent_name = "调度智能体"
    sub_agent_response_buffer = []  # 子智能体响应缓存

    async for event in result.stream_events():
        
        # 处理文本与推理生成事件
        if event.type == "raw_response_event":
            await handle_raw_response_event(event, current_agent_name, sub_agent_response_buffer)
        
        # 处理智能体交接与工具调用事件
        elif event.type == "run_item_stream_event":
            await handle_run_item_event(event, current_agent_name, sub_agent_response_buffer)
        
        # 处理智能体状态更新事件
        elif event.type == "agent_updated_stream_event":
            current_agent_name = event.new_agent.name
    
    # 流结束前的兜底处理
    await flush_sub_agent_buffer(sub_agent_response_buffer)
```

**3. 智能体服务流式处理（agent_service.py）**

```python
class AgentService:
    @staticmethod
    async def process_query(context, user_input, flag=True) -> AsyncGenerator:
        """
        智能体查询处理的流式入口
        
        处理流程：
        1. 加载用户历史记忆
        2. 启动智能体流式运行
        3. 处理并转发事件流
        4. 保存最终结果到记忆系统
        5. 异常处理和重试机制
        """
        try:
            # 加载对话历史
            chat_history = session_manager.prepare_history(user_id, session_id, user_input)
            
            # 启动智能体流式运行
            result = Runner.run_streamed(
                max_turns=15,
                starting_agent=orchestrator_agent,
                input=chat_history,
                context=context,
                run_config=RunConfig(tracing_disabled=True)
            )
            
            # 处理并转发事件流
            async for chunk in process_stream_response_events(result):
                yield chunk
            
            # 保存最终结果
            if result.final_output:
                self._save_conversation_result(user_id, session_id, chat_history, result.final_output)
                
        except Exception as e:
            # 异常处理和重试
            yield from self._handle_processing_error(e, context, user_input, flag)
```

**4. FastAPI流式端点（routes.py）**：

@router.post("/api/query", summary="智能体对话接口")
async def query(request: TextMessageRequest):
    """
    智能体对话的流式API端点
    

```python
技术特点：
1. 使用StreamingResponse实现SSE流
2. 媒体类型设置为text/event-stream
3. 集成完整的错误处理
4. 支持对话上下文传递
"""
return StreamingResponse(
    AgentService.process_query(request.context, request.query),
    media_type="text/event-stream"
)
```
#### 2.完整代码实现

**1. 响应工具类（response_utils.py）**

```python
import uuid
import re
from datetime import datetime
from backend.app.presentation.schemas import MessageResponse, TextMessageBody, FinishMessageBody, StatusEnum, Metadata

def create_text_response(text, can_handle) -> MessageResponse:
    """
    创建文本类型的SSE响应消息
    
    参数:
        text: 消息文本内容
        can_handle: 消息类型（THINKING/PROCESS/ANSWER）
        
    返回:
        MessageResponse: 标准化SSE响应对象
    """
    message = TextMessageBody(text=text, type=can_handle)
    return MessageResponse(id=str(uuid.uuid4()),
                           content=message,
                           status=StatusEnum.IN_PROGRESS,
                           metadata=Metadata(createTime=str(datetime.now())))

def message_end_response(message_id: str = str(uuid.uuid4())):
    """
    创建流式传输结束信号
    
    返回:
        MessageResponse: 包含结束信号的响应对象
    """
    return MessageResponse(id=message_id,
                           content=FinishMessageBody(),
                           status=StatusEnum.FINISHED,
                           metadata=Metadata(createTime=str(datetime.now())))
```

**2. 流式事件处理器（stream_processor.py）**：

```python
from backend.app.infrastructure.logger import logger
from backend.app.presentation.schemas import TypeEnum
from backend.app.presentation.response_utils import create_text_response, message_end_response

# 兼容不同版本的OpenAI SDK
try:
    from openai.types.responses.response_stream_event import (
        ResponseTextDeltaEvent, 
        ResponseReasoningTextDeltaEvent,
        ResponseReasoningSummaryTextDeltaEvent,
    )
except ImportError:
    from openai.types.responses.response_stream_event import (
        ResponseTextDeltaEvent,
        ResponseReasoningSummaryTextDeltaEvent,
    )
    ResponseReasoningTextDeltaEvent = None

from agents.items import ToolCallItem, HandoffOutputItem

# 工具名称映射表（中文展示）
TOOL_NAME_MAPPING = {
    "query_knowledge": "查询知识库",
    "bailian_web_search": "联网搜索",
    "return_to_orchestrator": "返回调度中心",
    "transfer_to_technical_agent": "转接技术顾问智能体",
    "transfer_to_comprehensive_service_agent": "转接综合服务智能体",
    "search_mcp": "联网搜索", 
    "baidu_map_mcp": "百度地图查询"
}

async def process_stream_response_events(result):
    """
    处理智能体流式响应事件的主处理器
    
    返回:
        AsyncGenerator: SSE消息生成器
    """
    current_agent_name = "调度智能体"
    sub_agent_response_buffer = []
    sub_agent_return_count = 0

    async for event in result.stream_events():
        
        # ------------------------------------------------------------------
        # 1. 文本与推理生成事件处理
        # ------------------------------------------------------------------
        if event.type == "raw_response_event":
            yield from await handle_raw_response_event(
                event, current_agent_name, sub_agent_response_buffer
            )

        # ------------------------------------------------------------------
        # 2. 智能体交接与工具调用事件处理
        # ------------------------------------------------------------------
        elif event.type == "run_item_stream_event":
            yield from await handle_run_item_event(
                event, current_agent_name, sub_agent_response_buffer, sub_agent_return_count
            )

        # ------------------------------------------------------------------
        # 3. 智能体状态更新事件处理
        # ------------------------------------------------------------------
        elif event.type == "agent_updated_stream_event":
            current_agent_name = event.new_agent.name
            text = f"🤖当前智能体为: {current_agent_name}"
            logger.info(text)
            yield "data: " + create_text_response(text, TypeEnum.PROCESS).model_dump_json() + "\n\n"

    # ------------------------------------------------------------------
    # 4. 流结束前的兜底处理
    # ------------------------------------------------------------------
    if sub_agent_response_buffer:
        full_response = "".join(sub_agent_response_buffer)
        if full_response.strip():
            yield "data: " + create_text_response(full_response, TypeEnum.ANSWER).model_dump_json() + "\n\n"
            sub_agent_response_buffer = []

    # ------------------------------------------------------------------
    # 5. 发送结束信号
    # ------------------------------------------------------------------
    found_end = message_end_response()
    if found_end:
        yield "data: " + found_end.model_dump_json() + "\n\n"

async def handle_raw_response_event(event, current_agent_name, sub_agent_response_buffer):
    """
    处理原始响应事件
    
    处理逻辑:
    1. 文本增量事件：根据当前智能体类型决定消息类型
    2. 推理事件：始终为THINKING类型
    3. 推理摘要：始终为THINKING类型
    """
    if isinstance(event.data, ResponseTextDeltaEvent):
        delta_text = event.data.delta
        if not delta_text:
            return

        # 调度智能体：直接输出答案
        if current_agent_name == "调度智能体":
            # 先输出缓存的子智能体响应
            if sub_agent_response_buffer:
                full_response = "".join(sub_agent_response_buffer)
                if full_response.strip():
                    yield "data: " + create_text_response(full_response, TypeEnum.ANSWER).model_dump_json() + "\n\n"
                sub_agent_response_buffer.clear()

            yield "data: " + create_text_response(delta_text, TypeEnum.ANSWER).model_dump_json() + "\n\n"
        else:
            # 子智能体：缓存响应，等待合适时机输出
            sub_agent_response_buffer.append(delta_text)

    # 处理推理过程事件
    elif ResponseReasoningTextDeltaEvent and isinstance(event.data, ResponseReasoningTextDeltaEvent):
        if event.data.delta:
            yield "data: " + create_text_response(event.data.delta, TypeEnum.THINKING).model_dump_json() + "\n\n"
    
    # 处理推理摘要事件
    elif isinstance(event.data, ResponseReasoningSummaryTextDeltaEvent):
        if event.data.delta:
            yield "data: " + create_text_response(event.data.delta, TypeEnum.THINKING).model_dump_json() + "\n\n"

async def handle_run_item_event(event, current_agent_name, sub_agent_response_buffer, sub_agent_return_count):
    """
    处理运行项事件（交接、工具调用等）
    
    处理逻辑:
    1. 交接事件：更新当前智能体，发送交接消息
    2. 工具调用：根据工具类型决定处理方式
    3. 工具输出：记录日志，不向前端推送
    """
    # 处理智能体交接事件
    if hasattr(event, "name") and event.name == "handoff_occured":
        if isinstance(event.item, HandoffOutputItem) and event.item.type == "handoff_output_item":
            source_agent = event.item.source_agent.name
            target_agent = event.item.target_agent.name
            current_agent_name = target_agent
            
            text = f"🔄 正在协调智能体交接: {source_agent} ➡️ {target_agent}"
            yield "data: " + create_text_response(text, TypeEnum.PROCESS).model_dump_json() + "\n\n"
        else:
            logger.error("🔄智能体交接出现错误")

    # 处理工具调用事件
    elif hasattr(event, "name") and event.name == "tool_called":
        if isinstance(event.item, ToolCallItem) and event.item.type == "tool_call_item":
            tool_name = event.item.raw_item.name
            tool_args = event.item.raw_item.arguments

            # 调度智能体调用非返回工具时，输出缓存的子智能体响应
            if current_agent_name == "调度智能体" and tool_name != "return_to_orchestrator":
                if sub_agent_response_buffer:
                    full_response = "".join(sub_agent_response_buffer)
                    if full_response.strip():
                        yield "data: " + create_text_response(full_response, TypeEnum.ANSWER).model_dump_json() + "\n\n"
                    sub_agent_response_buffer.clear()

            # 处理返回调度中心工具
            if tool_name == "return_to_orchestrator":
                sub_agent_return_count += 1
                current_agent_name = "调度智能体"
                logger.info(f"Control return to Orchestrator (第 {sub_agent_return_count} 次)")
                
                display_name = TOOL_NAME_MAPPING.get(tool_name, tool_name)
                yield "data: " + create_text_response(display_name, TypeEnum.PROCESS).model_dump_json() + "\n\n"
            else:
                # 其他工具正常显示调用过程
                logger.info(f"Tool Call: {tool_name} Tool Args:{tool_args}")
                display_name = TOOL_NAME_MAPPING.get(tool_name, tool_name)
                yield "data: " + create_text_response(display_name, TypeEnum.PROCESS).model_dump_json() + "\n\n"

    # 处理工具输出事件（仅记录日志）
    elif hasattr(event, "name") and event.name == "tool_output":
        logger.info("Tool Output Received")
```

**3. 智能体服务（agent_service.py）**：

```python
import uuid
import re
import traceback
from typing import AsyncGenerator
from agents import Runner
from agents.run import RunConfig

from backend.app.infrastructure.logger import logger
from backend.app.presentation.response_utils import create_text_response
from backend.app.application.session_manager import session_manager
from backend.app.application.stream_processor import process_stream_response_events
from backend.app.presentation.schemas import TypeEnum
from backend.app.core_agents.orchestrator import orchestrator_agent

class AgentService:
    """
    智能体服务 - 流式通信引擎
    负责处理用户查询，管理智能体执行流程，实现流式响应
    """
    
    @staticmethod
    async def process_query(context, user_input, flag=True) -> AsyncGenerator:
        """
        处理用户查询的主入口
        
        参数:
            context: 用户上下文信息（包含user_id和session_id）
            user_input: 用户输入的查询文本
            flag: 重试标志（True表示允许重试）
            
        返回:
            AsyncGenerator: SSE消息生成器
        """
        # 提取用户ID和会话ID
        user_id = context.user_id
        session_id = context.session_id if context.session_id else str(uuid.uuid4())

        logger.info(f"开始处理新的用户请求 - 用户ID: {user_id}, 会话ID: {session_id}")
        
        # 准备聊天历史
        chat_history = session_manager.prepare_history(user_id, session_id, user_input)

        try:
            # 启动智能体流式运行
            logger.info("启动智能体运行流处理")
            result = Runner.run_streamed(
                max_turns=15,
                starting_agent=orchestrator_agent,
                input=chat_history,
                context=context,
                run_config=RunConfig(tracing_disabled=True)
            )

            # 处理并转发事件流
            async for chunk in process_stream_response_events(result):
                yield chunk

            # 保存最终结果到记忆系统
            if result.final_output:
                cleaned_output = re.sub(r'\n+', '\n', result.final_output)
                chat_history.append({"role": "assistant", "content": cleaned_output})
                session_manager.save_history(user_id, chat_history, session_id)

            logger.debug(f"智能体执行完成，最终智能体: {result.final_agent.name}")

        except Exception as e:
            # 异常处理和重试机制
            yield from AgentService._handle_processing_error(e, context, user_input, flag)
            
        finally:
            # 资源清理
            logger.info("请求处理完成，开始清理资源")
            if flag and 'user_id' in locals() and 'session_id' in locals():
                logger.info(f"保存用户会话历史 - 用户ID: {user_id}, 会话ID: {session_id}")

    @staticmethod
    async def _handle_processing_error(e, context, user_input, flag):
        """
        处理执行错误的统一方法
        
        处理逻辑:
        1. 记录错误日志
        2. 向客户端发送错误消息
        3. 根据标志决定是否重试
        """
        logger.error(f"AgentService.process_query执行出错: {str(e)}")
        logger.debug(f"异常详情: {traceback.format_exc()}")
        
        # 发送错误消息到客户端
        error_text = f"系统处理出错: {str(e)}"
        yield "data: " + create_text_response(error_text, TypeEnum.PROCESS).model_dump_json() + "\n\n"
        
        # 根据标志决定是否重试
        if flag:
            retry_text = "开始重试..."
            yield "data: " + create_text_response(retry_text, TypeEnum.PROCESS).model_dump_json() + "\n\n"
            
            # 递归调用进行重试
            async for item in AgentService.process_query(context, user_input, flag=False):
                yield item

    @staticmethod
    def _save_conversation_result(user_id, session_id, chat_history, final_output):
        """
        保存对话结果到记忆系统
        
        参数:
            user_id: 用户ID
            session_id: 会话ID
            chat_history: 聊天历史
            final_output: 最终输出结果
        """
        cleaned_output = re.sub(r'\n+', '\n', final_output)
        chat_history.append({"role": "assistant", "content": cleaned_output})
        session_manager.save_history(user_id, chat_history, session_id)
        logger.info(f"对话结果已保存 - 用户ID: {user_id}, 会话ID: {session_id}")
```

**4. API路由（routes.py）**：

```python
from fastapi import APIRouter
from starlette.responses import StreamingResponse
from backend.app.application.agent_service import AgentService
from backend.app.presentation.schemas import TextMessageRequest, UserSessionsRequest
from backend.app.application.session_manager import session_manager
from backend.app.infrastructure.logger import logger

router = APIRouter()

@router.post("/api/query", summary="智能体对话接口")
async def query(request: TextMessageRequest):
    """
    智能体对话的流式API端点
    
    请求参数:
        request: 包含查询文本和用户上下文
        
    返回:
        StreamingResponse: SSE流式响应
        
    技术特点:
        1. 支持流式传输，实时推送智能体思考过程
        2. 集成记忆管理，提供对话上下文
        3. 完善的错误处理和重试机制
    """
    context = request.context
    query_text = request.query
    
    logger.info(f"收到用户查询 - 用户ID: {context.user_id}, 会话ID: {context.session_id}")
    logger.debug(f"查询内容: {query_text}")
    
    return StreamingResponse(
        AgentService.process_query(context, query_text),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream; charset=utf-8',
            'X-Accel-Buffering': 'no'  # 禁用Nginx缓冲
        }
    )

@router.post("/api/user_sessions")
def get_user_sessions(request: UserSessionsRequest):
    """
    获取用户的所有会话记忆数据
    
    请求参数:
        request: 包含user_id的请求体
        
    返回:
        dict: 包含用户所有会话信息的JSON响应
    """
    logger.info("接收到获取用户会话请求")
    user_id = request.user_id
    logger.info(f"获取用户 {user_id} 的所有会话记忆数据")

    try:
        all_sessions = session_manager.get_all_sessions_memory(user_id)
        logger.debug(f"成功获取用户 {user_id} 的 {len(all_sessions)} 个会话")

        return {
            "success": True,
            "user_id": user_id,
            "total_sessions": len(all_sessions),
            "sessions": all_sessions
        }
    except Exception as e:
        logger.error(f"获取用户 {user_id} 的会话数据时出错: {str(e)}")
        return {
            "success": False,
            "user_id": user_id,
            "error": str(e)
        }
```

**功能总结**：

1. **分层架构设计**：
   - 事件源层：OpenAI Agents SDK事件流
   - 处理层：事件分类、消息转换、缓存管理
   - 传输层：SSE流式传输
   - 展示层：前端动态渲染
2. **智能缓存管理**：
   - 子智能体响应缓存，避免打断思考过程
   - 智能释放时机：交接、工具调用、流结束
   - 兜底机制确保内容完整性
3. **稳定可靠的连接管理**：
   - SSE连接生命周期管理
   - 自动重连机制
   - 错误处理和优雅降级
4. **丰富的事件类型支持**：
   - 思考过程（THINKING）
   - 处理过程（PROCESS）
   - 最终答案（ANSWER）
   - 结束信号（FINISHED）

这个流式通信系统实现了多智能体协同过程的实时可视化，让用户能够清晰看到智能体的思考过程、工具调用和交接流程，大大提升了交互体验和系统透明度。





## 5、总结

通过《多智能体开发（上）》和《多智能体开发（下）》两篇课件，我们完整地构建了一个基于OpenAI Agents SDK的多智能体客服系统。该系统具备以下特点：

1. **智能体分工协作**：调度智能体、技术顾问智能体、全能业务智能体各司其职，通过交接机制协同处理复杂任务。
2. **记忆管理**：支持多用户、多会话的对话历史存储和智能截断，实现上下文感知。
3. **流式交互**：通过SSE协议实时推送思考过程、工具调用和最终答案，提升用户体验。
4. **可扩展架构**：模块化设计，便于添加新的智能体、工具和MCP服务器。

至此，我们已经完成了一个完整的**多智能体后端系统**的搭建现在的系统不仅能"思考"（通过智能体），还能"记忆"（通过会话管理），并且能"表达"（通过流式响应）。接下来，你可以启动 `main.py`，使用前端或 Postman 进行测试，体验真正的多智能体协作流程！



## 6、整合于测试

在完成记忆管理和流式API构建后，我们需要对整个系统进行整合和测试，确保各个模块协同工作，达到预期的效果。



### 1 目标

将记忆管理、流式API与前端展示进行整合，进行端到端的测试，验证多智能体系统的完整功能，包括多轮对话记忆、流式响应和多跳任务处理。

### 2 需求分析

1. **系统整合需求**：
   - **模块协同**：确保记忆管理、智能体服务、流式API和前端展示层无缝集成
   - **数据流一致性**：验证对话历史从保存、加载到传递给智能体的完整流程
   - **错误处理链**：确保系统级错误能够正确传递和处理，提供友好的用户反馈
2. **功能测试需求**：
   - **单轮对话测试**：验证基本问答功能，包括意图识别和智能体分发
   - **多轮对话测试**：验证记忆管理系统的有效性，确保上下文连贯性
   - **复杂任务测试**：验证多智能体协作处理多步骤任务的能力

### 3 实现流程

1. **系统环境准备**：

   - 配置开发环境，安装所有依赖包
   - 设置环境变量和配置文件
   - 初始化数据库和外部服务连接

2. **端到端测试执行**：

   - 启动后端服务，验证是否成功
   - 执行单轮对话测试，验证基础功能
   - 执行多轮对话测试，验证记忆管理
   - 执行多跳任务测试，验证多智能体协作

   

## 7、项目启动指南

### 1、环境准备

#### 1. 系统要求

- **Python版本**: 3.10或更高版本
- **操作系统**:
  - Windows 10/11
- **内存**: 至少4GB RAM
- **磁盘空间**: 至少2GB可用空间
- **网络**: 稳定的互联网连接（用于调用外部API和MCP服务）

#### 2. 依赖安装

```python

# 1. 创建虚拟环境（推荐）
python -m venv .venv

# Windows激活
.venv\Scripts\activate


# 3. 安装依赖包
pip install -r requirements.txt
或者
pip  install -e .

```

#### 3. 环境变量配置

```python
# 1. 复制环境变量模板
cp .env .env.example 

# 2. 编辑.env.example文件，填入必要的配置
# 使用文本编辑器打开.env.example文件，根据以下说明填写配置
```

**.env文件配置说明**：

```python

# LLM配置 硅基流动
SF_API_KEY=sk-vnxijjgodhcjisacoilneb****
SF_BASE_URL=https://api.siliconflow.cn/v1
SUB_MODEL_NAME=Qwen/Qwen3-32B

# LLM配置 百链
AL_BAILIAN_API_KEY=sk-26d57c96***
AL_BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MAIN_MODEL_NAME=qwen3-max


# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=its
MYSQL_CHARSET=utf8mb4
MYSQL_CONNECT_TIMEOUT=10
MYSQL_MAX_CONNECTIONS=5

# MCP配置 (百炼通用搜索)
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/sse
DASHSCOPE_API_KEY=sk-26d57c968c364e7bb14f1fc350d4bff0
# MCP配置 (百度地图)
BAIDUMAP_AK=kTKdTNRLndgbvBpYngbizpBGX2eBVJIj

# 知识库配置
KNOWLEDGE_BASE_URL=http://127.0.0.1:8001


# 测试使用
; OPENAI_API_KEY=sk-3fNNVrOHy9YbLm87IQ***
; OPENAI_BASE_URL=https://api.openai-proxy.org/v1
; OPENAI_MODEL_NAME=gpt-5.2-pro
```

#### 4.第三方服务的官网

以下是本项目中使用到的第三方服务的官网地址，您需要在这些平台上注册账号并获取相应的API密钥：

1. **硅基流动 (Silicon Flow)**
   - 官网：https://cloud.siliconflow.cn/
   - 用途：提供轻量模型，用于调度智能体（SUB_MODEL_NAME）
   - 注意：注册后创建API Key，并选择Qwen/Qwen3-32B模型
   - 文档：https://siliconflow.cn/zh-cn/docs
2. **阿里云百炼 (Alibaba Bailian)**
   - 官网：https://bailian.console.aliyun.com/
   - 用途：提供主力模型，用于技术顾问智能体和全能业务智能体（MAIN_MODEL_NAME）
   - 注意：注册阿里云账号，开通百炼服务，获取API Key
   - 文档：https://help.aliyun.com/zh/bailian/
3. **达摩院DashScope**
   - 官网：https://dashscope.aliyuncs.com/
   - 用途：提供通用搜索MCP服务
   - 注意：在DashScope控制台创建API Key，并开通WebSearch MCP服务
   - 文档：https://help.aliyun.com/zh/dashscope/
4. **百度地图开放平台**
   - 官网：https://lbsyun.baidu.com/
   - 用途：提供百度地图MCP服务，用于地点搜索、导航等
   - 注意：注册百度地图开放平台账号，创建应用，获取访问应用（AK）
   - 文档：https://lbsyun.baidu.com/index.php?title=webapi
5. **OpenAI (可选)**
   - 官网：https://openai.com/
   - 用途：备用模型，如果使用OpenAI模型需要配置
   - 注意：注册OpenAI账号，获取API Key
   - 文档：https://platform.openai.com/docs
6. **Python虚拟环境 (venv)**
   - 文档：https://docs.python.org/3/library/venv.html
   - 用途：创建独立的Python运行环境，避免依赖冲突
7. **FastAPI框架**
   - 官网：https://fastapi.tiangolo.com/
   - 文档：https://fastapi.tiangolo.com/zh/
   - 用途：构建Web API服务
8. **OpenAI Agents SDK**
   - 官网：https://openai.github.io/openai-agents-python/
   - 文档：https://github.com/openai/openai-agents-python
   - 用途：构建多智能体系统的核心框架
9. **PyMySQL (MySQL驱动)**
   - 官网：https://pymysql.readthedocs.io/
   - 用途：Python连接MySQL数据库
10. **dbutils (数据库连接池)**
    - 文档：https://webwareforpython.github.io/DBUtils/
    - 用途：管理数据库连接池，提高性能
11. **pydantic (数据验证)**
    - 官网：https://docs.pydantic.dev/
    - 用途：数据验证和设置管理
12. **uvicorn (ASGI服务器)**
    - 官网：https://www.uvicorn.org/
    - 用途：运行FastAPI应用
13. **python-dotenv (环境变量管理)**
    - 官网：https://saurabh-kumar.com/python-dotenv/
    - 用途：从.env文件加载环境变量



### 2、 服务启动与验证

#### 1. 启动后端服务

```python
# 开发环境启动（带热重载）
cd backend/app
uvicorn main:app --reload --host 0.0.0.0 --port 8000

```

#### 2. 验证服务运行

```python
# 健康检查
curl http://localhost:8000/health

# 预期响应：
# {
#   "status": "healthy",
#   "timestamp": "2025-01-15T10:30:00.123456",
#   "service": "ITS Multi-Agent System",
#   "version": "2.0.0"
# }

# 查看API文档
# 浏览器访问：http://localhost:8000/docs
```

### 3、功能测试与验证（可选）

#### 1. 基本功能测试

```python
# 测试技术问题
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "电脑蓝屏怎么办？",
    "context": {
      "user_id": "test_user_001",
      "session_id": "test_session_001"
    }
  }'

# 测试服务站查询
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "附近有没有小米服务站？",
    "context": {
      "user_id": "test_user_002",
      "session_id": "test_session_002"
    }
  }'
```

#### 2. 多轮对话测试

```python
# 创建测试脚本 test_conversation.sh
#!/bin/bash

USER_ID="test_user_$(date +%s)"
SESSION_ID="test_session"

echo "测试用户ID: $USER_ID"

# 第一轮对话
echo "=== 第一轮对话 ==="
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"我的电脑是戴尔XPS 13\",
    \"context\": {
      \"user_id\": \"$USER_ID\",
      \"session_id\": \"$SESSION_ID\"
    }
  }" 2>/dev/null | grep "data:" | tail -1

sleep 2

# 第二轮对话
echo "=== 第二轮对话 ==="
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"我刚才说的电脑型号是什么？\",
    \"context\": {
      \"user_id\": \"$USER_ID\",
      \"session_id\": \"$SESSION_ID\"
    }
  }" 2>/dev/null | grep "data:" | tail -1
```



### 4、 故障排除

#### 常见问题1: MCP连接失败

**症状**: 日志中出现"MCP连接建立失败"或"Tool call failed"
**解决方案**:

```python
# 检查MCP配置
1. 验证.env文件中的API密钥和URL
2. 检查网络连接，确保可以访问外部API
3. 查看MCP服务商的状态页面，确认服务正常
4. 增加超时时间配置
```



#### 常见问题2: 数据库连接失败

**症状**: "数据库查询失败"或"Connection refused"
**解决方案**:

```python
# 检查MySQL服务
1. 确保MySQL服务正在运行: systemctl status mysql
2. 验证连接参数: mysql -u root -p -h localhost
3. 检查防火墙设置: sudo ufw allow 3306
4. 增加连接池大小（在settings.py中调整MYSQL_MAX_CONNECTIONS）
```



#### 常见问题3: 模型API调用失败

**症状**: "模型调用失败"或"Invalid API key"
**解决方案**:

```python
# 检查模型配置
1. 验证API密钥是否正确且有余额
2. 检查Base URL是否正确
3. 确认模型名称是否支持
4. 查看API提供商的速率限制
```



#### 常见问题4: 流式响应中断

**症状**: SSE连接意外断开或响应不完整
**解决方案**:

```python
# 调整流式配置
1. 增加SSE超时时间
2. 检查前端EventSource的重连机制
3. 验证网络稳定性，特别是代理设置
```

#### 常见问题5: 模型回复不稳定

**症状**: 模型回复质量参差不齐，有时准确有时错误，回复长度和格式不一致，或者在不同时间相同问题得到差异较大的答案,这属于**正常**。

**如果想调试，可以试下下面解决方案**:

```python
# 模型稳定性优化配置
1. 调整模型参数设置：
   - 降低temperature参数（减少随机性）：推荐值0.3-0.5
   - 设置top_p参数（控制采样范围）：推荐值0.8-0.9
   - 设置max_tokens参数（控制输出长度）：根据场景调整
   - 启用stream_options参数（控制流式输出）：设置"include_usage": True

2. 优化智能体提示词设计：
   - 明确指令边界：在每个智能体的instructions中明确职责范围
   - 添加示例回复：在prompt中添加期望的回答格式示例
   - 强化拒绝规则：明确哪些问题不应该回答，如何拒绝
   - 设置思考步骤：引导模型分步骤思考，提高推理稳定性

3. 实施输出标准化：
   - 添加后处理逻辑：对模型输出进行清洗和格式化
   - 设置回复模板：为不同场景定义标准回复结构
   - 实现内容验证：检查回复是否符合预期格式和内容要求

4. 启用模型路由和降级：
   - 多模型备选：配置多个模型作为备选，主模型失败时自动切换
```

### 8、升级与扩展

#### 1.问题说明

**前端**：目前思考区域会分为两部分展示效果不太好，这块我在讲课之前会重新修改一下。

**后端**：具体代码结构大家可以自行调整，有的地方可能还是有些冗余。

讲完第一班之后，会给大家一个前端后端最终版本。



#### 2. 添加新智能体

```python
# 1. 在core_agents/目录下创建新智能体
# 2. 在orchestrator.py中添加handoff配置
# 3. 更新提示词文件
# 4. 测试新智能体功能
```

#### 3. 添加新工具

```python
# 1. 在infrastructure/tools/目录下创建新工具
# 2. 使用@function_tool装饰器
# 3. 在相应的智能体中注册工具
# 4. 更新工具映射表（如有前端展示需要）
```

