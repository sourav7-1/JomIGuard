// Short English line under a Bangla heading or button label (for judges who don't read Bangla).
export function En({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <span lang="en" className={`block text-xs font-normal leading-snug opacity-75 ${className}`}>{children}</span>;
}
