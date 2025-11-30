import { Job } from './api';

// Map server statuses to client statuses
export type ClientJobStatus = 'planning' | 'ticketing' | 'building' | 'complete' | 'failed';

export function mapServerStatusToClient(serverStatus: Job['status']): ClientJobStatus {
  const statusMap: Record<Job['status'], ClientJobStatus> = {
    collecting: 'planning',
    queued: 'planning',
    planning: 'planning',
    prd_ready: 'planning',
    ticketing: 'ticketing',
    tickets_ready: 'ticketing',
    building: 'building',
    running: 'building',
    build_done: 'complete',
    done: 'complete',
    failed: 'failed',
  } as any;
  return statusMap[serverStatus] || 'planning';
}

export function calculateProgress(job: Job): number {
  switch (job.status) {
    case 'collecting':
      return 5;
    case 'queued':
    case 'planning':
      return 15;
    case 'prd_ready':
      return 30;
    case 'ticketing':
      return 45;
    case 'tickets_ready':
      return 55;
    case 'building':
    case 'running':
      return job.steps && job.steps.length > 0
        ? Math.min(55 + job.steps.length * 5, 90)
        : 70;
    case 'build_done':
    case 'done':
      return 100;
    case 'failed':
      return 0;
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

