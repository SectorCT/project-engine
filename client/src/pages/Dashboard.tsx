import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ProjectCard } from "@/components/ProjectCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Search } from "lucide-react";

interface Project {
  id: string;
  name: string;
  status: "planning" | "building" | "testing" | "complete" | "failed";
  progress: number;
  techStack: string[];
  createdAt: string;
  lastActivity: string;
}

const mockProjects: Project[] = [
  {
    id: "1",
    name: "E-commerce Platform",
    status: "building",
    progress: 68,
    techStack: ["React", "Node.js", "PostgreSQL", "Stripe"],
    createdAt: "2024-01-15",
    lastActivity: "2 hours ago",
  },
  {
    id: "2",
    name: "Task Management App",
    status: "complete",
    progress: 100,
    techStack: ["React", "Firebase", "Tailwind"],
    createdAt: "2024-01-10",
    lastActivity: "1 day ago",
  },
  {
    id: "3",
    name: "Social Dashboard",
    status: "testing",
    progress: 85,
    techStack: ["Next.js", "PostgreSQL", "Redis"],
    createdAt: "2024-01-12",
    lastActivity: "30 minutes ago",
  },
  {
    id: "4",
    name: "Blog Platform",
    status: "planning",
    progress: 15,
    techStack: ["Vue", "Express", "MongoDB"],
    createdAt: "2024-01-18",
    lastActivity: "5 minutes ago",
  },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filteredProjects = mockProjects.filter((project) => {
    const matchesSearch = project.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesFilter =
      statusFilter === "all" || project.status === statusFilter;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="min-h-screen bg-background p-6 lg:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h1 className="text-3xl font-bold">Projects</h1>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1 sm:w-64">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="planning">Planning</SelectItem>
                <SelectItem value="building">Building</SelectItem>
                <SelectItem value="testing">Testing</SelectItem>
                <SelectItem value="complete">Complete</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={() => navigate("/create")}
              className="w-full sm:w-auto"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create New Project
            </Button>
          </div>
        </div>

        {/* Projects Grid */}
        {filteredProjects.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProjects.map((project, index) => (
              <motion.div
                key={project.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <ProjectCard {...project} />
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <h2 className="text-2xl font-semibold mb-2">No projects found</h2>
            <p className="text-muted-foreground mb-6">
              {searchQuery || statusFilter !== "all"
                ? "Try adjusting your search or filters"
                : "Create your first project to get started"}
            </p>
            {!searchQuery && statusFilter === "all" && (
              <Button onClick={() => navigate("/create")}>
                <Plus className="w-4 h-4 mr-2" />
                Create Project
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

