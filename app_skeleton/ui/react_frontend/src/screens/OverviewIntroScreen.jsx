import OverviewIntroBody from '../components/overview/OverviewIntroBody.jsx';

export default function OverviewIntroScreen({ onSubChange, onNavigate }) {
  return (
    <section className="overview-page">
      <OverviewIntroBody onSubChange={onSubChange} onNavigate={onNavigate} />
    </section>
  );
}
