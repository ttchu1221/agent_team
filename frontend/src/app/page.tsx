"use client";

import { useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import TaskList from "@/components/TaskList";
import CinnamorollPet from "@/components/CinnamorollPet";
import { MessageSquare, ListTodo, Briefcase, FlaskConical, Home } from "lucide-react";

const navItems = [
  { id: "chat", icon: MessageSquare, label: "对话" },
  { id: "tasks", icon: ListTodo, label: "任务" },
  { id: "career", icon: Briefcase, label: "求职" },
  { id: "research", icon: FlaskConical, label: "科研" },
  { id: "life", icon: Home, label: "生活" },
];

export default function HomePage() {
  const [activeTab, setActiveTab] = useState("chat");

  return (
    <div className="flex h-screen bg-white dark:bg-gray-950">
      {/* Sidebar */}
      <nav className="w-16 border-r border-gray-200 dark:border-gray-800 flex flex-col items-center py-4 gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-12 h-12 rounded-xl flex flex-col items-center justify-center gap-0.5 transition-colors ${
                isActive
                  ? "bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                  : "text-gray-400 hover:text-gray-600 hover:bg-gray-50 dark:hover:bg-gray-900"
              }`}
              title={item.label}
            >
              <Icon className="w-5 h-5" />
              <span className="text-[10px]">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Main Content */}
      <main className="flex-1 flex">
        {activeTab === "chat" && (
          <div className="flex-1 flex">
            <div className="flex-1">
              <ChatPanel />
            </div>
            <div className="w-80 border-l border-gray-200 dark:border-gray-800 hidden lg:block">
              <TaskList />
            </div>
          </div>
        )}

        {activeTab === "tasks" && (
          <div className="flex-1 max-w-3xl mx-auto">
            <TaskList />
          </div>
        )}

        {(activeTab === "career" || activeTab === "research" || activeTab === "life") && (
          <div className="flex-1">
            <ChatPanel />
          </div>
        )}
      </main>

      {/* 玉桂狗宠物 */}
      <CinnamorollPet />
    </div>
  );
}
