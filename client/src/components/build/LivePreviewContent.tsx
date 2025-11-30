import { Ticket } from "@/lib/api";
import { TicketsPanel } from "./TicketsPanel";

interface LivePreviewContentProps {
  device: "desktop" | "tablet" | "mobile";
  tickets?: Ticket[];
}

export const LivePreviewContent = ({ device, tickets = [] }: LivePreviewContentProps) => {
  return (
    <div className="bg-background-elevated rounded-lg border border-border overflow-hidden w-full aspect-video flex flex-col">
      {/* Browser Controls */}
      <div className="flex items-center gap-2 p-2 bg-background-overlay border-b border-border">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-status-failed"></div>
          <div className="w-3 h-3 rounded-full bg-warning"></div>
          <div className="w-3 h-3 rounded-full bg-success"></div>
        </div>
        <div className="flex-1 bg-input rounded-md px-3 py-1.5 text-xs text-muted-foreground flex items-center gap-2">
          <span>🔒</span>
          <span>localhost:3000/dashboard</span>
        </div>
      </div>

      {/* Preview Content */}
      <div className="flex-1 overflow-auto bg-background">
        <div className="p-6 space-y-4 h-full">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gradient">
              Task Management App
            </h1>
          </div>

          {tickets.length > 0 ? (
            <TicketsPanel tickets={tickets} />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-card p-4 rounded-lg border border-border">
                <h3 className="font-semibold mb-2">To Do</h3>
                <div className="space-y-2">
                  <div className="text-xs text-muted-foreground text-center py-4">
                    No tickets yet
                  </div>
                </div>
              </div>
              <div className="bg-card p-4 rounded-lg border border-border">
                <h3 className="font-semibold mb-2">In Progress</h3>
                <div className="space-y-2">
                  <div className="text-xs text-muted-foreground text-center py-4">
                    No tickets yet
                  </div>
                </div>
              </div>
              <div className="bg-card p-4 rounded-lg border border-border">
                <h3 className="font-semibold mb-2">Done</h3>
                <div className="space-y-2">
                  <div className="text-xs text-muted-foreground text-center py-4">
                    No tickets yet
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

