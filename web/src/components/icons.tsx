// Small inline icons (no icon library needed). All are decorative: aria-hidden.

type IconProps = { className?: string };

function Svg({ className, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className ?? "h-5 w-5"}
    >
      {children}
    </svg>
  );
}

export const LogoMark = ({ className }: IconProps) => (
  <svg viewBox="0 0 32 32" aria-hidden="true" className={className ?? "h-8 w-8"}>
    <rect width="32" height="32" rx="9" fill="var(--accent)" />
    <path
      d="M9 12.5a4.5 4.5 0 0 1 4.5-4.5h5a4.5 4.5 0 0 1 4.5 4.5v3a4.5 4.5 0 0 1-4.5 4.5H15l-4 3.5V19.6A4.5 4.5 0 0 1 9 15.5z"
      fill="#fff"
    />
    <path d="m13 14 2 2 4-4" stroke="var(--accent)" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const ArrowUp = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 19V5M5 12l7-7 7 7" />
  </Svg>
);
export const Stop = (p: IconProps) => (
  <Svg {...p}>
    <rect x="7" y="7" width="10" height="10" rx="1.5" />
  </Svg>
);
export const Plus = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 5v14M5 12h14" />
  </Svg>
);
export const Receipt = (p: IconProps) => (
  <Svg {...p}>
    <path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6" />
  </Svg>
);
export const PiggyBank = (p: IconProps) => (
  <Svg {...p}>
    <path d="M5 11a7 6 0 0 1 12-3h2v3l2 1v3h-2.5A7 6 0 0 1 15 18v2h-2v-1.5a8 8 0 0 1-3 0V20H8v-2.5A6 6 0 0 1 5 11zM14 6V4" />
  </Svg>
);
export const HeartPulse = (p: IconProps) => (
  <Svg {...p}>
    <path d="M20.5 8.5A4.5 4.5 0 0 0 12 6a4.5 4.5 0 0 0-8.5 2.5C3.5 14 12 20 12 20s8.5-6 8.5-11.5zM3.5 12h4l1.5-2 2 4 1.5-2h8" />
  </Svg>
);
export const GradCap = (p: IconProps) => (
  <Svg {...p}>
    <path d="m2 9 10-5 10 5-10 5zM6 11v5c3 2.5 9 2.5 12 0v-5M22 9v6" />
  </Svg>
);
export const Plane = (p: IconProps) => (
  <Svg {...p}>
    <path d="M2 16l20-8-4 12-5-4-3 4v-5l8-7-11 6z" />
  </Svg>
);
export const Wallet = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3 7a2 2 0 0 1 2-2h13v4M3 7v10a2 2 0 0 0 2 2h15V9H5a2 2 0 0 1-2-2zM16 14h1" />
  </Svg>
);
export const ShieldCheck = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6zM9 12l2 2 4-4" />
  </Svg>
);
export const Quote = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 7h6v6H6v4M14 7h6v6h-4v4" />
  </Svg>
);
export const EyeOff = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3 3l18 18M10.6 6.1A9 9 0 0 1 12 6c5 0 9 6 9 6a15 15 0 0 1-2.5 3M6.6 6.6C4.3 8.2 3 12 3 12s4 6 9 6a8.6 8.6 0 0 0 4-1M9.9 9.9a3 3 0 0 0 4.2 4.2" />
  </Svg>
);
export const ExternalLink = (p: IconProps) => (
  <Svg {...p}>
    <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
  </Svg>
);
export const Passport = (p: IconProps) => (
  <Svg {...p}>
    <path d="M6 3h11a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6zM9 17h6M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />
  </Svg>
);
