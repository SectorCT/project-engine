import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Settings, FolderOpen, User } from "lucide-react";
import { Sparkles } from "lucide-react";

export const Navbar = () => {
  const navigate = useNavigate();

  return (
    <div className="border-b border-border bg-background-elevated">
      <div className="max-w-[1920px] mx-auto px-6 py-4 flex items-center justify-between">
        <div
          className="flex items-center gap-3 cursor-pointer"
          onClick={() => navigate("/dashboard")}
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">
              Project-Engine
            </h1>
            <p className="text-xs text-muted-foreground">
              AI Development Platform
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon">
            <Settings className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon">
            <FolderOpen className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => navigate("/profile")}>
            <User className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
};

