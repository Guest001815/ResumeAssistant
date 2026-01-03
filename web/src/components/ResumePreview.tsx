import React, { forwardRef } from "react";

type Props = { html: string };

const ResumePreview = forwardRef<HTMLIFrameElement, Props>(({ html }, ref) => {
  return (
    <div className="w-full max-w-[210mm] min-h-[297mm] mx-auto bg-white shadow-2xl transition-all duration-300 ease-in-out transform">
      <iframe 
        title="resume" 
        srcDoc={html} 
        ref={ref}
        className="w-full h-full min-h-[297mm] border-none block"
        sandbox="allow-same-origin allow-scripts"
      />
    </div>
  );
});

ResumePreview.displayName = "ResumePreview";

export default ResumePreview;
