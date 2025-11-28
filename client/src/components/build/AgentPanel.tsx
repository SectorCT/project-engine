import { useState, useRef, useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Search, MessageSquare } from "lucide-react";

interface AgentMessage {
  id: string;
  agentRole: "analyst" | "manager" | "architect" | "developer" | "qa";
  agentName: string;
  content: string;
  timestamp: string;
  isDecision?: boolean;
  category?: "planning" | "development" | "testing";
}

const agentColors = {
  analyst: "bg-agent-analyst",
  manager: "bg-agent-manager",
  architect: "bg-agent-architect",
  developer: "bg-agent-developer",
  qa: "bg-agent-qa",
};

const agentNames = {
  analyst: "Analyst",
  manager: "Manager",
  architect: "Architect",
  developer: "Developer",
  qa: "QA",
};

const mockMessages: AgentMessage[] = [
  {
    id: "1",
    agentRole: "analyst",
    agentName: "Sarah",
    content: "Analyzing project requirements and user stories...",
    timestamp: "2:34 PM",
    category: "planning",
  },
  {
    id: "2",
    agentRole: "manager",
    agentName: "Mike",
    content: "Breaking down the project into 5 main components and 12 tasks",
    timestamp: "2:35 PM",
    isDecision: true,
    category: "planning",
  },
  {
    id: "3",
    agentRole: "architect",
    agentName: "Alex",
    content: "Designing system architecture with microservices pattern",
    timestamp: "2:36 PM",
    category: "planning",
  },
  {
    id: "4",
    agentRole: "developer",
    agentName: "Jordan",
    content: "Creating UserDashboard component with authentication flow",
    timestamp: "2:38 PM",
    category: "development",
  },
  {
    id: "5",
    agentRole: "qa",
    agentName: "Casey",
    content: "Running test suite... All 12 tests passed ✓",
    timestamp: "2:40 PM",
    category: "testing",
  },
];

export const AgentPanel = () => {
  const [messages] = useState<AgentMessage[]>(mockMessages);
  const [filter, setFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const filteredMessages = messages.filter((msg) => {
    const matchesFilter =
      filter === "all" ||
      filter === msg.category ||
      (filter === "decisions" && msg.isDecision);
    const matchesSearch = msg.content
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getInitials = (name: string) => name.charAt(0).toUpperCase();

  return (
    <Card className="glass h-full flex flex-col">
      <div className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <MessageSquare className="w-5 h-5" />
          Agent Communication
        </h2>

        <div className="flex flex-wrap gap-2 mb-3">
          {["all", "planning", "development", "testing", "decisions"].map(
            (f) => (
              <Button
                key={f}
                variant={filter === f ? "default" : "outline"}
                size="sm"
                onClick={() => setFilter(f)}
                className="text-xs"
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </Button>
            )
          )}
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search messages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div ref={scrollRef} className="space-y-4">
          {filteredMessages.map((message) => (
            <div
              key={message.id}
              className="flex gap-3 animate-fade-in"
            >
              <div
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold flex-shrink-0",
                  agentColors[message.agentRole]
                )}
              >
                {getInitials(message.agentName)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm">
                    {message.agentName}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    • {agentNames[message.agentRole]}
                  </span>
                  {message.isDecision && (
                    <Badge
                      variant="outline"
                      className="text-xs bg-primary/10 text-primary border-primary/20"
                    >
                      DECISION
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-foreground mb-1">
                  {message.content}
                </p>
                <span className="text-xs text-muted-foreground">
                  {message.timestamp}
                </span>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
};

