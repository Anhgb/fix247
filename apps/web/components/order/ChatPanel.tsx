"use client";

import * as React from "react";
import { Send, Image as ImageIcon, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/Button";

export interface ChatMessageItem {
  id: string;
  sender_id: string;
  sender_role: string;
  content: string;
  media_url?: string | null;
  created_at: string;
}

interface ChatPanelProps {
  orderId: string;
  messages: ChatMessageItem[];
  currentUserId?: string;
  currentUserRole?: string;
  onSendMessage: (content: string, mediaUrl?: string) => Promise<void>;
}

export function ChatPanel({
  orderId,
  messages,
  currentUserId,
  currentUserRole,
  onSendMessage,
}: ChatPanelProps) {
  const [inputText, setInputText] = React.useState("");
  const [isSending, setIsSending] = React.useState(false);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || isSending) return;

    setIsSending(true);
    try {
      await onSendMessage(text);
      setInputText("");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="flex flex-col h-80 bg-surface-card border border-surface-border rounded-2xl overflow-hidden shadow-lg">
      {/* Header */}
      <div className="px-4 py-2.5 bg-surface-elevated/70 border-b border-surface-border flex items-center justify-between">
        <span className="text-xs font-bold text-white uppercase tracking-wider">
          Trao đổi trong đơn hàng
        </span>
        <span className="text-[11px] text-emerald-400 flex items-center gap-1">
          <ShieldAlert className="w-3.5 h-3.5" />
          Ẩn số điện thoại (Bảo mật)
        </span>
      </div>

      {/* Message list */}
      <div className="flex-1 p-3 overflow-y-auto space-y-2.5">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-slate-500">
            Chưa có tin nhắn nào. Bạn có thể nhắn tin trao đổi với thợ tại đây.
          </div>
        ) : (
          messages.map((m) => {
            const isMe = currentUserId
              ? m.sender_id === currentUserId
              : m.sender_role === currentUserRole;

            return (
              <div
                key={m.id}
                className={`flex flex-col ${isMe ? "items-end" : "items-start"}`}
              >
                <span className="text-[10px] text-slate-400 mb-0.5 px-1">
                  {isMe ? "Bạn" : m.sender_role === "technician" ? "Thợ sửa chữa" : "Khách hàng"}
                </span>
                <div
                  className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed ${
                    isMe
                      ? "bg-brand-600 text-white rounded-tr-none shadow-md"
                      : "bg-surface-elevated text-slate-200 rounded-tl-none border border-surface-border"
                  }`}
                >
                  <p>{m.content}</p>
                  {m.media_url && (
                    <img
                      src={m.media_url}
                      alt="Ảnh đính kèm"
                      className="mt-2 rounded-lg max-h-40 object-cover"
                    />
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="p-2.5 bg-surface-elevated/50 border-t border-surface-border flex items-center gap-2"
      >
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Nhập tin nhắn..."
          className="flex-1 bg-surface-card border border-surface-border rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
        />
        <Button
          type="submit"
          disabled={!inputText.trim() || isSending}
          size="sm"
          className="h-10 px-4 min-w-[48px]"
        >
          <Send className="w-4 h-4" />
        </Button>
      </form>
    </div>
  );
}
