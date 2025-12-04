import { useState, useEffect } from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import './ThemeToggle.css';

type Theme = 'light' | 'dark' | 'auto';

const THEME_CONFIG = {
  light: {
    icon: Sun,
    label: 'Light theme',
    next: 'dark' as Theme,
  },
  dark: {
    icon: Moon,
    label: 'Dark theme',
    next: 'auto' as Theme,
  },
  auto: {
    icon: Monitor,
    label: 'System theme',
    next: 'light' as Theme,
  },
};

function getSystemTheme(): 'light' | 'dark' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme: Theme) {
  const effectiveTheme = theme === 'auto' ? getSystemTheme() : theme;
  document.documentElement.setAttribute('data-theme', effectiveTheme);
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem('theme') as Theme | null;
    return stored && ['light', 'dark', 'auto'].includes(stored) ? stored : 'auto';
  });

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Listen for system theme changes when in auto mode
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      if (theme === 'auto') {
        applyTheme('auto');
      }
    };
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [theme]);

  const config = THEME_CONFIG[theme];
  const Icon = config.icon;
  const nextLabel = THEME_CONFIG[config.next].label.toLowerCase();

  return (
    <button
      className="theme-toggle"
      onClick={() => setTheme(config.next)}
      title={`${config.label} (click for ${nextLabel})`}
      aria-label={config.label}
    >
      <Icon size={16} />
    </button>
  );
}
