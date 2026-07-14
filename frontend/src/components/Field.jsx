import React, { useEffect, useRef, useState } from "react";
import { useSelector } from "react-redux";

/**
 * Every field on the left panel renders through this component. Fields can
 * now be edited directly (per spec: rep may either type into the form OR
 * describe the visit in chat) -- but the "AI updated" pulse below remains
 * exclusively tied to changes that came from the chat/agent path, never
 * from a manual edit, so the causal link between "what I said in chat" and
 * "what changed in the form" stays unambiguous.
 */
export default function Field({ name, label, empty = "Not logged yet", editable = false, children }) {
  const isUpdated = useSelector((s) => s.interaction.recentlyUpdated.includes(name));
  const [pulseKey, setPulseKey] = useState(0);
  const wasUpdated = useRef(false);

  useEffect(() => {
    if (isUpdated && !wasUpdated.current) {
      setPulseKey((k) => k + 1);
    }
    wasUpdated.current = isUpdated;
  }, [isUpdated]);

  return (
    <div className="field" data-pulse={pulseKey}>
      <div className="field-label-row">
        <label className="field-label">{label}</label>
        {isUpdated && (
          <span key={pulseKey} className="field-ai-tag">
            AI updated
          </span>
        )}
      </div>
      <div
        key={`box-${pulseKey}`}
        className={`field-box ${isUpdated ? "field-box--pulse" : ""} ${editable ? "field-box--editable" : ""}`}
      >
        {children ?? <span className="field-empty">{empty}</span>}
      </div>
    </div>
  );
}