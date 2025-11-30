import { useState, useRef, useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Search, MessageSquare, Send, Trash2 } from "lucide-react";
import { JobMessage, JobStep, api } from "@/lib/api";
import { toast } from "sonner";

interface AgentMessage {
  id: string;
  agentRole: "analyst" | "manager" | "architect" | "developer" | "qa" | "user";
  agentName: string;
  content: string;
  timestamp: string;
  isDecision?: boolean;
  category?: "planning" | "development" | "testing";
  role?: "user" | "agent" | "system";
}

interface AgentPanelProps {
  messages?: JobMessage[];
  steps?: JobStep[];
  onSendMessage?: (content: string) => void;
  canSendMessages?: boolean;
  onMessageDeleted?: () => void;
}

const agentColors: Record<string, string> = {
  analyst: "bg-agent-analyst",
  manager: "bg-agent-manager",
  architect: "bg-agent-architect",
  developer: "bg-agent-developer",
  qa: "bg-agent-qa",
  user: "bg-muted",
  "Client Relations": "bg-agent-analyst",
  "CEO": "bg-agent-manager",
  "CTO": "bg-agent-architect",
  "Secretary": "bg-agent-qa",
};

const agentNames: Record<string, string> = {
  analyst: "Analyst",
  manager: "Manager",
  architect: "Architect",
  developer: "Developer",
  qa: "QA",
  user: "You",
};

function mapAgentNameToRole(agentName: string): AgentMessage["agentRole"] {
  const name = agentName.toLowerCase();
  if (name.includes("client") || name.includes("relations")) return "analyst";
  if (name.includes("ceo") || name.includes("manager")) return "manager";
  if (name.includes("cto") || name.includes("architect")) return "architect";
  if (name.includes("secretary") || name.includes("qa")) return "qa";
  return "developer";
}

