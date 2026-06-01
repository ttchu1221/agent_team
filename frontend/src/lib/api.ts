export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  task_id?: string;
  agent_type?: string;
}

export interface ChatResponse {
  reply: string;
  task_id: string | null;
  session_id: string;
}

export interface TaskResponse {
  task_id: string;
  status: string;
  intent: string | null;
  result: string | null;
  error: string | null;
  created_at: string;
  updated_at: string | null;
}

const API_BASE = "/api/v1";

export async function sendMessage(
  message: string,
  sessionId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(error.detail || "请求失败");
  }

  return res.json();
}

export async function getTasks(limit = 20): Promise<{ tasks: TaskResponse[]; total: number }> {
  const res = await fetch(`${API_BASE}/tasks?limit=${limit}`);
  if (!res.ok) throw new Error("获取任务失败");
  return res.json();
}

export async function getTask(taskId: string): Promise<TaskResponse> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}`);
  if (!res.ok) throw new Error("获取任务详情失败");
  return res.json();
}

export async function retryTask(taskId: string): Promise<{ task_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/retry`, { method: "POST" });
  if (!res.ok) throw new Error("重试任务失败");
  return res.json();
}

export async function deleteTask(taskId: string): Promise<{ detail: string; task_id: string }> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("删除任务失败");
  return res.json();
}

// ---------- 流式聊天 ----------

export interface StreamChatEvent {
  type: "session" | "task" | "delta" | "done" | "error";
  content?: string;
  session_id?: string;
  task_id?: string;
  agent_type?: string;
}

/**
 * 流式发送消息 - 返回 AsyncGenerator，逐块接收回复
 */
export async function* sendMessageStream(
  message: string,
  sessionId?: string
): AsyncGenerator<StreamChatEvent> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(error.detail || "请求失败");
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          yield JSON.parse(line.slice(6)) as StreamChatEvent;
        } catch {
          // skip malformed JSON
        }
      }
    }
  }

  // 处理剩余 buffer
  if (buffer.startsWith("data: ")) {
    try {
      yield JSON.parse(buffer.slice(6)) as StreamChatEvent;
    } catch {
      // skip
    }
  }
}
