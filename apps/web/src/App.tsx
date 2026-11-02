// The app shell: the top bar and its three tabs.
import { useEffect, useState } from 'react';
import { Builder } from './Builder';
import { Battle } from './battle/Battle';
import { Cards } from './Cards';

type Tab = 'builder' | 'cards' | 'battle';
const TABS: Array<{ id: Tab; label: string }> = [
  { id: 'builder', label: 'Lance Ledger' },
  { id: 'cards', label: 'Unit Cards' },
  { id: 'battle', label: 'Charter Trial' },
];

export function App() {
  const [tab, setTab] = useState<Tab>(() => TABS.find((t) => location.hash === `#${t.id}`)?.id ?? 'builder');
  useEffect(() => {
    history.replaceState(null, '', `#${tab}`);
  }, [tab]);
  return (
    <>
      <nav className="topbar">
        <h1>Brass Charter</h1>
        <div className="tabs" role="tablist">
          {TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? 'on' : ''} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
      </nav>
      {tab === 'builder' ? (
        <Builder />
      ) : (
        <div className="app">{tab === 'cards' ? <Cards /> : <Battle />}</div>
      )}
    </>
  );
}
