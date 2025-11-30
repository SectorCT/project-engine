import { Ticket } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

interface TicketsPanelProps {
  tickets: Ticket[];
}

interface TicketItemProps {
  ticket: Ticket;
  level?: number;
  isExpanded?: boolean;
  onToggle?: () => void;
  hasChildren?: boolean;
}

const statusColors = {
  todo: "bg-muted text-foreground border-border",
  "in-progress": "bg-primary/10 text-primary border-primary/20",
  "in_progress": "bg-primary/10 text-primary border-primary/20",
  done: "bg-success/10 text-success border-success/20",
  completed: "bg-success/10 text-success border-success/20",
};

const typeColors = {
  epic: "bg-purple-500/20 text-purple-600 border-purple-500/30",
  story: "bg-blue-500/20 text-blue-600 border-blue-500/30",
  task: "bg-gray-500/20 text-gray-600 border-gray-500/30",
};

function TicketItem({ ticket, level = 0, isExpanded = true, onToggle, hasChildren = false }: TicketItemProps & { hasChildren?: boolean }) {
  const statusKey = ticket.status.toLowerCase().replace("-", "_") as keyof typeof statusColors;
  const statusColor = statusColors[statusKey] || statusColors.todo;
  const typeColor = typeColors[ticket.type] || typeColors.task;
  const isNested = level > 0;

  const handleClick = () => {
    // Make the ticket clickable - you can add navigation or modal opening here
    console.log('Ticket clicked:', ticket.id);
  };

  return (
    <div className={cn("space-y-1", isNested && "ml-10")}>
      <div
        onClick={handleClick}
        className={cn(
          "p-2 rounded text-sm border transition-colors cursor-pointer hover:opacity-80",
          statusColor,
          level === 0 && "font-medium",
          isNested && "bg-background/50 border-l-4 border-l-primary/30"
        )}
      >
        <div className="flex items-start gap-2">
          {hasChildren && onToggle && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggle();
              }}
              className="mt-0.5 flex-shrink-0 hover:bg-background/50 rounded p-0.5"
            >
              {isExpanded ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
            </button>
          )}
          {!hasChildren && <div className="w-4" />}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Badge
                variant="outline"
                className={cn("text-[10px] px-1.5 py-0", typeColor)}
              >
                {ticket.type.toUpperCase()}
              </Badge>
              <span className="font-medium truncate">{ticket.title}</span>
            </div>
            {ticket.description && (
              <p className="text-xs text-muted-foreground line-clamp-2">
                {ticket.description}
              </p>
            )}
            <div className="flex items-center gap-2 mt-1.5 text-[10px] text-muted-foreground">
              <span>Assigned: {ticket.assigned_to || "Unassigned"}</span>
              {ticket.dependencies.length > 0 && (
                <span>• {ticket.dependencies.length} dependency(ies)</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function TicketsPanel({ tickets }: TicketsPanelProps) {
  // Build hierarchy: map of parent_id -> children
  const childrenMap = new Map<string, Ticket[]>();
  const ticketMap = new Map<string, Ticket>();
  
  // First pass: create ticket map and identify children
  tickets.forEach((ticket) => {
    ticketMap.set(ticket.id, ticket);
    
    // If ticket has a parent (and parent_id is not the ticket itself), add to children map
    if (ticket.parent_id && ticket.parent_id !== ticket.id) {
      if (!childrenMap.has(ticket.parent_id)) {
        childrenMap.set(ticket.parent_id, []);
      }
      childrenMap.get(ticket.parent_id)!.push(ticket);
    }
  });

  // Find root tickets (those without a parent or parent_id === id)
  const rootTickets = tickets.filter(
    (ticket) => !ticket.parent_id || ticket.parent_id === ticket.id
  );

  // Helper to normalize status - handle various status formats and edge cases
  const normalizeStatus = (status: string | null | undefined): "todo" | "in-progress" | "done" => {
    if (!status) return "todo";
    const s = status.toLowerCase().trim();
    // Handle in_progress variations
    if (s === "in-progress" || s === "in_progress" || s === "working" || s === "in progress") {
      return "in-progress";
    }
    // Handle done variations
    if (s === "done" || s === "completed" || s === "finished") {
      return "done";
    }
    // Default to todo for any other status (including empty string, "pending", etc.)
    return "todo";
  };

  // Group root tickets by status - ensure in_progress tickets go to in-progress column
  const ticketsByStatus = {
    todo: rootTickets.filter((t) => {
      const normalized = normalizeStatus(t.status);
      return normalized === "todo";
    }),
    "in-progress": rootTickets.filter((t) => {
      const normalized = normalizeStatus(t.status);
      return normalized === "in-progress";
    }),
    done: rootTickets.filter((t) => {
      const normalized = normalizeStatus(t.status);
      return normalized === "done";
    }),
  };

  // Component to render a ticket with its children
  const TicketWithChildren = ({ ticket, level = 0 }: { ticket: Ticket; level?: number }) => {
    const [isExpanded, setIsExpanded] = useState(true);
    const children = childrenMap.get(ticket.id) || [];
    const hasChildren = children.length > 0;

    return (
      <>
        <TicketItem
          ticket={ticket}
          level={level}
          isExpanded={isExpanded}
          onToggle={hasChildren ? () => setIsExpanded(!isExpanded) : undefined}
          hasChildren={hasChildren}
        />
        {isExpanded && hasChildren && (
          <div className="space-y-1">
            {children.map((child) => (
              <TicketWithChildren key={child.id} ticket={child} level={level + 1} />
            ))}
          </div>
        )}
      </>
    );
  };

  // Render tickets for a status column
  const renderStatusColumn = (status: "todo" | "in-progress" | "done", label: string) => {
    const statusTickets = ticketsByStatus[status];

    return (
      <div className="bg-card rounded-lg border border-border h-full flex flex-col overflow-hidden max-h-full">
        <div className="p-3 border-b border-border flex-shrink-0">
          <h3 className="font-semibold text-sm">{label}</h3>
        </div>
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-3 min-h-0">
          <div className="space-y-2">
            {statusTickets.length === 0 ? (
              <div className="text-xs text-muted-foreground text-center py-4">
                No tickets
              </div>
            ) : (
              statusTickets.map((ticket) => (
                <TicketWithChildren key={ticket.id} ticket={ticket} />
              ))
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 h-full w-full">
      {renderStatusColumn("todo", "To Do")}
      {renderStatusColumn("in-progress", "In Progress")}
      {renderStatusColumn("done", "Done")}
    </div>
  );
}

