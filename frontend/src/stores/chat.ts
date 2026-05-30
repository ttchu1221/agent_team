import { create } from "zustand";
import type { ChatMessage } from "@/lib/api";

interface ChatState {
  messages: ChatMessage[];
  sessionId: string | null;
  isLoading: boolean;
  addMessage: (msg: ChatMessage) => void;
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

  setSessionId: (id) => set({ sessionId: id }),

  setLoading: (loading) => set({ isLoading: loading }),

  clearMessages: () => set({ messages: [], sessionId: null }),
}));
