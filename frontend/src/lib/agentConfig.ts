// Agent 类型配置 - 定义不同 Agent 的显示样式
export const agentConfigs: Record<string, {
  name: string;
  icon: string;
  color: string;
  bgColor: string;
  borderColor: string;
  description: string;
}> = {
  research: {
    name: "科研助手",
    icon: "🔬",
    color: "text-purple-600",
    bgColor: "bg-purple-50 dark:bg-purple-900/20",
    borderColor: "border-purple-200 dark:border-purple-800",
    description: "论文搜索、学术分析、文献综述",
  },
  career: {
    name: "职业顾问",
    icon: "💼",
    color: "text-blue-600",
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    borderColor: "border-blue-200 dark:border-blue-800",
    description: "简历优化、面试准备、职业规划",
  },
  finance: {
    name: "财务助手",
    icon: "💰",
    color: "text-green-600",
    bgColor: "bg-green-50 dark:bg-green-900/20",
    borderColor: "border-green-200 dark:border-green-800",
    description: "支出分析、预算管理、投资建议",
  },
  travel: {
    name: "旅行规划",
    icon: "✈️",
    color: "text-orange-600",
    bgColor: "bg-orange-50 dark:bg-orange-900/20",
    borderColor: "border-orange-200 dark:border-orange-800",
    description: "行程规划、住宿推荐、交通方案",
  },
  health: {
    name: "健康顾问",
    icon: "❤️",
    color: "text-red-600",
    bgColor: "bg-red-50 dark:bg-red-900/20",
    borderColor: "border-red-200 dark:border-red-800",
    description: "健康记录、运动计划、饮食建议",
  },
  study: {
    name: "学习助手",
    icon: "📚",
    color: "text-indigo-600",
    bgColor: "bg-indigo-50 dark:bg-indigo-900/20",
    borderColor: "border-indigo-200 dark:border-indigo-800",
    description: "学习计划、知识整理、进度追踪",
  },
  life: {
    name: "生活管家",
    icon: "🏠",
    color: "text-teal-600",
    bgColor: "bg-teal-50 dark:bg-teal-900/20",
    borderColor: "border-teal-200 dark:border-teal-800",
    description: "日程管理、待办事项、提醒设置",
  },
};

// 默认配置（用于普通对话）
export const defaultAgentConfig = {
  name: "AI 助手",
  icon: "🤖",
  color: "text-gray-600",
  bgColor: "bg-gray-50 dark:bg-gray-900/20",
  borderColor: "border-gray-200 dark:border-gray-800",
  description: "通用对话助手",
};

export function getAgentConfig(agentType?: string) {
  if (!agentType) return defaultAgentConfig;
  return agentConfigs[agentType] || defaultAgentConfig;
}
