import { Calendar } from 'lucide-react';

export default function MeetingScreen({ title, description }) {
  return (
    <div className="stack-md">
      <div className="panel">
        <h3 className="panel-title">
          <Calendar size={18} /> {title || 'Meeting Booking Calendar'}
        </h3>
        <p className="panel-lead prose-block">
          {description || 'Schedule and manage meetings.'}
        </p>
      </div>
      
      <div className="panel">
        <h4 className="text-title-3">Booking Calendar</h4>
        <p className="text-footnote muted">
          Multiple calendars for booking setup will come later.
        </p>
      </div>
    </div>
  );
}
