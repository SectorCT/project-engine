import React, { createContext, useContext, useEffect, useLayoutEffect, useState } from "react";

type Theme = "dark" | "light" | "system";
type ColorScheme = "default" | "blue" | "green" | "purple";

interface ThemeContextType {
  theme: Theme;
  colorScheme: ColorScheme;
  setTheme: (theme: Theme) => void;
  setColorScheme: (scheme: ColorScheme) => void;
  resolvedTheme: "dark" | "light";
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem("theme");
    return (saved as Theme) || "dark";
  });

  const [colorScheme, setColorSchemeState] = useState<ColorScheme>(() => {
    const saved = localStorage.getItem("colorScheme");
    return (saved as ColorScheme) || "default";
  });

  const getSystemTheme = (): "dark" | "light" => {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };

  const resolvedTheme: "dark" | "light" = theme === "system" ? getSystemTheme() : theme;

  // Apply theme immediately on mount to prevent flash
  useLayoutEffect(() => {
    const root = document.documentElement;
    const initialTheme = (() => {
      const saved = localStorage.getItem("theme");
      return (saved as Theme) || "dark";
    })();
    const initialResolvedTheme = initialTheme === "system" ? getSystemTheme() : initialTheme;
    
    if (initialResolvedTheme === "light") {
      root.classList.add("light");
    } else {
      root.classList.remove("light");
    }
    
    const savedColorScheme = localStorage.getItem("colorScheme") || "default";
    root.setAttribute("data-color-scheme", savedColorScheme);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    
    // Apply theme class based on resolved theme
    if (resolvedTheme === "light") {
      root.classList.add("light");
    } else {
      root.classList.remove("light");
    }

    // Apply color scheme
    root.setAttribute("data-color-scheme", colorScheme);

    // Save to localStorage
    localStorage.setItem("theme", theme);
    localStorage.setItem("colorScheme", colorScheme);
  }, [theme, colorScheme, resolvedTheme]);

  // Listen for system theme changes
  useEffect(() => {
    if (theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleChange = () => {
        const root = document.documentElement;
        const newResolvedTheme = mediaQuery.matches ? "dark" : "light";
        if (newResolvedTheme === "light") {
          root.classList.add("light");
        } else {
          root.classList.remove("light");
        }
      };
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }
  }, [theme]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  const setColorScheme = (newScheme: ColorScheme) => {
    setColorSchemeState(newScheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, colorScheme, setTheme, setColorScheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};

