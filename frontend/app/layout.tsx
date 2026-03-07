import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'AI Negotiation Copilot',
  description: 'Multimodal real-time negotiation assistant',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
