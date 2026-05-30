import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "个人智能助理团队",
  description: "多智能体协作系统 - 个人AI助理平台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
