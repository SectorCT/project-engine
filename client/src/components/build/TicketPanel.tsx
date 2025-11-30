import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

export interface TicketEvent {
  ticketId: string;
  title?: string;
  status?: string;
  type?: string;
  assignedTo?: string;
  timestamp?: string;
  message?: string;
}

interface TicketPanelProps {
  tickets: TicketEvent[];
  className?: string;
}

const statusStyles: Record<string, string> = {
  todo: "bg-muted text-foreground",
  in_progress: "bg-blue-100 text-blue-800",
  done: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

const FALLBACK_STATUS = "todo";

function formatStatusLabel(status: string) {
  return status.replace(/_/g, " ");
}

export function TicketPanel({ tickets, className }: TicketPanelProps) {
  const toTimestamp = (value?: string) => {
    if (!value) return 0;
    const ms = new Date(value).getTime();
    return Number.isNaN(ms) ? 0 : ms;
  };

  const sorted = [...tickets].sort((a, b) => toTimestamp(a.timestamp) - toTimestamp(b.timestamp));

  return (
    <Card className={cn("glass flex flex-col h-full", className)}>
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-sm">Ticket Progress</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0">
        {sorted.length === 0 ? (
          <div className="text-sm text-muted-foreground">No ticket activity yet.</div>
        ) : (
          <ScrollArea className="h-full pr-2">
            <div className="space-y-3">
              {sorted.map((ticket) => {
                const status = ticket.status || FALLBACK_STATUS;
                return (
                  <div key={ticket.ticketId} className="border border-border rounded-md p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-medium truncate">
                          {ticket.title || "Untitled Ticket"}
                        </p>
                        <p className="text-xs text-muted-foreground truncate">
                          {ticket.assignedTo || ticket.type || "Unassigned"}
                        </p>
                      </div>
                      <Badge
                        className={cn(
                          "text-xs capitalize",
                          statusStyles[status] || "bg-muted text-foreground"
                        )}
                      >
                        {formatStatusLabel(status)}
                      </Badge>
                    </div>
                    {ticket.message && (
                      <p className="mt-2 text-xs text-muted-foreground">{ticket.message}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}

