import "./globals.css";
import "./workspace.css";
export const metadata = {
  title: "Stock Intelligence AI",
  description: "Investigación financiera trazable y valoración reproducible",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
