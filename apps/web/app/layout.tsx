import type { Metadata, Viewport } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/ui/Toast";

export const metadata: Metadata = {
  title: "Fix 24/7 – Cứu hộ Xe máy & Sửa Điện máy tại Huế",
  description:
    "Nền tảng cứu hộ xe máy khẩn cấp và sửa chữa đồ điện gia dụng tại nhà nhanh chóng, uy tín tại TP. Huế. Chẩn đoán AI, thợ đến sau 15 phút.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Fix 24/7",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#0f172a",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className="dark">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
      </head>
      <body className="min-h-screen bg-surface flex flex-col text-slate-100 antialiased selection:bg-brand-500 selection:text-white">
        <ToastProvider>
          <div className="mx-auto w-full max-w-md min-h-screen flex flex-col bg-surface shadow-2xl relative border-x border-surface-border/40">
            {children}
          </div>
        </ToastProvider>

        {/* Register Service Worker for PWA & Offline SOS */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js').then(
                    function(reg) { console.log('[Fix247] SW registered: ', reg.scope); },
                    function(err) { console.log('[Fix247] SW registration failed: ', err); }
                  );
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}
