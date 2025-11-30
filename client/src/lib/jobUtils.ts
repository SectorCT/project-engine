import { Job } from './api';

// Map server statuses to client statuses
export type ClientJobStatus = 'planning' | 'building' | 'testing' | 'complete' | 'failed';

export function mapServerStatusToClient(serverStatus: Job['status']): ClientJobStatus {
  const statusMap: Partial<Record<Job['status'], ClientJobStatus>> = {
    collecting: 'planning',
    queued: 'planning',
    planning: 'planning',
    prd_ready: 'planning',
    ticketing: 'planning',
    tickets_ready: 'planning',
    building: 'building',
    running: 'building',
    build_done: 'complete',
    done: 'complete',
    failed: 'failed',
  };
  return statusMap[serverStatus] || 'planning';
}

export function calculateProgress(job: Job): number {
  // Calculate progress based on status
  switch (job.status) {
    case 'collecting':
      return 5;
    case 'queued':
      return 10;
    case 'planning':
      return 20;
    case 'prd_ready':
      return 30;
    case 'ticketing':
      return 40;
    case 'tickets_ready':
      return 50;
    case 'building':
      // If we have steps, calculate based on steps
      if (job.steps && job.steps.length > 0) {
        // Rough estimate: 50% base + up to 50% based on steps (assuming ~10 steps total)
        return Math.min(50 + (job.steps.length * 5), 95);
      }
      return 50;
    case 'build_done':
    case 'done':
      return 100;
    case 'failed':
      // For failed jobs, show progress up to the point of failure
      // If we have steps, show progress based on completed work
      if (job.steps && job.steps.length > 0) {
        return Math.min(50 + (job.steps.length * 5), 95);
      }
      // Otherwise show minimal progress to indicate it started
      return 10;
    default:
      return 0;
  }
}

export function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) {
    return 'just now';
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
  } else {
    const days = Math.floor(diffInSeconds / 86400);
    return `${days} day${days !== 1 ? 's' : ''} ago`;
  }
}

export function extractTechStack(job: Job): string[] {
  // Try to extract tech stack from prompt or requirements
  const text = (job.requirements_summary || job.prompt || '').toLowerCase();
  const techKeywords = [
    'react', 'vue', 'angular', 'next.js', 'svelte',
    'node.js', 'python', 'django', 'flask', 'express', 'ruby', 'go', 'rust',
    'postgresql', 'mongodb', 'mysql', 'redis',
    'typescript', 'javascript', 'tailwind', 'css', 'html',
  ];
  
  const found: string[] = [];
  for (const tech of techKeywords) {
    if (text.includes(tech)) {
      found.push(tech.charAt(0).toUpperCase() + tech.slice(1));
    }
  }
  
  return found.slice(0, 6); // Limit to 6 items
}

