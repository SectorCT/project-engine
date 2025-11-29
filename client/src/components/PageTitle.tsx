import { useLayoutEffect } from "react";
import { useLocation } from "react-router-dom";

const routeTitleMap: Record<string, string> = {
  "/": "Home",
  "/login": "Login",
  "/register": "Register",
  "/dashboard": "Dashboard",
  "/create": "Create Project",
  "/profile": "Profile",
};

export const PageTitle = () => {
  const location = useLocation();

  useLayoutEffect(() => {
    const getPageTitle = () => {
      // Check for dynamic routes first
      if (location.pathname.startsWith("/project/") || location.pathname.startsWith("/build/")) {
        return "Live Build";
      }
      if (location.pathname.startsWith("/apps/")) {
        return "App Detail";
      }
      
      // Check static routes
      const pageName = routeTitleMap[location.pathname];
      if (pageName) {
        return pageName;
      }
      
      // Handle 404/not found pages
      return "Not Found";
    };

    const pageName = getPageTitle();
    document.title = `projectEngine - ${pageName}`;
  }, [location.pathname]);

  return null;
};

