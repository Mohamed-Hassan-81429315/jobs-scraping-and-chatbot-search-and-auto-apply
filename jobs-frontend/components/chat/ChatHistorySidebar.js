import { getUser } from '../../lib/auth';
import { listConversations } from '../../app/chat/actions';
import ChatHistoryList from './ChatHistoryList';

/** Server component: only ever lists the signed-in user's chats. Renders nothing for guests. */
export default async function ChatHistorySidebar({ activeId = null }) {
  const user = await getUser();
  if (!user) return null;

  const items = await listConversations();
  return <ChatHistoryList items={items} activeId={activeId ? String(activeId) : null} />;
}
