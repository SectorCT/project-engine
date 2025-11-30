import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import React from "react";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Parse text and convert URLs to clickable links
 * Returns an array of React elements (strings and anchor tags)
 */
export function parseUrls(text: string): (string | React.ReactElement)[] {
  // URL regex pattern - matches http://, https://, and optionally www.
  const urlRegex = /(https?:\/\/[^\s]+|www\.[^\s]+)/gi;
  const parts: (string | React.ReactElement)[] = [];
  let lastIndex = 0;
  let match;
  let key = 0;

  while ((match = urlRegex.exec(text)) !== null) {
    // Add text before the URL
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    // Add the URL as a clickable link
    let url = match[0];
    // Add http:// if it's a www. URL
    if (url.startsWith('www.')) {
      url = `http://${url}`;
    }

    parts.push(
      React.createElement(
        'a',
        {
          key: `link-${key++}`,
          href: url,
          target: '_blank',
          rel: 'noopener noreferrer',
          className: 'text-primary hover:underline break-all'
        },
        match[0]
      )
    );

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text after the last URL
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  // If no URLs were found, return the original text as a string
  return parts.length > 0 ? parts : [text];
}

