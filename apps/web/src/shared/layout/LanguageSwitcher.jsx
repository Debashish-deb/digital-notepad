import { Languages } from 'lucide-react';
import { LOCALE_META } from '@/i18n/constants.js';
import { useGuiT } from '@/i18n/useGuiT.js';

export default function LanguageSwitcher({
  variant = 'select',
  className = '',
  showLabel = true,
}) {
  const { locale, setLocale, t } = useGuiT();

  const handleLocaleChange = (nextLocale) => {
    setLocale(nextLocale);
  };

  if (variant === 'pills') {
    return (
      <div
        className={`overview-intro-lang${className ? ` ${className}` : ''}`}
        role="group"
        aria-label={t('common.langLabel')}
      >
        {showLabel && (
          <span className="overview-intro-lang-label">
            <Languages size={14} aria-hidden />
            {t('common.langLabel')}
          </span>
        )}
        <div className="overview-intro-lang-options">
          {LOCALE_META.map((opt) => (
            <button
              key={opt.id}
              type="button"
              className={`overview-intro-lang-btn${locale === opt.id ? ' active' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                handleLocaleChange(opt.id);
              }}
              aria-pressed={locale === opt.id}
              lang={opt.id}
            >
              {opt.native}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <label className={`locale-switcher${className ? ` ${className}` : ''}`}>
      {showLabel && <Languages size={14} aria-hidden />}
      <select
        className="locale-switcher-select"
        value={locale}
        onChange={(e) => {
          e.stopPropagation();
          handleLocaleChange(e.target.value);
        }}
        onClick={(e) => e.stopPropagation()}
        aria-label={t('common.langLabel')}
        style={{ textAlign: 'center', textAlignLast: 'center', borderRadius: '8px' }}
      >
        {LOCALE_META.map((opt) => (
          <option key={opt.id} value={opt.id} lang={opt.id}>
            {opt.native}
          </option>
        ))}
      </select>
    </label>
  );
}
