"use client";

import { useState, useRef, useEffect } from "react";
import { postQuery, type Citation, type QueryResponse } from "@/lib/api";
import styles from "./page.module.css";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  timestamp: Date;
}

const WELCOME_SUGGESTIONS = [
  "What are the key findings in the executive summary?",
  "Compare the revenue figures across all documents",
  "What are the main risk factors mentioned?",
  "Summarize the legal obligations in the contract",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [selectedCitations, setSelectedCitations] = useState<Citation[] | null>(null);
  const [activeMsgId, setActiveMsgId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [input]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res: QueryResponse = await postQuery({ question: text, session_id: sessionId });
      setSessionId(res.session_id);
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.answer,
        citations: res.citations,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (res.citations?.length) {
        setSelectedCitations(res.citations);
        setActiveMsgId(assistantMsg.id);
      }
    } catch {
      const errMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "I encountered an error processing your request. Please check that your backend is running and try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const showCitations = (msg: Message) => {
    if (msg.citations?.length) {
      setSelectedCitations(msg.citations);
      setActiveMsgId(msg.id);
    }
  };

  return (
    <div className={styles.layout}>
      {/* Chat column */}
      <div className={styles.chatCol}>
        <div className={styles.chatHeader}>
          <div>
            <h1 className={`heading-lg ${styles.chatTitle}`}>Ask Questions</h1>
            <p className={styles.chatSub}>Query your documents with natural language</p>
          </div>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => {
              setMessages([]);
              setSelectedCitations(null);
              setSessionId(undefined);
            }}
            title="New conversation"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.51"/>
            </svg>
            New chat
          </button>
        </div>

        <div className={styles.messages}>
          {messages.length === 0 && (
            <div className={styles.welcome}>
              <div className={styles.welcomeIcon}>◎</div>
              <h2 className={styles.welcomeTitle}>Ask anything about your documents</h2>
              <p className={styles.welcomeSub}>
                I'll search across all your uploaded documents and provide precise answers with source citations.
              </p>
              <div className={styles.suggestions}>
                {WELCOME_SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    className={styles.suggestion}
                    onClick={() => { setInput(s); textareaRef.current?.focus(); }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`${styles.message} ${styles[msg.role]} ${activeMsgId === msg.id ? styles.active : ""}`}
            >
              {msg.role === "assistant" && (
                <div className={styles.msgAvatar}>⬡</div>
              )}
              <div className={styles.msgBody}>
                <div className={styles.msgContent}>{msg.content}</div>
                {msg.role === "assistant" && msg.citations && msg.citations.length > 0 && (
                  <div className={styles.msgCitations}>
                    <button
                      className={styles.citationsToggle}
                      onClick={() => showCitations(msg)}
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                      </svg>
                      {msg.citations.length} citation{msg.citations.length !== 1 ? "s" : ""}
                    </button>
                    <div className={styles.citPills}>
                      {msg.citations.slice(0, 3).map((c, i) => (
                        <span key={i} className={styles.citPill}>
                          {c.source.split("/").pop() || c.source}{c.page ? ` · p.${c.page}` : ""}
                        </span>
                      ))}
                      {msg.citations.length > 3 && (
                        <span className={styles.citPill}>+{msg.citations.length - 3} more</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className={`${styles.message} ${styles.assistant}`}>
              <div className={styles.msgAvatar}>⬡</div>
              <div className={styles.msgBody}>
                <div className={styles.thinking}>
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className={styles.inputArea}>
          <div className={styles.inputWrap}>
            <textarea
              ref={textareaRef}
              className={styles.textarea}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents…"
              rows={1}
              disabled={loading}
            />
            <button
              className={`${styles.sendBtn} ${input.trim() && !loading ? styles.active : ""}`}
              onClick={sendMessage}
              disabled={!input.trim() || loading}
              aria-label="Send message"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
          <p className={styles.inputHint}>
            Press Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>

      {/* Citations panel */}
      <div className={`${styles.citationsPanel} ${selectedCitations ? styles.panelVisible : ""}`}>
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>Citations</span>
          <button
            className={styles.panelClose}
            onClick={() => { setSelectedCitations(null); setActiveMsgId(null); }}
            aria-label="Close citations"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {selectedCitations ? (
          <div className={styles.citationsList}>
            {selectedCitations.map((c, i) => (
              <div key={i} className={styles.citationItem}>
                <div className={styles.citationMeta}>
                  <span className={styles.citationDoc}>{c.source.split("/").pop() || c.source}</span>
                  {c.page && <span className={styles.citationPage}>Page {c.page}</span>}
                  <span className={styles.citationScore}>
                    {Math.round(c.score * 100)}% match
                  </span>
                </div>
                <p className={styles.citationExcerpt}>&ldquo;{c.excerpt}&rdquo;</p>
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.panelEmpty}>
            <div className={styles.panelEmptyIcon}>◇</div>
            <p>Citations will appear here after you receive an answer.</p>
          </div>
        )}
      </div>
    </div>
  );
}
