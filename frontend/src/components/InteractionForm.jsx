import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Field from "./Field";
import { updateInteractionFields } from "../api/client";
import { formStateSetSilently } from "../store/interactionSlice";
import "./InteractionForm.css";

const SENTIMENT_META = {
  Positive: { color: "var(--positive)", bg: "var(--positive-soft)" },
  Neutral: { color: "var(--neutral)", bg: "var(--neutral-soft)" },
  Negative: { color: "var(--negative)", bg: "var(--negative-soft)" },
};

const INTERACTION_TYPES = ["Meeting", "Call", "Email", "Conference"];

function TagList({ items, tone = "brand", onRemove }) {
  if (!items || items.length === 0) return <span className="field-empty">None added yet</span>;
  return (
    <div className="tag-list">
      {items.map((item, i) => (
        <span className={`tag tag--${tone}`} key={`${item}-${i}`}>
          {item}
          {onRemove && (
            <button type="button" className="tag-remove" onClick={() => onRemove(item)} aria-label={`Remove ${item}`}>
              ×
            </button>
          )}
        </span>
      ))}
    </div>
  );
}

function TagAdder({ placeholder, onAdd }) {
  const [value, setValue] = useState("");
  function submit(e) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    onAdd(trimmed);
    setValue("");
  }
  return (
    <form className="tag-adder" onSubmit={submit}>
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button type="submit">+ Add</button>
    </form>
  );
}

export default function InteractionForm() {
  const dispatch = useDispatch();
  const fields = useSelector((s) => s.interaction.fields);
  const sessionId = useSelector((s) => s.chat.sessionId);
  const [draft, setDraft] = useState(fields);

  // Re-sync local draft whenever the backing fields change -- covers both
  // AI-driven updates from chat and the initial load.
  useEffect(() => {
    setDraft(fields);
  }, [fields]);

  async function commit(partialUpdate) {
    setDraft((d) => ({ ...d, ...partialUpdate }));
    try {
      const updated = await updateInteractionFields(sessionId, partialUpdate);
      dispatch(formStateSetSilently(updated));
    } catch (err) {
      console.error("Failed to save field edit:", err);
    }
  }

  function handleBlurCommit(name) {
    const value = draft[name];
    if (value === fields[name]) return; // no change, skip the call
    commit({ [name]: value });
  }

  function handleTextChange(name, value) {
    setDraft((d) => ({ ...d, [name]: value }));
  }

  function addMaterial(item) {
    commit({ materials_shared: [...(fields.materials_shared || []), item] });
  }
  function removeMaterial(item) {
    commit({ materials_shared: (fields.materials_shared || []).filter((m) => m !== item) });
  }
  function addSample(item) {
    commit({ samples_distributed: [...(fields.samples_distributed || []), item] });
  }
  function removeSample(item) {
    commit({ samples_distributed: (fields.samples_distributed || []).filter((s) => s !== item) });
  }

  return (
    <section className="form-panel" aria-label="Interaction details">
      <div className="form-panel-inner">
        <div className="form-section-heading">
          <h2>Interaction Details</h2>
          <span className="lock-pill">✏️ Edit directly, or describe the visit in chat</span>
        </div>

        <div className="form-grid">
          <Field name="hcp_name" label="HCP Name" editable>
            <input
              type="text"
              className="field-input"
              placeholder="Search or enter HCP name..."
              value={draft.hcp_name || ""}
              onChange={(e) => handleTextChange("hcp_name", e.target.value)}
              onBlur={() => handleBlurCommit("hcp_name")}
            />
          </Field>

          <Field name="interaction_type" label="Interaction Type" editable>
            <select
              className="field-input"
              value={draft.interaction_type || ""}
              onChange={(e) => commit({ interaction_type: e.target.value })}
            >
              <option value="">Select...</option>
              {INTERACTION_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </Field>

          <Field name="date" label="Date" editable>
            <input
              type="text"
              className="field-input"
              placeholder="DD-MM-YYYY"
              value={draft.date || ""}
              onChange={(e) => handleTextChange("date", e.target.value)}
              onBlur={() => handleBlurCommit("date")}
            />
          </Field>

          <Field name="time" label="Time" editable>
            <input
              type="text"
              className="field-input"
              placeholder="HH:MM"
              value={draft.time || ""}
              onChange={(e) => handleTextChange("time", e.target.value)}
              onBlur={() => handleBlurCommit("time")}
            />
          </Field>
        </div>

        <Field name="attendees" label="Attendees" editable>
          <input
            type="text"
            className="field-input"
            placeholder="Enter names or search..."
            value={draft.attendees || ""}
            onChange={(e) => handleTextChange("attendees", e.target.value)}
            onBlur={() => handleBlurCommit("attendees")}
          />
        </Field>

        <Field name="topics_discussed" label="Topics Discussed" editable>
          <textarea
            className="field-input field-input--textarea"
            placeholder="Enter key discussion points..."
            value={draft.topics_discussed || ""}
            onChange={(e) => handleTextChange("topics_discussed", e.target.value)}
            onBlur={() => handleBlurCommit("topics_discussed")}
          />
        </Field>

        <div className="form-grid">
          <Field name="materials_shared" label="Materials Shared" empty="No materials added" editable>
            <TagList items={fields.materials_shared} tone="brand" onRemove={removeMaterial} />
            <TagAdder placeholder="Add material..." onAdd={addMaterial} />
          </Field>

          <Field name="samples_distributed" label="Samples Distributed" empty="No samples added" editable>
            <TagList items={fields.samples_distributed} tone="neutral" onRemove={removeSample} />
            <TagAdder placeholder="Add sample..." onAdd={addSample} />
          </Field>
        </div>

        <Field name="sentiment" label="Observed / Inferred HCP Sentiment" editable>
          <div className="sentiment-radio-group">
            {Object.keys(SENTIMENT_META).map((option) => (
              <label key={option} className="sentiment-radio">
                <input
                  type="radio"
                  name="sentiment"
                  value={option}
                  checked={fields.sentiment === option}
                  onChange={() => commit({ sentiment: option })}
                />
                <span
                  className="sentiment-pill"
                  style={{
                    color: SENTIMENT_META[option].color,
                    background: fields.sentiment === option ? SENTIMENT_META[option].bg : "transparent",
                  }}
                >
                  ● {option}
                </span>
              </label>
            ))}
          </div>
        </Field>

        <Field name="outcomes" label="Outcomes" editable>
          <textarea
            className="field-input field-input--textarea"
            placeholder="Key outcomes or agreements..."
            value={draft.outcomes || ""}
            onChange={(e) => handleTextChange("outcomes", e.target.value)}
            onBlur={() => handleBlurCommit("outcomes")}
          />
        </Field>

        <Field name="follow_up_actions" label="Follow-up Actions" editable>
          <textarea
            className="field-input field-input--textarea"
            placeholder="Enter next steps or tasks..."
            value={draft.follow_up_actions || ""}
            onChange={(e) => handleTextChange("follow_up_actions", e.target.value)}
            onBlur={() => handleBlurCommit("follow_up_actions")}
          />
        </Field>

        <Field name="ai_suggested_followups" label="AI Suggested Follow-ups" empty="Nothing suggested yet">
          {fields.ai_suggested_followups && fields.ai_suggested_followups.length > 0 && (
            <ul className="suggestion-list">
              {fields.ai_suggested_followups.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          )}
        </Field>
      </div>
    </section>
  );
}