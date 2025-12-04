import type { SortOption } from '../types/market';

interface SortBarProps {
  active: SortOption;
  onChange: (sort: SortOption) => void;
}

const sortOptions: { id: SortOption; label: string }[] = [
  { id: 'newest', label: 'Newest' },
  { id: 'volume', label: 'Volume' },
  { id: 'ending', label: 'Ending Soon' },
];

export function SortBar({ active, onChange }: SortBarProps) {
  return (
    <div className="sort-bar flex items-center gap-2 px-4 py-1 border-b border-[var(--color-border)]">
      <span className="sort-label text-xs text-[var(--color-text-secondary)]">Sort by:</span>
      {sortOptions.map((opt) => (
        <button
          key={opt.id}
          data-sort={opt.id}
          onClick={() => onChange(opt.id)}
          className={`sort-btn px-2 py-1 text-xs font-medium rounded transition-colors
            ${active === opt.id
              ? 'active text-[var(--color-primary)] bg-[var(--color-primary)]/10'
              : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'
            }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
