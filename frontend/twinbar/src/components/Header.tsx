export function Header() {
  return (
    <header className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white py-6 px-4 text-center">
      <div className="flex items-center justify-center gap-2 mb-1">
        <span className="logo-mark text-4xl font-bold tracking-tighter">||</span>
        <span className="logo-text text-2xl font-bold">Twinbar</span>
      </div>
      <p className="app-subtitle text-sm opacity-90">
        Predictive Markets for Smart Capital
      </p>
    </header>
  );
}
