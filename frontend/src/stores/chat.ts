import { create } from "zustand";
import type { ChatMessage } from "@/lib/api";

interface ChatState {
  messages: ChatMessage[];
  sessionId: string | null;
  isLoading: boolean;
  addMessage: (msg: ChatMessage) => void;
  updateLastAssistant: (content: string, taskId?: string, agentType?: string) => void;
  setSessionId: (id: string) => void;
  setLoading: (loading: boolean) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  sessionId: null,
  isLoading: false,

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  updateLastAssistant: (content, taskId, agentType) =>
    set((state) => {
      const msgs = [...state.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "assistant") {
          msgs[i] = { 
            ...msgs[i], 
            content, 
            task_id: taskId || msgs[i].task_id,
            agent_type: agentType || msgs[i].agent_type
          };
          break;
        }
      }
      return { messages: msgs };
    }),

  setSessionId: (id) => set({ sessionId: id }),

  setLoading: (loading) => set({ isLoading: loading }),

  clearMessages: () => set({ messages: [], sessionId: null }),
}));
