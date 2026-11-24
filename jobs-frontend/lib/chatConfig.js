// Where the chatbot lives and which query param selects a saved conversation.
// If the chatbot is not on the home page, change CHAT_PATH here (e.g. '/chat').
export const CHAT_PATH = '/';
export const CHAT_PARAM = 'chat';

export const chatHref = (id) => (id ? `${CHAT_PATH}?${CHAT_PARAM}=${id}` : CHAT_PATH);
