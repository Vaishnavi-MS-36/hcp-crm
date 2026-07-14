import { createSlice } from "@reduxjs/toolkit";

const emptyForm = {
  id: null,
  hcp_name: null,
  interaction_type: null,
  date: null,
  time: null,
  attendees: null,
  topics_discussed: null,
  materials_shared: [],
  samples_distributed: [],
  sentiment: null,
  outcomes: null,
  follow_up_actions: null,
  ai_suggested_followups: [],
};

const initialState = {
  fields: emptyForm,
  recentlyUpdated: [], // field names the AI just touched, used to trigger the highlight animation
};

function diffKeys(prev, next) {
  const keys = new Set([...Object.keys(prev), ...Object.keys(next)]);
  const changed = [];
  keys.forEach((k) => {
    const a = JSON.stringify(prev[k]);
    const b = JSON.stringify(next[k]);
    if (a !== b) changed.push(k);
  });
  return changed;
}

const interactionSlice = createSlice({
  name: "interaction",
  initialState,
  reducers: {
    formStateReceived(state, action) {
      const changed = diffKeys(state.fields, action.payload);
      state.fields = action.payload;
      state.recentlyUpdated = changed;
    },
    formStateSetSilently(state, action) {
      // Used for direct manual form edits -- updates the fields without
      // triggering the "AI updated" pulse, since the rep typed this
      // themselves rather than the assistant inferring it from chat.
      state.fields = action.payload;
    },
    clearHighlights(state) {
      state.recentlyUpdated = [];
    },
    resetForm(state) {
      state.fields = emptyForm;
      state.recentlyUpdated = [];
    },
  },
});

export const { formStateReceived, formStateSetSilently, clearHighlights, resetForm } = interactionSlice.actions;
export default interactionSlice.reducer;