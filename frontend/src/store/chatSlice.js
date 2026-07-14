import { createSlice, nanoid } from "@reduxjs/toolkit";

const initialState = {
  sessionId: typeof window !== "undefined"
    ? (localStorage.getItem("hcp_session_id") || nanoid())
    : nanoid(),
  messages: [
    {
      id: nanoid(),
      role: "assistant",
      content:
        "Hi, I'm your AI logging assistant. Tell me about a visit — e.g. \"Met Dr. Sharma today at 4pm, discussed OncoBoost efficacy, she was positive, left the Phase III brochure and 10 samples.\"",
      toolCalls: [],
    },
  ],
  isSending: false,
  error: null,
};

if (typeof window !== "undefined") {
  localStorage.setItem("hcp_session_id", initialState.sessionId);
}

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    messageSent(state, action) {
      state.messages.push({ id: nanoid(), role: "user", content: action.payload, toolCalls: [] });
      state.isSending = true;
      state.error = null;
    },
    replyReceived(state, action) {
      const { reply, toolCalls } = action.payload;
      state.messages.push({ id: nanoid(), role: "assistant", content: reply, toolCalls: toolCalls || [] });
      state.isSending = false;
    },
    requestFailed(state, action) {
      state.isSending = false;
      state.error = action.payload;
      state.messages.push({
        id: nanoid(),
        role: "assistant",
        content: `Sorry, I couldn't process that: ${action.payload}`,
        toolCalls: [],
        isError: true,
      });
    },
  },
});

export const { messageSent, replyReceived, requestFailed } = chatSlice.actions;
export default chatSlice.reducer;
