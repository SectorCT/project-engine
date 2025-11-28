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
    <Card className="glass flex flex-col">
      <div className="p-2 border-b border-border">
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

      <ScrollArea className="flex-1 p-2">
        <div ref={scrollRef} className="space-y-2">
          {filteredMessages.map((message) => (
            <div
              key={message.id}
              className="flex gap-2 animate-fade-in"
            >
              <div
                className={cn(
                  "w-6 h-6 rounded-full flex items-center justify-center text-white font-semibold flex-shrink-0 text-xs",
                  agentColors[message.agentRole]
                )}
              >
                {getInitials(message.agentName)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className="font-semibold text-xs">
                    {message.agentName}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    • {agentNames[message.agentRole]}
                  </span>
                  {message.isDecision && (
                    <Badge
                      variant="outline"
                      className="text-[10px] bg-primary/10 text-primary border-primary/20 px-1 py-0"
                    >
                      DECISION
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-foreground mb-0.5">
                  {message.content}
                </p>
                <span className="text-[10px] text-muted-foreground">
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

