"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStore } from "@/stores/chat";
import { sendMessageStream } from "@/lib/api";
import { Send, Bot, User, Loader2, Trash2, StopCircle } from "lucide-react";
import MarkdownRenderer from "./MarkdownRenderer";
import { getAgentConfig } from "@/lib/agentConfig";

export default function ChatPanel() {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const { messages, sessionId, isLoading, addMessage, updateLastAssistant, setSessionId, setLoading, clearMessages } =
    useChatStore();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    addMessage({ role: "user", content: text });
    setInput("");
    setLoading(true);

    // 先插入一条空的 assistant 消息，用于流式填充
    addMessage({ role: "assistant", content: "" });

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      let currentSessionId = sessionId;
      let taskId: string | undefined;
      let agentType: string | undefined;
      let fullContent = "";

      for await (const event of sendMessageStream(text, currentSessionId || undefined)) {
        if (controller.signal.aborted) break;

        switch (event.type) {
          case "session":
            if (event.session_id && !currentSessionId) {
              currentSessionId = event.session_id;
              setSessionId(event.session_id);
            }
            break;
          case "task":
            taskId = event.task_id;
            agentType = event.agent_type;
            break;
          case "delta":
            fullContent += event.content || "";
            updateLastAssistant(fullContent, taskId, agentType);
            break;
          case "done":
            break;
          case "error":
            updateLastAssistant(`❌ ${event.content}`);
            break;
        }
      }
    } catch (err: unknown) {
      console.error("Chat stream failed:", err);
      const errorMsg = err instanceof Error ? err.message : "请求失败";
      updateLastAssistant(`❌ ${errorMsg}`);
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Bot className="w-6 h-6 text-blue-500" />
          <h1 className="text-lg font-semibold">AI 助理团队</h1>
        </div>
        <button
          onClick={clearMessages}
          className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
          title="清空对话"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-20">
            <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg">你好！我是你的 AI 助理团队</p>
            <p className="text-sm mt-2">试试说：帮我分析一个职位描述 / 整理我的待办事项</p>
          </div>
        )}

        {messages.map((msg, i) => {
          const agentConfig = getAgentConfig(msg.agent_type);
          const isAgentTask = msg.role === "assistant" && msg.agent_type;

          return (
            <div
              key={i}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-lg ${
                  isAgentTask 
                    ? `${agentConfig.bgColor} ${agentConfig.borderColor} border`
                    : "bg-blue-500"
                }`}>
                  {isAgentTask ? (
                    <span>{agentConfig.icon}</span>
                  ) : (
                    <Bot className="w-4 h-4 text-white" />
                  )}
                </div>
              )}
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-blue-500 text-white rounded-br-md"
                    : isAgentTask
                      ? `${agentConfig.bgColor} ${agentConfig.borderColor} border rounded-bl-md`
                      : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-md"
                }`}
              >
                {/* Agent 标签 */}
                {isAgentTask && (
                  <div className={`text-xs font-medium mb-2 ${agentConfig.color}`}>
                    {agentConfig.name}
                  </div>
                )}
                
                {/* 内容区域 */}
                {msg.role === "user" ? (
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                ) : isAgentTask ? (
                  <MarkdownRenderer content={msg.content} />
                ) : (
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                )}
                
                {/* 流式输出中的光标 */}
                {msg.role === "assistant" && isLoading && i === messages.length - 1 && msg.content && (
                  <span className="inline-block w-0.5 h-4 bg-blue-500 ml-0.5 animate-pulse align-text-bottom" />
                )}
              </div>
              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-gray-600 dark:text-gray-300" />
                </div>
              )}
            </div>
          );
        })}

        {/* 加载中（等待首个 token 时显示 spinner） */}
        {isLoading && messages.length > 0 && messages[messages.length - 1].role === "assistant" && !messages[messages.length - 1].content && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-bl-md px-4 py-3">
              <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-3 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
            rows={1}
            className="flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
          />
          {isLoading ? (
            <button
              onClick={handleStop}
              className="p-3 rounded-xl bg-red-500 text-white hover:bg-red-600 transition-colors"
              title="停止生成"
            >
              <StopCircle className="w-5 h-5" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="p-3 rounded-xl bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
