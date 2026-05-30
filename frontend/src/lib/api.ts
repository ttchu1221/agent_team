export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  task_id?: string;
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
