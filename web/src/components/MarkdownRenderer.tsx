import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * Markdown 渲染组件
 * 支持 GFM（GitHub Flavored Markdown）和代码语法高亮
 */
export default function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  // 检测是否为草稿预览模式
  const isDraft = className.includes("draft-content");
  
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // 代码块渲染
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            const language = match ? match[1] : "";
            
            return !inline && language ? (
              <SyntaxHighlighter
                style={oneDark}
                language={language}
                PreTag="div"
                className="rounded-lg !my-2 !text-sm"
                {...props}
              >
                {String(children).replace(/\n$/, "")}
              </SyntaxHighlighter>
            ) : (
              <code
                className="bg-gray-100 text-red-600 px-1.5 py-0.5 rounded text-sm font-mono"
                {...props}
              >
                {children}
              </code>
            );
          },
          // 段落
          p({ children }) {
            return <p className={`last:mb-0 leading-relaxed ${isDraft ? "mb-4 text-base text-gray-800" : "mb-3"}`}>{children}</p>;
          },
          // 标题
          h1({ children }) {
            return <h1 className={`font-bold first:mt-0 ${isDraft ? "text-3xl mb-4 mt-6 text-gray-900 border-b pb-2 border-gray-200" : "text-2xl mb-3 mt-4"}`}>{children}</h1>;
          },
          h2({ children }) {
            return <h2 className={`font-bold first:mt-0 ${isDraft ? "text-2xl mb-3 mt-5 text-gray-900" : "text-xl mb-2 mt-3"}`}>{children}</h2>;
          },
          h3({ children }) {
            return <h3 className={`font-semibold first:mt-0 ${isDraft ? "text-xl mb-3 mt-4 text-gray-800" : "text-lg mb-2 mt-3"}`}>{children}</h3>;
          },
          h4({ children }) {
            return <h4 className={`font-semibold ${isDraft ? "text-lg mb-2 mt-3 text-gray-800" : "text-base mb-2 mt-2"}`}>{children}</h4>;
          },
          // 列表
          ul({ children }) {
            return <ul className={`list-disc mb-3 ${isDraft ? "ml-6 space-y-2 text-base" : "list-inside space-y-1"}`}>{children}</ul>;
          },
          ol({ children }) {
            return <ol className={`list-decimal mb-3 ${isDraft ? "ml-6 space-y-2 text-base" : "list-inside space-y-1"}`}>{children}</ol>;
          },
          li({ children }) {
            return <li className={`leading-relaxed ${isDraft ? "text-gray-700 pl-1" : ""}`}>{children}</li>;
          },
          // 链接
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline"
              >
                {children}
              </a>
            );
          },
          // 引用
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-gray-300 pl-4 py-2 my-3 italic text-gray-700 bg-gray-50 rounded-r">
                {children}
              </blockquote>
            );
          },
          // 表格
          table({ children }) {
            return (
              <div className="overflow-x-auto my-3">
                <table className="min-w-full border-collapse border border-gray-300">
                  {children}
                </table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-gray-100">{children}</thead>;
          },
          tbody({ children }) {
            return <tbody>{children}</tbody>;
          },
          tr({ children }) {
            return <tr className="border-b border-gray-300">{children}</tr>;
          },
          th({ children }) {
            return (
              <th className="px-4 py-2 text-left font-semibold border border-gray-300">
                {children}
              </th>
            );
          },
          td({ children }) {
            return <td className="px-4 py-2 border border-gray-300">{children}</td>;
          },
          // 分隔线
          hr() {
            return <hr className="my-4 border-gray-300" />;
          },
          // 强调
          strong({ children }) {
            return <strong className="font-bold">{children}</strong>;
          },
          em({ children }) {
            return <em className="italic">{children}</em>;
          },
          // 删除线
          del({ children }) {
            return <del className="line-through text-gray-500">{children}</del>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

