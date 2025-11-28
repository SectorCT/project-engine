import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
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
import { ArrowLeft, ArrowRight, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

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
  { id: 1, name: "Project Idea" },
  { id: 2, name: "Configuration" },
  { id: 3, name: "Preview" },
  { id: 4, name: "Launch" },
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

  const handleLaunch = () => {
    // Mock project creation - navigate to live build
    navigate("/project/1");
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
      return formData.name.length > 0 && formData.description.length >= 20;
    }
    return true;
  };

  return (
    <div className="min-h-screen bg-background p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Progress Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div
                    className={cn(
                      "w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-colors",
                      currentStep >= step.id
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    {currentStep > step.id ? "✓" : step.id}
                  </div>
                  <span className="mt-2 text-xs text-center text-muted-foreground">
                    {step.name}
                  </span>
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={cn(
                      "h-1 flex-1 mx-2 transition-colors",
                      currentStep > step.id ? "bg-primary" : "bg-muted"
                    )}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        <Card className="glass">
          <CardHeader>
            <CardTitle>Step {currentStep}: {steps[currentStep - 1].name}</CardTitle>
          </CardHeader>
          <CardContent>
            <AnimatePresence mode="wait">
              {/* Step 1: Project Idea */}
              {currentStep === 1 && (
                <motion.div
                  key="step1"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-6"
                >
                  <div className="space-y-2">
                    <Label htmlFor="name">Project Name</Label>
                    <Input
                      id="name"
                      placeholder="My Awesome App"
                      value={formData.name}
                      onChange={(e) =>
                        updateFormData({ name: e.target.value })
                      }
                      maxLength={50}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">Project Description</Label>
                    <Textarea
                      id="description"
                      placeholder="Describe what you want to build... Be as detailed as possible."
                      value={formData.description}
                      onChange={(e) =>
                        updateFormData({ description: e.target.value })
                      }
                      rows={8}
                      minLength={20}
                    />
                    <p className="text-xs text-muted-foreground">
                      Minimum 20 characters. {formData.description.length}/20
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label>Example Prompts</Label>
                    <div className="flex flex-wrap gap-2">
                      {examplePrompts.map((prompt, index) => (
                        <Badge
                          key={index}
                          variant="outline"
                          className="cursor-pointer hover:bg-primary/10"
                          onClick={() =>
                            updateFormData({ description: prompt })
                          }
                        >
                          {prompt}
                        </Badge>
                      ))}
                    </div>
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
                  className="space-y-6"
                >
                  <div className="space-y-3">
                    <Label>Platform</Label>
                    <RadioGroup
                      value={formData.platform}
                      onValueChange={(value: "web" | "mobile" | "desktop") =>
                        updateFormData({ platform: value })
                      }
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="web" id="web" />
                        <Label htmlFor="web" className="cursor-pointer">
                          Web App
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="mobile" id="mobile" />
                        <Label htmlFor="mobile" className="cursor-pointer">
                          Mobile App
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="desktop" id="desktop" />
                        <Label htmlFor="desktop" className="cursor-pointer">
                          Desktop App
                        </Label>
                      </div>
                    </RadioGroup>
                  </div>

                  <div className="space-y-3">
                    <Label>Tech Stack</Label>
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
                                className="cursor-pointer"
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

                  <div className="space-y-2">
                    <Label>Complexity</Label>
                    <Select
                      value={formData.complexity}
                      onValueChange={(value: "simple" | "medium" | "complex") =>
                        updateFormData({ complexity: value })
                      }
                    >
                      <SelectTrigger>
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
                    <Label>Features</Label>
                    <div className="space-y-2">
                      {[
                        "Authentication",
                        "Payment Processing",
                        "Real-time Updates",
                        "File Upload",
                        "Email Notifications",
                        "Admin Dashboard",
                      ].map((feature) => (
                        <div key={feature} className="flex items-center space-x-2">
                          <Checkbox
                            id={feature}
                            checked={formData.features.includes(feature)}
                            onCheckedChange={() => toggleFeature(feature)}
                          />
                          <Label
                            htmlFor={feature}
                            className="cursor-pointer font-normal"
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
                  className="space-y-6"
                >
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-semibold mb-2">Project Summary</h3>
                      <div className="bg-muted/30 p-4 rounded-lg space-y-2 text-sm">
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
                      <h3 className="font-semibold mb-2">Agents</h3>
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
                            className="flex items-center gap-2 p-2 bg-muted/30 rounded"
                          >
                            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-xs font-semibold">
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
                  className="space-y-6"
                >
                  <div className="text-center space-y-4">
                    <div className="flex justify-center">
                      <Sparkles className="w-16 h-16 text-primary" />
                    </div>
                    <h3 className="text-2xl font-semibold">
                      Ready to Start Building?
                    </h3>
                    <p className="text-muted-foreground">
                      Your project will be created and AI agents will begin
                      working immediately.
                    </p>
                  </div>
                  <div className="bg-muted/30 p-4 rounded-lg space-y-2 text-sm">
                    <p>
                      <span className="font-medium">Estimated Time:</span>{" "}
                      {formData.complexity === "simple"
                        ? "1-2 weeks"
                        : formData.complexity === "medium"
                        ? "2-4 weeks"
                        : "4+ weeks"}
                    </p>
                    <p>
                      <span className="font-medium">Estimated Cost:</span> $50-200
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
            <div className="flex justify-between mt-8 pt-6 border-t border-border">
              <Button
                variant="outline"
                onClick={handleBack}
                disabled={currentStep === 1}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              {currentStep < 4 ? (
                <Button onClick={handleNext} disabled={!canProceed()}>
                  Next
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              ) : (
                <Button onClick={handleLaunch} size="lg">
                  <Sparkles className="w-4 h-4 mr-2" />
                  Start Building
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

