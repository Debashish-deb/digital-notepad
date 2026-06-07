import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import './HubNestedNav.css';

const HUB_TREE_ACCENTS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b'];

function resolveTreeAccent(activeIndex) {
  if (activeIndex < 0) return 'var(--color-primary)';
  return HUB_TREE_ACCENTS[activeIndex % HUB_TREE_ACCENTS.length];
}

function hasLayoutSize(rect) {
  return rect.width > 0 && rect.height > 0;
}

function HubTreeConnector({ frameRef, railRef, bodyRef, accent, activeSectionId }) {
  const [segments, setSegments] = useState(null);
  const rafRef = useRef(0);

  const measure = useCallback(() => {
    const frame = frameRef.current;
    const rail = railRef.current;
    const body = bodyRef.current;
    if (!frame || !rail || !body) {
      setSegments(null);
      return false;
    }

    const fr = frame.getBoundingClientRect();
    if (!hasLayoutSize(fr)) {
      setSegments(null);
      return false;
    }

    const detailList = body.querySelector('.hub-detail-rail-list');
    const activeBtn = rail.querySelector('.hub-section-rail-item--active');
    if (!detailList || !activeBtn) {
      setSegments(null);
      return false;
    }

    const items = [...detailList.querySelectorAll('.hub-detail-rail-item')];
    if (!items.length) {
      setSegments(null);
      return false;
    }

    const br = activeBtn.getBoundingClientRect();
    const dr = detailList.getBoundingClientRect();
    if (!hasLayoutSize(br) || !hasLayoutSize(dr)) {
      setSegments(null);
      return false;
    }

    const itemRects = items.map((btn) => btn.getBoundingClientRect());
    if (!itemRects.some(hasLayoutSize)) {
      setSegments(null);
      return false;
    }

    const parentX = br.right - fr.left;
    const parentY = br.top + br.height / 2 - fr.top;
    const trunkX = dr.left - fr.left + 1;

    const childLines = items.map((btn, index) => {
      const r = itemRects[index];
      const cy = r.top + r.height / 2 - fr.top;
      const cx = r.left - fr.left;
      const isActive = btn.classList.contains('hub-detail-rail-item--active');
      return { x1: trunkX, y1: cy, x2: cx, y2: cy, isActive };
    });

    const trunkTop = Math.min(childLines[0].y1, parentY);
    const trunkBottom = Math.max(childLines[childLines.length - 1].y1, parentY);

    setSegments({
      parent: { x1: parentX, y1: parentY, x2: trunkX, y2: parentY },
      trunk: { x1: trunkX, y1: trunkTop, x2: trunkX, y2: trunkBottom },
      children: childLines,
    });
    return true;
  }, [frameRef, railRef, bodyRef]);

  const scheduleMeasure = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
    }

    measure();
    rafRef.current = requestAnimationFrame(() => {
      measure();
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = 0;
        measure();
      });
    });
  }, [measure]);

  useLayoutEffect(() => {
    scheduleMeasure();

    const frame = frameRef.current;
    const rail = railRef.current;
    const body = bodyRef.current;
    if (!frame) return undefined;

    const observed = new Set();

    const syncObservedNodes = (resizeObserver) => {
      const nodes = [frame];
      if (rail) nodes.push(rail);
      if (body) nodes.push(body);

      if (rail) {
        rail.querySelectorAll('.hub-section-rail-item').forEach((node) => nodes.push(node));
      }
      if (body) {
        const detailList = body.querySelector('.hub-detail-rail-list');
        if (detailList) {
          nodes.push(detailList);
          detailList.querySelectorAll('.hub-detail-rail-item').forEach((node) => nodes.push(node));
        }
      }

      nodes.forEach((node) => {
        if (!observed.has(node)) {
          resizeObserver.observe(node);
          observed.add(node);
        }
      });
    };

    const ro = new ResizeObserver(() => {
      syncObservedNodes(ro);
      scheduleMeasure();
    });
    syncObservedNodes(ro);

    const mo = new MutationObserver(() => {
      syncObservedNodes(ro);
      scheduleMeasure();
    });

    if (body) {
      mo.observe(body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['class'],
      });
    }
    if (rail) {
      mo.observe(rail, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['class'],
      });
    }

    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          scheduleMeasure();
        }
      },
      { threshold: 0 },
    );
    io.observe(frame);

    window.addEventListener('resize', scheduleMeasure);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = 0;
      }
      ro.disconnect();
      mo.disconnect();
      io.disconnect();
      observed.clear();
      window.removeEventListener('resize', scheduleMeasure);
    };
  }, [scheduleMeasure, activeSectionId, frameRef, railRef, bodyRef]);

  useEffect(() => {
    scheduleMeasure();
  }, [scheduleMeasure, activeSectionId]);

  if (!segments) return null;

  return (
    <svg className="hub-tree-connector" aria-hidden>
      <path
        className="hub-tree-connector__parent"
        d={`M ${segments.parent.x1} ${segments.parent.y1} H ${segments.parent.x2}`}
        stroke={accent}
      />
      <path
        className="hub-tree-connector__trunk"
        d={`M ${segments.trunk.x1} ${segments.trunk.y1} V ${segments.trunk.y2}`}
        stroke={accent}
      />
      {segments.children.map((line, i) => (
        <path
          key={i}
          className={`hub-tree-connector__branch${line.isActive ? ' hub-tree-connector__branch--active' : ''}`}
          d={`M ${line.x1} ${line.y1} H ${line.x2}`}
          stroke={accent}
        />
      ))}
      <circle
        className="hub-tree-connector__parent-node"
        cx={segments.parent.x1}
        cy={segments.parent.y1}
        r="3.5"
        fill={accent}
      />
      {segments.children
        .filter((line) => line.isActive)
        .map((line, i) => (
          <circle
            key={`active-${i}`}
            className="hub-tree-connector__child-node"
            cx={line.x2}
            cy={line.y2}
            r="3"
            fill={accent}
          />
        ))}
    </svg>
  );
}

