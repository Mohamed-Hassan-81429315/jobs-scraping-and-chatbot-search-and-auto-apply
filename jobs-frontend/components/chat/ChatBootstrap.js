import { getUser } from '../../lib/auth';
import PendingChatImporter from './PendingChatImporter';

/** Put once in the root layout. Renders nothing for guests. */
export default async function ChatBootstrap() {
  const user = await getUser();
  if (!user) return null;
  return <PendingChatImporter />;
}
