import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ProjectCardProps {
  id: string;
  name: string;
  status: "planning" | "building" | "testing" | "complete" | "failed";
  progress: number;
  techStack: string[];
  createdAt: string;
  lastActivity: string;
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
}: ProjectCardProps) => {
  const navigate = useNavigate();

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => navigate(`/project/${id}`)}
      className="cursor-pointer"
    >
      <Card className="glass h-full transition-smooth hover:glow-primary">
        <CardContent className="p-6">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-semibold text-foreground">{name}</h3>
            <Badge className={cn("border", statusColors[status])}>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </Badge>
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

