import { useCallback, useEffect, useState } from 'react';
import {
  DEFAULT_PRESETS,
  mergePresetIntoState,
  resetChannelIntensity,
} from '@/features/imaging/utils/channelState.js';
import {
  deleteChannelPreset,
  fetchChannelPresets,
  saveChannelPreset,
} from '@/services/imageAssetsClient.js';

function IntensitySlider({ label, value, min, max, step, onChange }) {
  return (
    <label className="image-panel__field">
      <span>{label}</span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
      <span className="image-panel__field-value">{value}</span>
    </label>
  );
}

export default function ChannelManager({
  channelState,
  onChange,
  viewerFlags = {},
}) {
  const [savedPresets, setSavedPresets] = useState([]);
  const [presetName, setPresetName] = useState('');
  const [loadError, setLoadError] = useState(null);

  const refreshPresets = useCallback(async () => {
    try {
      const data = await fetchChannelPresets();
      setSavedPresets(data.presets || []);
      setLoadError(null);
    } catch (err) {
      setLoadError(err?.message || 'Failed to load presets');
    }
  }, []);

  useEffect(() => {
    refreshPresets();
  }, [refreshPresets]);

  const patchChannel = (index, patch) => {
    onChange(channelState.map((row) => (row.index === index ? { ...row, ...patch } : row)));
  };

  const showAll = () => onChange(channelState.map((row) => ({ ...row, visible: true })));
  const hideAll = () => onChange(channelState.map((row) => ({ ...row, visible: false })));
  const resetAll = () => onChange(channelState.map((row) => resetChannelIntensity({ ...row, visible: row.visible })));

  const applyPreset = (preset) => {
    onChange(mergePresetIntoState(channelState, preset.channels || preset));
  };

  const handleSavePreset = async () => {
    const name = presetName.trim();
    if (!name) return;
    await saveChannelPreset({ name, channels: channelState });
    setPresetName('');
    refreshPresets();
  };

  const handleDeletePreset = async (presetId) => {
    await deleteChannelPreset(presetId);
    refreshPresets();
  };

  return (
    <div className="image-panel image-panel--channels">
      <div className="image-panel__actions">
        <button type="button" className="btn btn-ghost btn-xs" onClick={showAll}>Show All</button>
        <button type="button" className="btn btn-ghost btn-xs" onClick={hideAll}>Hide All</button>
        <button type="button" className="btn btn-ghost btn-xs" onClick={resetAll}>Reset Channels</button>
      </div>

      {channelState.map((ch) => (
        <details key={ch.index} className="image-panel__channel" open={ch.visible}>
          <summary>
            <input
              type="checkbox"
              checked={ch.visible}
              onChange={(e) => patchChannel(ch.index, { visible: e.target.checked })}
              onClick={(e) => e.stopPropagation()}
            />
            <span>{ch.label}</span>
            <input
              type="color"
              value={ch.color}
              onChange={(e) => patchChannel(ch.index, { color: e.target.value })}
              onClick={(e) => e.stopPropagation()}
              aria-label={`Color for ${ch.label}`}
            />
          </summary>
          <IntensitySlider label="Min" value={ch.min} min={0} max={254} step={1} onChange={(v) => patchChannel(ch.index, { min: v })} />
          <IntensitySlider label="Max" value={ch.max} min={1} max={255} step={1} onChange={(v) => patchChannel(ch.index, { max: v })} />
          <IntensitySlider label="Gamma" value={ch.gamma} min={0.2} max={3} step={0.05} onChange={(v) => patchChannel(ch.index, { gamma: v })} />
          <IntensitySlider label="Brightness" value={ch.brightness} min={-128} max={128} step={1} onChange={(v) => patchChannel(ch.index, { brightness: v })} />
          <IntensitySlider label="Contrast" value={ch.contrast} min={0.2} max={3} step={0.05} onChange={(v) => patchChannel(ch.index, { contrast: v })} />
          <IntensitySlider label="Opacity" value={ch.opacity} min={0} max={1} step={0.05} onChange={(v) => patchChannel(ch.index, { opacity: v })} />
          <button type="button" className="btn btn-ghost btn-xs" onClick={() => patchChannel(ch.index, resetChannelIntensity(ch))}>
            Reset
          </button>
        </details>
      ))}

      {!viewerFlags.low_resource_mode ? (
        <div className="image-panel__presets">
          <h4>Presets</h4>
          {Object.entries(DEFAULT_PRESETS).map(([name, preset]) => (
            <button key={name} type="button" className="btn btn-ghost btn-xs" onClick={() => applyPreset(preset)}>
              {name}
            </button>
          ))}
          <div className="image-panel__preset-save">
            <input
              type="text"
              placeholder="Preset name"
              value={presetName}
              onChange={(e) => setPresetName(e.target.value)}
            />
            <button type="button" className="btn btn-sm" onClick={handleSavePreset}>Save</button>
          </div>
          {loadError ? <p className="text-footnote text-danger">{loadError}</p> : null}
          <ul className="image-panel__preset-list">
            {savedPresets.map((p) => (
              <li key={p.preset_id}>
                <button type="button" className="btn btn-ghost btn-xs" onClick={() => applyPreset(p)}>{p.name}</button>
                <button type="button" className="btn btn-ghost btn-xs text-danger" onClick={() => handleDeletePreset(p.preset_id)}>×</button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
