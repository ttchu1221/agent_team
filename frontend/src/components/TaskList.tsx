"use client";

import { useEffect, useState } from "react";
import { getTasks, type TaskResponse } from "@/lib/api";
import {
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  RefreshCw,
  ListTodo,
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
              return (
                <div
                  key={task.task_id}
                  className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-400 font-mono">{task.task_id.slice(0, 12)}...</span>
                    <span className={`flex items-center gap-1 text-xs font-medium ${cfg.color}`}>
                      {cfg.icon} {cfg.label}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                    {task.intent || "无描述"}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
