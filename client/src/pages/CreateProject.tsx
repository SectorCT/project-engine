import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Navbar } from "@/components/Navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { ArrowLeft, ArrowRight, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { toast } from "sonner";

interface ProjectFormData {
  description: string;
  agreedToTerms: boolean;
}

const examplePrompts = [
  "A task management app with teams, projects, and real-time collaboration",
  "An e-commerce platform with inventory management and payment processing",
  "A social media dashboard with analytics and scheduling features",
];

const steps = [
  { id: 1, name: "Project Idea", description: "Describe what you want to build" },
  { id: 2, name: "Confirm & Launch", description: "Review and start building" },
];

export default function CreateProject() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<ProjectFormData>({
    description: "",
    agreedToTerms: false,
  });

  const updateFormData = (updates: Partial<ProjectFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  };

  const handleNext = () => {
    if (currentStep < 2) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleLaunch = async () => {
    if (!formData.description.trim()) {
      toast.error("Please provide a project description");
      return;
    }

    if (!formData.agreedToTerms) {
      toast.error("You must agree to the terms of service to proceed");
      return;
    }

    setIsSubmitting(true);
    try {
      const job = await api.createJob(formData.description.trim());
      toast.success("Project created successfully!");
      navigate(`/project/${job.id}`);
    } catch (error: any) {
      toast.error(error?.detail || error?.message || "Failed to create project");
    } finally {
      setIsSubmitting(false);
    }
  };


  const canProceed = () => {
    if (currentStep === 1) {
      return formData.description.length >= 20;
    }
    return true;
  };

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      <Navbar />
      <div className="flex-1 p-4 lg:p-6 overflow-hidden">
        <div className="max-w-6xl mx-auto h-full flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between mb-4 flex-shrink-0">
            <div className="flex items-center gap-3">
              <img 
                src="/projectEngineICON.png" 
                alt="Project Engine" 
                className="h-8 w-8"
              />
              <div>
                <h1 className="text-xl font-semibold">Create New Project</h1>
                <p className="text-xs text-muted-foreground">
                  Step {currentStep} of 2
                </p>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
              Cancel
            </Button>
          </div>

          {/* Progress Indicator */}
          <div className="mb-4 flex-shrink-0">
            <div className="flex items-center justify-between">
              {steps.map((step, index) => (
                <div key={step.id} className="flex items-center flex-1">
                  <div className="flex flex-col items-center flex-1">
                    <div
                      className={cn(
                        "w-12 h-12 rounded-full flex items-center justify-center font-semibold transition-all relative",
                        currentStep >= step.id
                          ? "bg-gradient-primary text-primary-foreground shadow-lg ring-2 ring-foreground/10"
                          : "bg-muted text-muted-foreground border-2 border-border"
                      )}
                    >
                      {currentStep > step.id ? (
                        <span className="text-lg">✓</span>
                      ) : (
                        <span className={cn(
                          currentStep >= step.id ? "text-primary-foreground" : ""
                        )}>
                          {step.id}
                        </span>
                      )}
                    </div>
                    <div className="mt-3 text-center">
                      <p className={cn(
                        "text-sm font-medium transition-colors",
                        currentStep >= step.id ? "text-foreground" : "text-muted-foreground"
                      )}>
                        {step.name}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {step.description}
                      </p>
                    </div>
                  </div>
                  {index < steps.length - 1 && (
                    <div className="flex-1 mx-4 relative">
                      <div className="absolute inset-0 flex items-center">
                        <div className="h-0.5 w-full bg-muted"></div>
                      </div>
                      <div
                        className={cn(
                          "h-0.5 transition-all duration-500 ease-out",
                          currentStep > step.id ? "bg-gradient-primary w-full" : "w-0"
                        )}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

        <Card className="glass glow-card flex-1 flex flex-col min-h-0 border-border/50">
          <CardHeader className="flex-shrink-0 pb-4 border-b border-border/50">
            <CardTitle className="text-xl font-semibold">Step {currentStep}: {steps[currentStep - 1].name}</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto p-6">
            <AnimatePresence mode="wait">
              {/* Step 1: Project Idea */}
              {currentStep === 1 && (
                <motion.div
                  key="step1"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-4"
                >
                  <div className="space-y-3 mb-6">
                    <h2 className="text-3xl font-bold tracking-tight">What do you want to build?</h2>
                    <p className="text-base text-muted-foreground leading-relaxed">
                      Describe your project idea in detail. The more specific you are, the better our AI agents can help.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Textarea
                      id="description"
                      placeholder="Example: A real-time collaborative task management app with team workspaces, drag-and-drop kanban boards, integrated chat, and mobile responsiveness. Users should be able to assign tasks, set due dates, and receive notifications."
                      value={formData.description}
                      onChange={(e) =>
                        updateFormData({ description: e.target.value })
                      }
                      rows={8}
                      minLength={20}
                      className="text-sm resize-none bg-input/50 border-border/50 focus:border-border focus:ring-2 focus:ring-ring/20 transition-all"
                    />
                  </div>
                  <div className="space-y-3 pt-6 border-t border-border/50">
                    <div className="flex items-center gap-2">
                      <Lightbulb className="w-5 h-5 text-warning" />
                      <Label className="text-sm font-semibold">Example Prompts</Label>
                    </div>
                    <ul className="space-y-2.5">
                      {examplePrompts.map((prompt, index) => (
                        <li
                          key={index}
                          className="cursor-pointer p-3 rounded-lg bg-muted/30 border border-border/30 hover:bg-muted/50 hover:border-border/50 transition-all text-sm text-muted-foreground hover:text-foreground"
                          onClick={() =>
                            updateFormData({ description: prompt })
                          }
                        >
                          {prompt}
                        </li>
                      ))}
                    </ul>
                  </div>
                </motion.div>
              )}

              {/* Step 2: Confirm & Launch */}
              {currentStep === 2 && (
                <motion.div
                  key="step4"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-4"
                >
                  <div className="text-center space-y-3">
                    <div className="flex justify-center">
                      <img 
                        src="/logo.png" 
                        alt="Project Engine" 
                        className="h-12 w-auto"
                      />
                    </div>
                    <h3 className="text-xl font-semibold">
                      Ready to Start Building?
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      Your project will be created and AI agents will begin
                      working immediately.
                    </p>
                  </div>
                  
                  <div className="bg-muted/30 border border-border/30 p-4 rounded-lg space-y-3">
                    <h4 className="text-sm font-semibold">Project Description</h4>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                      {formData.description || "No description provided"}
                    </p>
                  </div>

                  <div className="flex items-start space-x-3 p-4 rounded-lg border border-border/50 bg-muted/20">
                    <Checkbox 
                      id="terms" 
                      checked={formData.agreedToTerms}
                      onCheckedChange={(checked) => 
                        updateFormData({ agreedToTerms: checked === true })
                      }
                      className="mt-0.5"
                    />
                    <Label htmlFor="terms" className="cursor-pointer text-sm leading-relaxed flex-1">
                      I agree to the{" "}
                      <a 
                        href="/terms" 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        terms of service
                      </a>
                      {" "}and understand that AI agents will work on my project.
                    </Label>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Navigation */}
            <div className="flex justify-between mt-6 pt-6 border-t border-border/50 flex-shrink-0">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleBack}
                disabled={currentStep === 1}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Cancel
              </Button>
              {currentStep < 2 ? (
                <Button 
                  onClick={handleNext} 
                  disabled={!canProceed()}
                  size="sm"
                  className="bg-gradient-primary text-primary-foreground font-medium shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              ) : (
                <Button 
                  onClick={handleLaunch} 
                  size="default"
                  className="bg-gradient-primary text-primary-foreground font-medium shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed px-6"
                  disabled={isSubmitting || !formData.agreedToTerms}
                >
                  <img 
                    src="/logo.png" 
                    alt="" 
                    className="w-4 h-4 mr-2"
                  />
                  {isSubmitting ? "Creating..." : "Start Building"}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
        </div>
      </div>
    </div>
  );
}

