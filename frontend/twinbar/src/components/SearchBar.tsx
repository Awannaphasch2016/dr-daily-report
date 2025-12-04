import { useState } from 'react';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

interface SearchBarProps {
  onSearch: (query: string) => void;
}

export function SearchBar({ onSearch }: SearchBarProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(query);
  };

  return (
    <section className="search-section p-4 bg-[var(--color-bg)] sticky top-0 z-50">
      <form onSubmit={handleSubmit} className="search-container flex gap-2 bg-[var(--color-bg-secondary)] rounded-xl p-2 px-4">
        <input
          id="search-input"
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            onSearch(e.target.value);
          }}
          className="search-input flex-1 bg-transparent outline-none text-[var(--color-text)] placeholder:text-[var(--color-text-secondary)]"
          placeholder="Search markets..."
          autoComplete="off"
        />
        <button
          id="search-btn"
          type="submit"
          className="search-btn w-10 h-10 flex items-center justify-center bg-[var(--color-primary)] text-white rounded-lg hover:bg-[var(--color-primary-dark)] transition-colors"
        >
          <MagnifyingGlassIcon className="w-5 h-5" />
        </button>
      </form>
    </section>
  );
}
