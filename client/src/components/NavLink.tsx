import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";

interface NavLinkProps {
  to: string;
  end?: boolean;
  className?: string;
  activeClassName?: string;
  children: React.ReactNode;
}

export const NavLink = ({
  to,
  end = false,
  className = "",
  activeClassName = "text-primary font-semibold",
  children,
}: NavLinkProps) => {
  const location = useLocation();
  const isActive = end
    ? location.pathname === to
    : location.pathname.startsWith(to);

  return (
    <Link to={to} className={cn(className, isActive && activeClassName)}>
      {children}
    </Link>
  );
};