function formatTimestamp(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

export const AgentPanel = ({ messages = [], steps = [], onSendMessage, canSendMessages = false, onMessageDeleted }: AgentPanelProps) => {
  const [filter, setFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [deletingMessageId, setDeletingMessageId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<React.ElementRef<typeof ScrollArea>>(null);

  // Check if in dev mode (for delete button visibility)
  const isDevMode = import.meta.env.DEV || import.meta.env.VITE_DEV_MODE === 'true';

  const handleDeleteMessage = async (messageId: string) => {
    if (!window.confirm("Are you sure you want to delete this message? This action cannot be undone.")) {
      return;
    }

    setDeletingMessageId(messageId);
    try {
      // Strip the prefix to get the original ID
      const originalId = messageId.startsWith('msg-') 
        ? messageId.replace('msg-', '') 
        : messageId.startsWith('step-')
        ? messageId.replace('step-', '')
        : messageId;
      
      // Only delete if it's a message (steps might not have delete API)
      if (messageId.startsWith('msg-')) {
        await api.deleteJobMessage(originalId);
        toast.success("Message deleted successfully");
        onMessageDeleted?.();
      } else {
        toast.error("Cannot delete step messages");
      }
    } catch (error: any) {
      toast.error(error?.detail || "Failed to delete message");
    } finally {
      setDeletingMessageId(null);
    }
  };

  // Combine messages and steps into a unified list
  const allMessages: AgentMessage[] = [
    ...messages.map((msg) => ({
      id: `msg-${msg.id}`, // Prefix with 'msg-' to ensure uniqueness
      agentRole: msg.role === "user" ? "user" : mapAgentNameToRole(msg.sender),
      agentName: msg.sender || (msg.role === "user" ? "You" : "Agent"),
      content: msg.content,
      timestamp: formatTimestamp(msg.created_at),
      role: msg.role,
      category: msg.metadata?.stage === "requirements" ? "planning" : undefined,
    })),
    ...steps.map((step) => ({
      id: `step-${step.id}`, // Prefix with 'step-' to ensure uniqueness
      agentRole: mapAgentNameToRole(step.agent_name),
      agentName: step.agent_name,
      content: step.message,
      timestamp: formatTimestamp(step.created_at),
      category: "development" as const,
    })),
  ].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  const filteredMessages = allMessages.filter((msg) => {
    const matchesFilter =
      filter === "all" ||
      filter === msg.category ||
      (filter === "decisions" && msg.isDecision);
    const matchesSearch = msg.content
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    // Use setTimeout to ensure DOM is updated
    setTimeout(() => {
      if (scrollAreaRef.current) {
        // Find the ScrollArea viewport (Radix UI structure)
        const viewport = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]') as HTMLElement;
        if (viewport) {
          viewport.scrollTop = viewport.scrollHeight;
        } else if (scrollRef.current) {
          // Fallback to direct scroll
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      }
    }, 100);
  }, [filteredMessages.length, messages.length, steps.length]);

  const handleSend = () => {
    if (inputValue.trim() && onSendMessage) {
      onSendMessage(inputValue.trim());
      setInputValue("");
    }
  };

  const getInitials = (name: string) => name.charAt(0).toUpperCase();

  return (
    <Card className="glass flex flex-col h-full">
      <div className="p-2 border-b border-border flex-shrink-0">
        <h2 className="text-sm font-semibold mb-2 flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          Agent Communication
        </h2>

        <div className="flex flex-wrap gap-1 mb-2">
          {["all", "planning", "development", "testing", "decisions"].map(
            (f) => (
              <Button
                key={f}
                variant={filter === f ? "default" : "outline"}
                size="sm"
                onClick={() => setFilter(f)}
                className="text-[10px] h-6 px-2"
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </Button>
            )
          )}
        </div>

        <div className="relative">
          <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-3 h-3 text-muted-foreground" />
          <Input
            placeholder="Search messages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-7 h-7 text-xs"
          />
        </div>
      </div>

      <ScrollArea ref={scrollAreaRef} className="flex-1 p-2 min-h-0">
        <div ref={scrollRef} className="space-y-2">
          {filteredMessages.length === 0 ? (
            <div className="text-center text-sm text-muted-foreground py-8">
              No messages yet
            </div>
          ) : (
            filteredMessages.map((message) => (
            <div
              key={message.id}
              className="flex gap-2 animate-fade-in group"
            >
              <div
                className={cn(
                  "w-6 h-6 rounded-full flex items-center justify-center text-white font-semibold flex-shrink-0 text-xs",
                    agentColors[message.agentRole] || agentColors[message.agentName] || "bg-muted"
                )}
              >
                {getInitials(message.agentName)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className="font-semibold text-xs">
                    {message.agentName}
                  </span>
                    {message.agentRole !== "user" && (
                  <span className="text-[10px] text-muted-foreground">
                        • {agentNames[message.agentRole] || message.agentName}
                  </span>
                    )}
                  {message.isDecision && (
                    <Badge
                      variant="outline"
                      className="text-[10px] bg-primary/10 text-primary border-primary/20 px-1 py-0"
                    >
                      DECISION
                    </Badge>
                  )}
                  {isDevMode && message.role !== 'system' && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity ml-auto"
                      onClick={() => handleDeleteMessage(message.id)}
                      disabled={deletingMessageId === message.id}
                    >
                      <Trash2 className="w-3 h-3 text-destructive" />
                    </Button>
                  )}
                </div>
                  <p className="text-xs text-foreground mb-0.5 whitespace-pre-wrap">
                  {message.content}
                </p>
                <span className="text-[10px] text-muted-foreground">
                  {message.timestamp}
                </span>
              </div>
            </div>
            ))
          )}
        </div>
      </ScrollArea>

      {canSendMessages && onSendMessage && (
        <div className="p-2 border-t border-border flex-shrink-0">
          <div className="flex gap-2">
            <Input
              placeholder="Type your message..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              className="h-8 text-xs"
            />
            <Button
              size="sm"
              onClick={handleSend}
              disabled={!inputValue.trim()}
              className="h-8"
            >
              <Send className="w-3 h-3" />
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
};

