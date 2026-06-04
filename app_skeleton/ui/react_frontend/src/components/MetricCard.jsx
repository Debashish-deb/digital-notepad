import React from 'react';

export default function MetricCard({ label, value, variant = 'primary' }) {
  let variantClass = '';
  if (variant === 'success') variantClass = 'success';
  if (variant === 'accent') variantClass = 'accent';
  if (variant === 'warning') variantClass = 'warning';

  return (
    <div className={`metric-card ${variantClass}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
}
