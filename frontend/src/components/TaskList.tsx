"use client";

import { useEffect, useState } from "react";
import { getTasks, deleteTask, type TaskResponse } from "@/lib/api";
import {
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  RefreshCw,
  ListTodo,
  Trash2,
  X,
  Copy,
  Check,
} from "lucide-react";

const statusConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  pending: { icon: <Clock className="w-4 h-4" />, color: "text-gray-400", label: "待处理" },
  queued: { icon: <Clock className="w-4 h-4" />, color: "text-yellow-500", label: "排队中" },
  running: { icon: <Loader2 className="w-4 h-4 animate-spin" />, color: "text-blue-500", label: "执行中" },
  completed: { icon: <CheckCircle2 className="w-4 h-4" />, color: "text-green-500", label: "已完成" },
  failed: { icon: <XCircle className="w-4 h-4" />, color: "text-red-500", label: "失败" },
  retrying: { icon: <RefreshCw className="w-4 h-4 animate-spin" />, color: "text-orange-500", label: "重试中" },
};

export default function TaskList() {
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const data = await getTasks();
      setTasks(data.tasks);
    } catch (err) {
      console.error("Failed to fetch tasks:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (taskId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("确定要删除这个任务吗？")) return;
    setDeletingId(taskId);
    try {
      await deleteTask(taskId);
      setTasks((prev) => prev.filter((t) => t.task_id !== taskId));
      if (selectedTask?.task_id === taskId) setSelectedTask(null);
    } catch (err) {
      console.error("Failed to delete task:", err);
      alert("删除失败，请重试");
    } finally {
      setDeletingId(null);
    }
  };

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <ListTodo className="w-5 h-5 text-blue-500" />
          <h2 className="text-lg font-semibold">任务列表</h2>
          {tasks.length > 0 && (
            <span className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-full">
              {tasks.length}
            </span>
          )}
        </div>
        <button
          onClick={fetchTasks}
          className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading && tasks.length === 0 ? (
          <div className="text-center text-gray-400 mt-10">
            <Loader2 className="w-8 h-8 mx-auto animate-spin" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center text-gray-400 mt-10">
            <ListTodo className="w-10 h-10 mx-auto mb-3 opacity-50" />
            <p>暂无任务</p>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => {
              const cfg = statusConfig[task.status] || statusConfig.pending;
              const isClickable = task.status === "completed" || task.status === "failed";
              return (
                <div
                  key={task.task_id}
                  onClick={() => isClickable && setSelectedTask(task)}
                  className={`group p-4 rounded-xl border border-gray-200 dark:border-gray-700 transition-colors ${
                    isClickable
                      ? "cursor-pointer hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50/50 dark:hover:bg-blue-900/10"
                      : ""
                  } ${selectedTask?.task_id === task.task_id ? "border-blue-400 dark:border-blue-500 bg-blue-50/50 dark:bg-blue-900/10" : ""}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-400 font-mono">{task.task_id.slice(0, 12)}...</span>
                    <div className="flex items-center gap-2">
                      <span className={`flex items-center gap-1 text-xs font-medium ${cfg.color}`}>
                        {cfg.icon} {cfg.label}
                      </span>
                      <button
                        onClick={(e) => handleDelete(task.task_id, e)}
                        disabled={deletingId === task.task_id}
                        className="p-1 text-gray-300 hover:text-red-500 rounded transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50"
                        title="删除任务"
                      >
                        {deletingId === task.task_id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                    {task.intent || "无描述"}
                  </p>
                  {isClickable && (
                    <p className="text-xs text-blue-400 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      点击查看详情 →
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 任务详情弹窗 */}
      {selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setSelectedTask(null)}>
          <div
            className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-[700px] max-h-[80vh] flex flex-col border border-gray-200 dark:border-gray-700"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 弹窗头部 */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                {statusConfig[selectedTask.status]?.icon}
                <h3 className="text-lg font-semibold">任务详情</h3>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusConfig[selectedTask.status]?.color} bg-gray-100 dark:bg-gray-800`}>
                  {statusConfig[selectedTask.status]?.label}
                </span>
              </div>
              <button
                onClick={() => setSelectedTask(null)}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* 弹窗内容 */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {/* 任务描述 */}
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">任务描述</label>
                <p className="mt-1 text-sm text-gray-800 dark:text-gray-200">{selectedTask.intent || "无描述"}</p>
              </div>

              {/* 任务 ID */}
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">任务 ID</label>
                <p className="mt-1 text-xs font-mono text-gray-500">{selectedTask.task_id}</p>
              </div>

              {/* 时间信息 */}
              <div className="flex gap-6">
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">创建时间</label>
                  <p className="mt-1 text-xs text-gray-500">{new Date(selectedTask.created_at).toLocaleString("zh-CN")}</p>
                </div>
                {selectedTask.updated_at && (
                  <div>
                    <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">更新时间</label>
                    <p className="mt-1 text-xs text-gray-500">{new Date(selectedTask.updated_at).toLocaleString("zh-CN")}</p>
                  </div>
                )}
              </div>

              {/* 结果 / 错误 */}
              {(selectedTask.result || selectedTask.error) && (
                <div>
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                      {selectedTask.status === "failed" ? "错误信息" : "执行结果"}
                    </label>
                    <button
                      onClick={() => handleCopy(selectedTask.result || selectedTask.error || "")}
                      className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                    >
                      {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                      {copied ? "已复制" : "复制"}
                    </button>
                  </div>
                  <div className="mt-2 p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
                    <pre className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap font-sans leading-relaxed">
                      {selectedTask.status === "failed" ? selectedTask.error : selectedTask.result}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
