import { useMemo } from "react";
import { motion } from "framer-motion";
import { Ticket } from "@/lib/api";
import { cn } from "@/lib/utils";

interface BuildProgressIndicatorProps {
  tickets?: Ticket[];
  className?: string;
  jobStatus?: string;
  errorMessage?: string;
}

export const BuildProgressIndicator = ({ 
  tickets = [], 
  className, 
  jobStatus,
  errorMessage 
}: BuildProgressIndicatorProps) => {
  // Generate unique ID for gradient to avoid conflicts
  const gradientId = useMemo(() => `progressGradient-${Math.random().toString(36).substr(2, 9)}`, []);
  
  const isFailed = jobStatus === 'failed';
  
  // Determine the current phase and appropriate message
  const phaseInfo = useMemo(() => {
    switch (jobStatus) {
      case 'collecting':
        return {
          message: 'Waiting for your input',
          description: 'Please provide more details about your project in the chat below',
          icon: '💬',
          showProgress: false,
          progress: 0,
        };
      case 'queued':
        return {
          message: 'Job queued',
          description: 'Your project is in the queue and will start soon',
          icon: '⏳',
          showProgress: false,
          progress: 5,
        };
      case 'planning':
        return {
          message: 'Planning in progress',
          description: 'The executive team is designing your project architecture',
          icon: '🤔',
          showProgress: false,
          progress: 15,
        };
      case 'prd_ready':
        return {
          message: 'PRD ready',
          description: 'Product Requirements Document has been finalized',
          icon: '📋',
          showProgress: false,
          progress: 30,
        };
      case 'ticketing':
        return {
          message: 'Creating tickets',
          description: 'Breaking down the work into actionable tickets',
          icon: '🎫',
          showProgress: false,
          progress: 40,
        };
      case 'tickets_ready':
        return {
          message: 'Tickets ready',
          description: 'All tickets have been created. Build starting soon...',
          icon: '✅',
          showProgress: false,
          progress: 50,
        };
      case 'building':
        // Show actual progress based on tickets
        const workTickets = tickets.filter(t => t.type !== 'epic');
        if (workTickets.length === 0) {
          return {
            message: 'Building in progress',
            description: 'Starting the build process...',
            icon: '🔨',
            showProgress: true,
            progress: 50,
          };
        }
        const completed = workTickets.filter(t => t.status === 'done' || t.status === 'completed').length;
        const percentage = Math.round((completed / workTickets.length) * 100);
        return {
          message: 'Building your application',
          description: 'Tickets are being executed',
          icon: '🔨',
          showProgress: true,
          progress: Math.min(percentage, 100),
        };
      case 'build_done':
      case 'done':
        return {
          message: 'Build complete!',
          description: 'Your application has been successfully built',
          icon: '🎉',
          showProgress: true,
          progress: 100,
        };
      default:
        return {
          message: 'Initializing',
          description: 'Setting up your project...',
          icon: '🚀',
          showProgress: false,
          progress: 0,
        };
    }
  }, [jobStatus, tickets]);

  const progress = useMemo(() => {
    // If we have tickets and are building, calculate from tickets
    if (jobStatus === 'building' && tickets && tickets.length > 0) {
      const workTickets = tickets.filter(t => t.type !== 'epic');
      if (workTickets.length > 0) {
        const completed = workTickets.filter(t => t.status === 'done' || t.status === 'completed').length;
        return Math.round((completed / workTickets.length) * 100);
      }
    }
    return phaseInfo.progress;
  }, [tickets, jobStatus, phaseInfo]);

  const completedTickets = useMemo(() => {
    if (!tickets || tickets.length === 0) return 0;
    const workTickets = tickets.filter(t => t.type !== 'epic');
    return workTickets.filter(t => t.status === 'done' || t.status === 'completed').length;
  }, [tickets]);

  const totalTickets = useMemo(() => {
    if (!tickets || tickets.length === 0) return 0;
    return tickets.filter(t => t.type !== 'epic').length;
  }, [tickets]);

  if (isFailed) {
    return (
      <div className={cn("relative w-full h-full flex items-center justify-center", className)}>
        {/* Blurred Background Overlay with glass effect */}
        <div className="absolute inset-0 backdrop-blur-xl bg-background/40 border border-border/50 rounded-lg" />
        
        {/* Failed State Content */}
        <div className="relative z-10 flex flex-col items-center justify-center">
          {/* Glass card container */}
          <div className="glass rounded-2xl p-8 md:p-12 border border-status-failed/30 shadow-2xl flex flex-col items-center max-w-lg">
            {/* Error Icon */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8, rotate: -180 }}
              animate={{ opacity: 1, scale: 1, rotate: 0 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              className="w-24 h-24 md:w-32 md:h-32 rounded-full bg-status-failed/20 flex items-center justify-center mb-6"
            >
              <motion.div
                animate={{ 
                  scale: [1, 1.1, 1],
                }}
                transition={{ 
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
                className="text-5xl md:text-6xl"
              >
                ❌
              </motion.div>
            </motion.div>

            {/* Error Title */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.5 }}
              className="text-center mb-4"
            >
              <h2 className="text-3xl md:text-4xl font-bold text-status-failed mb-2">
                Build Failed
              </h2>
              <p className="text-lg text-muted-foreground">
                The build process encountered an error
              </p>
            </motion.div>

            {/* Error Message */}
            {errorMessage && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, duration: 0.5 }}
                className="mt-4 p-4 bg-status-failed/10 border border-status-failed/30 rounded-lg w-full"
              >
                <p className="text-sm text-foreground font-mono whitespace-pre-wrap break-words">
                  {errorMessage}
                </p>
              </motion.div>
            )}

            {/* Stats (if tickets exist) */}
            {totalTickets > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6, duration: 0.5 }}
                className="mt-6 text-center space-y-2"
              >
                <div className="text-lg md:text-xl font-semibold text-foreground">
                  {completedTickets} of {totalTickets} tickets completed before failure
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("relative w-full h-full flex items-center justify-center", className)}>
      {/* Blurred Background Overlay with glass effect */}
      <div className="absolute inset-0 backdrop-blur-xl bg-background/40 border border-border/50 rounded-lg" />
      
      {/* Progress Content */}
      <div className="relative z-10 flex flex-col items-center justify-center">
        {/* Glass card container */}
        <div className="glass rounded-2xl p-8 md:p-12 border border-border/50 shadow-2xl flex flex-col items-center">
          {/* Circular Progress Ring */}
          <div className="relative w-48 h-48 md:w-64 md:h-64">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 200 200">
              {/* Background Circle */}
              <circle
                cx="100"
                cy="100"
                r="85"
                stroke="currentColor"
                strokeWidth="12"
                fill="none"
                className="text-muted/20"
              />
              {/* Progress Circle */}
              <motion.circle
                cx="100"
                cy="100"
                r="85"
                stroke={`url(#${gradientId})`}
                strokeWidth="12"
                fill="none"
                strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * 85}`}
                initial={{ strokeDashoffset: 2 * Math.PI * 85 }}
                animate={{ 
                  strokeDashoffset: 2 * Math.PI * 85 * (1 - progress / 100),
                  opacity: phaseInfo.showProgress ? 1 : 0.3
                }}
                transition={{ duration: 1.5, ease: "easeOut" }}
              />
              {/* Gradient Definition */}
              <defs>
                <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="hsl(var(--primary))" />
                  <stop offset="50%" stopColor="hsl(var(--primary))" stopOpacity={0.8} />
                  <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.6} />
                </linearGradient>
              </defs>
            </svg>
            
            {/* Center Content */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2, duration: 0.5 }}
                className="text-center px-4"
              >
                {phaseInfo.showProgress ? (
                  <>
                    <motion.div
                      key={progress}
                      initial={{ scale: 1.2, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ duration: 0.3 }}
                      className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent"
                    >
                      {progress}%
                    </motion.div>
                    <div className="text-sm md:text-base text-muted-foreground mt-2 font-medium">
                      Complete
                    </div>
                  </>
                ) : (
                  <>
                    <motion.div
                      animate={jobStatus === 'collecting' ? {
                        scale: [1, 1.1, 1],
                      } : {}}
                      transition={{
                        duration: 2,
                        repeat: jobStatus === 'collecting' ? Infinity : 0,
                        ease: "easeInOut"
                      }}
                      className="text-4xl md:text-5xl mb-2"
                    >
                      {phaseInfo.icon}
                    </motion.div>
                    <div className="text-lg md:text-xl font-semibold text-foreground">
                      {phaseInfo.message}
                    </div>
                    <div className="text-xs md:text-sm text-muted-foreground mt-1 max-w-xs">
                      {phaseInfo.description}
                    </div>
                  </>
                )}
              </motion.div>
            </div>
          </div>

          {/* Stats - Only show when building with tickets */}
          {phaseInfo.showProgress && totalTickets > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.5 }}
              className="mt-8 text-center space-y-2"
            >
              <div className="text-lg md:text-xl font-semibold text-foreground">
                {completedTickets} of {totalTickets} tickets completed
              </div>
              <div className="text-sm text-muted-foreground">
                {totalTickets - completedTickets} remaining
              </div>
            </motion.div>
          )}

          {/* Animated Dots - Show when not in collecting phase */}
          {jobStatus !== 'collecting' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
              className="flex gap-2 mt-6 justify-center"
            >
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-2 h-2 rounded-full bg-primary"
                  animate={{
                    scale: [1, 1.5, 1],
                    opacity: [0.5, 1, 0.5],
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    delay: i * 0.2,
                  }}
                />
              ))}
            </motion.div>
          )}

          {/* Special message for collecting phase */}
          {jobStatus === 'collecting' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.5 }}
              className="mt-6 p-4 bg-primary/10 border border-primary/20 rounded-lg text-center max-w-md"
            >
              <p className="text-sm text-foreground font-medium">
                💡 Tip: Use the chat panel below to provide more details about your project requirements
              </p>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};

