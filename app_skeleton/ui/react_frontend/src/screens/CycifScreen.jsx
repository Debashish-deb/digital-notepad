import ImageProcessingPipelineScreen from './ImageProcessingPipelineScreen.jsx';

/** CyCif hub — imaging pipeline guide + document tabs elsewhere in nav. */
export default function CycifScreen({ variant = 'pipeline', dbProjects, API_URL, ...props }) {
  if (variant === 'pipeline') {
    return (
      <ImageProcessingPipelineScreen
        dbProjects={dbProjects}
        API_URL={API_URL}
        {...props}
      />
    );
  }
  return (
    <div className="panel">
      <p className="text-footnote muted">
        This CyCIF tool has moved to Computational Hub. Open LUMI HPC or Troubleshooting from the sidebar.
      </p>
    </div>
  );
}
