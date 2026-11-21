export function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <path d="M16 2 4 7v8c0 7.2 5 12.9 12 15 7-2.1 12-7.8 12-15V7z" fill="#101B33" />
      <path d="m16 8 6 10h-4l-2-3.5L14 18h-4z" fill="#F36F21" />
    </svg>
  );
}
export function Logo({ light = false }: { light?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark />
      <div className="leading-tight">
        <div className={`text-[15px] font-bold tracking-tight ${light ? "text-white" : "text-ink-900"}`}>Aegis<span className="text-brand-500">Bank</span> AI</div>
        <div className={`text-[10px] ${light ? "text-ink-300" : "text-ink-500"}`}>Fraud Investigation Platform</div>
      </div>
    </div>
  );
}
