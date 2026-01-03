import React from "react";

export default function MarkdownPane(props: {
  markdownText: string;
  setMarkdownText: (t: string) => void;
}) {
  const { markdownText, setMarkdownText } = props;

  return (
    <div className="w-full max-w-[210mm] min-h-[297mm] mx-auto bg-white shadow-2xl p-8 md:p-[20mm] transition-all duration-300">
      <textarea
        value={markdownText}
        onChange={(e) => setMarkdownText(e.target.value)}
        placeholder="在此输入 Markdown 内容..."
        className="w-full h-full min-h-[250mm] resize-none border-none focus:ring-0 p-0 text-gray-800 font-mono text-sm leading-relaxed bg-transparent"
        spellCheck={false}
      />
    </div>
  );
}
