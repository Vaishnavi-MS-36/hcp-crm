import React from "react";
import InteractionForm from "./components/InteractionForm";
import ChatPanel from "./components/ChatPanel";
import "./App.css";

export default function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="topbar-eyebrow">AI-FIRST CRM · HCP MODULE</span>
          <h1 className="topbar-title">Log HCP Interaction</h1>
        </div>
        <p className="topbar-sub">
          Describe the visit to the AI assistant, or edit the fields directly — both stay perfectly in sync.
        </p>
      </header>

      <main className="split">
        <InteractionForm />
        <ChatPanel />
      </main>
    </div>
  );
}