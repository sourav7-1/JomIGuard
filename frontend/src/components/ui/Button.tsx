import React, { forwardRef } from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost";
  size?: "default" | "sm";
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "default",
      isLoading,
      disabled,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    const base =
      "inline-flex items-center justify-center font-medium transition-colors select-none " +
      "min-h-[44px] min-w-[44px] rounded-lg " +
      "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent " +
      "disabled:opacity-50 disabled:pointer-events-none cursor-pointer";

    const variants = {
      primary: "bg-accent text-white hover:opacity-90 active:scale-[0.99]",
      ghost: "bg-transparent text-ink hover:bg-surface border border-line",
    };

    const sizes = {
      default: "px-5 py-2.5 text-base",
      sm: "px-3.5 py-2 text-sm",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
