import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Navbar } from "@/components/Navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ArrowRight, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { toast } from "sonner";

interface ProjectFormData {
  name: string;
  description: string;
  platform: "web" | "mobile" | "desktop";
  techStack: {
    frontend: string[];
    backend: string[];
    database: string[];
    other: string[];
  };
  complexity: "simple" | "medium" | "complex";
  features: string[];
}

const examplePrompts = [
  "A task management app with teams, projects, and real-time collaboration",
  "An e-commerce platform with inventory management and payment processing",
  "A social media dashboard with analytics and scheduling features",
];

const steps = [
  { id: 1, name: "Project Idea", description: "Describe what you want to build" },
  { id: 2, name: "Configuration", description: "Choose your tech preferences" },
  { id: 3, name: "Agent Assignment", description: "Review your AI team" },
  { id: 4, name: "Confirm & Launch", description: "Start building" },
];

export default function CreateProject() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<ProjectFormData>({
    name: "",
    description: "",
    platform: "web",
    techStack: {
      frontend: [],
      backend: [],
      database: [],
      other: [],
    },
    complexity: "medium",
    features: [],
  });

  const updateFormData = (updates: Partial<ProjectFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  };

  const handleNext = () => {
    if (currentStep < 4) {
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

    setIsSubmitting(true);
    try {
      // Build a comprehensive prompt from the form data
      let prompt = formData.description;
      
      // Add configuration details to the prompt
      if (formData.platform) {
        prompt += `\n\nPlatform: ${formData.platform}`;
      }
      if (formData.complexity) {
        prompt += `\n\nComplexity: ${formData.complexity}`;
      }
      if (formData.techStack.frontend.length > 0) {
        prompt += `\n\nPreferred Frontend: ${formData.techStack.frontend.join(', ')}`;
      }
      if (formData.techStack.backend.length > 0) {
        prompt += `\n\nPreferred Backend: ${formData.techStack.backend.join(', ')}`;
      }
      if (formData.techStack.database.length > 0) {
        prompt += `\n\nPreferred Database: ${formData.techStack.database.join(', ')}`;
      }
      if (formData.features.length > 0) {
        prompt += `\n\nRequired Features: ${formData.features.join(', ')}`;
      }

      const job = await api.createJob(prompt);
      toast.success("Project created successfully!");
      navigate(`/project/${job.id}`);
    } catch (error: any) {
      toast.error(error?.detail || error?.message || "Failed to create project");
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleTechStack = (
    category: keyof ProjectFormData["techStack"],
    value: string
  ) => {
    setFormData((prev) => {
      const current = prev.techStack[category];
      const updated = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      return {
        ...prev,
        techStack: { ...prev.techStack, [category]: updated },
      };
    });
  };

  const toggleFeature = (feature: string) => {
    setFormData((prev) => ({
      ...prev,
      features: prev.features.includes(feature)
        ? prev.features.filter((f) => f !== feature)
        : [...prev.features, feature],
    }));
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
                src="/logo.png" 
                alt="Project Engine" 
                className="h-8 w-auto"
              />
              <div>
                <h1 className="text-xl font-semibold">Create New Project</h1>
                <p className="text-xs text-muted-foreground">
                  Step {currentStep} of 4
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

              {/* Step 2: Configuration */}
              {currentStep === 2 && (
                <motion.div
                  key="step2"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-4"
                >
                  <div className="space-y-3">
                    <Label className="text-sm font-semibold">Platform</Label>
                    <RadioGroup
                      value={formData.platform}
                      onValueChange={(value: "web" | "mobile" | "desktop") =>
                        updateFormData({ platform: value })
                      }
                      className="space-y-2"
                    >
                      <div className="flex items-center space-x-3 p-3 rounded-lg border border-border/30 hover:bg-muted/30 transition-colors cursor-pointer">
                        <RadioGroupItem value="web" id="web" />
                        <Label htmlFor="web" className="cursor-pointer font-normal">
                          Web App
                        </Label>
                      </div>
                      <div className="flex items-center space-x-3 p-3 rounded-lg border border-border/30 hover:bg-muted/30 transition-colors cursor-pointer">
                        <RadioGroupItem value="mobile" id="mobile" />
                        <Label htmlFor="mobile" className="cursor-pointer font-normal">
                          Mobile App
                        </Label>
                      </div>
                      <div className="flex items-center space-x-3 p-3 rounded-lg border border-border/30 hover:bg-muted/30 transition-colors cursor-pointer">
                        <RadioGroupItem value="desktop" id="desktop" />
                        <Label htmlFor="desktop" className="cursor-pointer font-normal">
                          Desktop App
                        </Label>
                      </div>
                    </RadioGroup>
                  </div>

                  <div className="space-y-3">
                    <Label className="text-sm font-semibold">Tech Stack</Label>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label className="text-sm">Frontend</Label>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {["React", "Vue", "Next.js", "Angular"].map(
                            (tech) => (
                              <Badge
                                key={tech}
                                variant={
                                  formData.techStack.frontend.includes(tech)
                                    ? "default"
                                    : "outline"
                                }
                                className="cursor-pointer transition-all font-normal border-border/50"
                                onClick={() =>
                                  toggleTechStack("frontend", tech)
                                }
                              >
                                {tech}
                              </Badge>
                            )
                          )}
                        </div>
                      </div>
                      <div>
                        <Label className="text-sm">Backend</Label>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {["Node.js", "Python", "Ruby", "Go"].map((tech) => (
                            <Badge
                              key={tech}
                              variant={
                                formData.techStack.backend.includes(tech)
                                  ? "default"
                                  : "outline"
                              }
                              className="cursor-pointer"
                              onClick={() => toggleTechStack("backend", tech)}
                            >
                              {tech}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <Label className="text-sm">Database</Label>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {["PostgreSQL", "MongoDB", "MySQL"].map((tech) => (
                            <Badge
                              key={tech}
                              variant={
                                formData.techStack.database.includes(tech)
                                  ? "default"
                                  : "outline"
                              }
                              className="cursor-pointer"
                              onClick={() => toggleTechStack("database", tech)}
                            >
                              {tech}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <Label className="text-sm">Other</Label>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {["TypeScript", "Tailwind CSS"].map((tech) => (
                            <Badge
                              key={tech}
                              variant={
                                formData.techStack.other.includes(tech)
                                  ? "default"
                                  : "outline"
                              }
                              className="cursor-pointer"
                              onClick={() => toggleTechStack("other", tech)}
                            >
                              {tech}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <Label className="text-sm font-semibold">Complexity</Label>
                    <Select
                      value={formData.complexity}
                      onValueChange={(value: "simple" | "medium" | "complex") =>
                        updateFormData({ complexity: value })
                      }
                    >
                      <SelectTrigger className="bg-input/50 border-border/50">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="simple">
                          Simple - Basic CRUD, 1-2 weeks
                        </SelectItem>
                        <SelectItem value="medium">
                          Medium - Multiple features, 2-4 weeks
                        </SelectItem>
                        <SelectItem value="complex">
                          Complex - Advanced features, 4+ weeks
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-3">
                    <Label className="text-sm font-semibold">Features</Label>
                    <div className="space-y-2">
                      {[
                        "Authentication",
                        "Payment Processing",
                        "Real-time Updates",
                        "File Upload",
                        "Email Notifications",
                        "Admin Dashboard",
                      ].map((feature) => (
                        <div key={feature} className="flex items-center space-x-3 p-2 rounded-lg hover:bg-muted/30 transition-colors cursor-pointer">
                          <Checkbox
                            id={feature}
                            checked={formData.features.includes(feature)}
                            onCheckedChange={() => toggleFeature(feature)}
                          />
                          <Label
                            htmlFor={feature}
                            className="cursor-pointer font-normal flex-1"
                          >
                            {feature}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Step 3: Preview */}
              {currentStep === 3 && (
                <motion.div
                  key="step3"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-4"
                >
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-sm font-semibold mb-3">Project Summary</h3>
                      <div className="bg-muted/30 border border-border/30 p-4 rounded-lg space-y-2 text-sm">
                        <p>
                          <span className="font-medium">Name:</span>{" "}
                          {formData.name}
                        </p>
                        <p>
                          <span className="font-medium">Platform:</span>{" "}
                          {formData.platform}
                        </p>
                        <p>
                          <span className="font-medium">Complexity:</span>{" "}
                          {formData.complexity}
                        </p>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold mb-3">Agents</h3>
                      <div className="space-y-2">
                        {[
                          "Business Analyst",
                          "Project Manager",
                          "Architect",
                          "Developers (1-3)",
                          "QA Tester",
                        ].map((role) => (
                          <div
                            key={role}
                            className="flex items-center gap-3 p-3 bg-muted/30 border border-border/30 rounded-lg"
                          >
                            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-xs font-semibold text-primary">
                              {role.charAt(0)}
                            </div>
                            <span className="text-sm">{role}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Step 4: Launch */}
              {currentStep === 4 && (
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
                  <div className="bg-muted/30 border border-border/30 p-4 rounded-lg space-y-2 text-sm">
                    <p>
                      <span className="font-semibold">Estimated Time:</span>{" "}
                      {formData.complexity === "simple"
                        ? "1-2 weeks"
                        : formData.complexity === "medium"
                        ? "2-4 weeks"
                        : "4+ weeks"}
                    </p>
                    <p>
                      <span className="font-semibold">Estimated Cost:</span> $50-200
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox id="terms" />
                    <Label htmlFor="terms" className="cursor-pointer text-sm">
                      I agree to the terms of service
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
              {currentStep < 4 ? (
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
                  disabled={isSubmitting}
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

