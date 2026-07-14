import React, { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendChatMessage } from "../api/client";
import { messageSent, replyReceived, requestFailed } from "../store/chatSlice";
import { formStateReceived, clearHighlights } from "../store/interactionSlice";
import "./ChatPanel.css";

const SUGGESTIONS = [
  "Met Dr. Sharma today at 4pm, discussed OncoBoost efficacy data, she seemed positive and I left the Phase III brochure plus 10 samples.",
  "Actually change the sentiment to neutral.",
  "Also left a CardioFlow leave-behind with her.",
];

export default function ChatPanel() {
  const dispatch = useDispatch();
  const { sessionId, messages, isSending } = useSelector((s) => s.chat);
  const [draft, setDraft] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  async function submit(text) {
    const trimmed = text.trim();
    if (!trimmed || isSending) return;
    dispatch(messageSent(trimmed));
    setDraft("");
    try {
      const data = await sendChatMessage(sessionId, trimmed);
      dispatch(formStateReceived(data.form_state));
      dispatch(replyReceived({ reply: data.reply, toolCalls: data.tool_calls }));
      window.setTimeout(() => dispatch(clearHighlights()), 2200);
    } catch (err) {
      dispatch(requestFailed(err.message || "Unknown error"));
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    submit(draft);
  }

  return (
    <section className="chat-panel" aria-label="AI Assistant">
      <div className="chat-header">
        <div className="chat-header-dot" />
        <div>
          <div className="chat-header-title">AI Assistant</div>
          <div className="chat-header-sub">Log interaction via chat</div>
        </div>
      </div>

      <div className="chat-scroll" ref={scrollRef}>
        {messages.map((m) => (
          <div key={m.id} className={`bubble bubble--${m.role} ${m.isError ? "bubble--error" : ""}`}>
            <p>{m.content}</p>
            {m.toolCalls && m.toolCalls.length > 0 && (
              <div className="tool-trace">
                {m.toolCalls.map((tc, i) => (
                  <span className="tool-chip" key={i} title={tc.result_summary}>
                    ⚙ {tc.tool}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {isSending && (
          <div className="bubble bubble--assistant bubble--typing">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        )}
      </div>

      {messages.length <= 1 && (
        <div className="chat-suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" className="suggestion-chip" onClick={() => submit(s)}>
              {s.length > 46 ? s.slice(0, 46) + "…" : s}
            </button>
          ))}
        </div>
      )}

      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Describe interaction…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={isSending}
        />
        <button type="submit" disabled={isSending || !draft.trim()}>
          {isSending ? "…" : "Log"}
        </button>
      </form>
    </section>
  );
}
