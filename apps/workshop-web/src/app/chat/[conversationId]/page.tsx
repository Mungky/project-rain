import { ChatThread } from "@/components/chat/chat-thread";

interface ConversationPageProps {
  params: Promise<{ conversationId: string }>;
}

export default async function ConversationPage({
  params,
}: ConversationPageProps) {
  const { conversationId } = await params;

  return <ChatThread conversationId={conversationId} />;
}