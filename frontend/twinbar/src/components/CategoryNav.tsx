import type { MarketCategory } from '../types/market';

interface CategoryNavProps {
  active: MarketCategory;
  onChange: (category: MarketCategory) => void;
}

const categories: { id: MarketCategory; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'trending', label: '🔥 Trending' },
  { id: 'finance', label: '💰 Finance' },
  { id: 'crypto', label: '₿ Crypto' },
  { id: 'politics', label: '🏛️ Politics' },
  { id: 'sports', label: '⚽ Sports' },
];

export function CategoryNav({ active, onChange }: CategoryNavProps) {
  return (
    <nav className="category-nav flex gap-2 p-2 px-4 overflow-x-auto scrollbar-hide">
      {categories.map((cat) => (
        <button
          key={cat.id}
          data-category={cat.id}
          onClick={() => onChange(cat.id)}
          className={`category-chip flex-shrink-0 px-4 py-1 rounded-full text-sm font-medium whitespace-nowrap transition-colors
            ${active === cat.id
              ? 'active bg-[var(--color-primary)] text-white'
              : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]'
            }`}
        >
          {cat.label}
        </button>
      ))}
    </nav>
  );
}