/**
 * Level-2 navigation: vertical section rail beside hub content.
 * Visually distinct from ModuleShell horizontal top tabs.
 */
export function HubSectionFrame({
  sections,
  active,
  onChange,
  children,
  ariaLabel = 'Sections',
  layout = 'vertical',
}) {
  const frameRef = useRef(null);
  const railRef = useRef(null);
  const bodyRef = useRef(null);
  const activeIndex = sections.findIndex((s) => s.id === active);
  const treeAccent = useMemo(() => resolveTreeAccent(activeIndex), [activeIndex]);
  const isHorizontal = layout === 'horizontal';

  return (
    <div
      ref={frameRef}
      className={`hub-section-frame${isHorizontal ? ' hub-section-frame--horizontal' : ''}`}
      style={{ '--hub-tree-accent': treeAccent }}
    >
      <nav ref={railRef} className="hub-section-rail" aria-label={ariaLabel}>
        <ul className="hub-section-rail-list" role="tablist">
          {sections.map((item) => {
            const isActive = active === item.id;
            return (
              <li key={item.id} role="presentation">
                <button
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`hub-section-rail-item${isActive ? ' hub-section-rail-item--active' : ''}`}
                  onClick={() => onChange(item.id)}
                  title={item.description || item.label}
                >
                  {item.icon ? <span className="hub-rail-icon" aria-hidden>{item.icon}</span> : null}
                  <span className="hub-rail-label">{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      <div ref={bodyRef} className="hub-section-body" role="tabpanel">
        {children}
      </div>
      {!isHorizontal ? (
        <HubTreeConnector
          frameRef={frameRef}
          railRef={railRef}
          bodyRef={bodyRef}
          accent={treeAccent}
          activeSectionId={active}
        />
      ) : null}
    </div>
  );
}

/**
 * Level-3 navigation: compact vertical detail rail inside a section.
 */
export function HubDetailFrame({ sections, active, onChange, children, ariaLabel = 'Views' }) {
  if (!sections?.length) return <div className="hub-detail-body">{children}</div>;

  return (
    <div className="hub-detail-frame hub-detail-frame--tree">
      <nav className="hub-detail-rail" aria-label={ariaLabel}>
        <ul className="hub-detail-rail-list hub-detail-rail-list--tree" role="tablist">
          {sections.map((item) => {
            const isActive = active === item.id;
            return (
              <li key={item.id} role="presentation">
                <button
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`hub-detail-rail-item${isActive ? ' hub-detail-rail-item--active' : ''}`}
                  onClick={() => onChange(item.id)}
                  title={item.description || item.label}
                >
                  <span className="hub-rail-label">{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="hub-detail-body" role="tabpanel">
        {children}
      </div>
    </div>
  );
}
