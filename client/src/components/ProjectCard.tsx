import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Trash2, MoreVertical } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { useState } from "react";

interface ProjectCardProps {
  id: string;
  name: string;
  status: "planning" | "building" | "testing" | "complete" | "failed";
  progress: number;
  techStack: string[];
  createdAt: string;
  lastActivity: string;
  onDelete?: (id: string) => void;
}

const statusColors = {
  planning: "bg-status-planning/10 text-status-planning border-status-planning/20",
  building: "bg-status-building/10 text-status-building border-status-building/20",
  testing: "bg-status-testing/10 text-status-testing border-status-testing/20",
  complete: "bg-status-complete/10 text-status-complete border-status-complete/20",
  failed: "bg-status-failed/10 text-status-failed border-status-failed/20",
};

const progressColors = {
  planning: "bg-status-planning",
  building: "bg-status-building",
  testing: "bg-status-testing",
  complete: "bg-status-complete",
  failed: "bg-status-failed",
};

export const ProjectCard = ({
  id,
  name,
  status,
  progress,
  techStack,
  createdAt,
  lastActivity,
  onDelete,
}: ProjectCardProps) => {
  const navigate = useNavigate();
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDelete) {
      setIsDeleting(true);
      await onDelete(id);
      setIsDeleting(false);
    }
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="relative"
    >
      <Card 
        className="glass h-full transition-smooth hover:glow-primary cursor-pointer"
        onClick={() => navigate(`/project/${id}`)}
      >
        <CardContent className="p-6">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-semibold text-foreground flex-1 pr-2">{name}</h3>
            <div className="flex items-center gap-2">
              <Badge className={cn("border", statusColors[status])}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </Badge>
              {onDelete && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={handleDelete}
                      disabled={isDeleting}
                      className="text-destructive"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      {isDeleting ? "Deleting..." : "Delete"}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {techStack.slice(0, 4).map((tech, index) => (
                <Badge
                  key={index}
                  variant="outline"
                  className="text-xs bg-muted/50"
                >
                  {tech}
                </Badge>
              ))}
              {techStack.length > 4 && (
                <Badge variant="outline" className="text-xs bg-muted/50">
                  +{techStack.length - 4}
                </Badge>
              )}
            </div>

            <div className="text-sm text-muted-foreground">
              <p>Last activity: {lastActivity}</p>
            </div>
          </div>
        </CardContent>

        <CardFooter className="p-6 pt-0 flex flex-col gap-2">
          <div className="w-full">
            <div className="flex justify-between text-xs text-muted-foreground mb-1">
              <span>Progress</span>
              <span>{progress}%</span>
            </div>
            <Progress
              value={progress}
              className="h-2"
              indicatorClassName={progressColors[status]}
            />
          </div>
        </CardFooter>
      </Card>
    </motion.div>
  );
};

