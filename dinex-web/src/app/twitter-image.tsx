import { ImageResponse } from "next/og";

export const alt = "DineX: restaurant POS that works offline";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** The picture shown when the link is shared on WhatsApp, Facebook, LinkedIn or X. */
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", padding: 72, background: "linear-gradient(135deg,#0b6b52,#0f1f1a)", color: "white" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div style={{ width: 72, height: 72, borderRadius: 20, background: "#0D7A62", border: "3px solid #f5a623", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 44, fontWeight: 800 }}>D</div>
          <div style={{ fontSize: 52, fontWeight: 800 }}>DineX</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ fontSize: 76, fontWeight: 800, lineHeight: 1.05, maxWidth: 980 }}>Run your restaurant from one screen.</div>
          <div style={{ fontSize: 34, color: "#cfe7dd" }}>POS · Kitchen · Inventory · Staff · Payroll · Loyalty. Works offline.</div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 30, color: "#f5c26b" }}>
          <span>14-day free trial</span><span>by XverLabs</span>
        </div>
      </div>
    ),
    size,
  );
}
