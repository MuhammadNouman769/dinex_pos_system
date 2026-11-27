import Link from "next/link";
import { ArrowRight, BadgeCheck, ChefHat, CloudOff, Gift, Package, Receipt, Table2, UsersRound, Wallet, Boxes, BarChart3, CalendarClock, Smartphone, Check, ShieldCheck, Banknote } from "lucide-react";
import { Logo } from "@/components/Logo";
import { RedirectIfSignedIn } from "@/components/public/RedirectIfSignedIn";
import { FALLBACK_PLANS, POPULAR_PLAN } from "@/lib/plans";
import { abs, COMPANY, CONTACT_EMAIL, CONTACT_PHONE, SITE_DESCRIPTION, SITE_NAME, WHATSAPP_URL } from "@/lib/site";

const SHOWCASE = [
  { img: "/images/kitchen-screen.jpg", h: 750, tag: "Kitchen", title: "Orders reach the kitchen the moment you press Send", urdu: "Order seedha kitchen screen par.",
    points: ["New, Cooking and Ready columns that refresh by themselves", "Printed kitchen tickets with notes and options", "Sound alert for every new order"], alt: "DineX kitchen board with new, cooking and ready orders" },
  { img: "/images/tables-screen.jpg", h: 750, tag: "Tables and floors", title: "See every table, floor and reservation at a glance", urdu: "Har table ka haal ek nazar mein.",
    points: ["Draw your floor plan with round and square tables", "Book tables by time and party size, no double bookings", "Move or merge bills between tables"], alt: "DineX tables screen showing floors and table status" },
  { img: "/images/payroll-screen.jpg", h: 750, tag: "Staff and payroll", title: "Attendance, advances and salaries without a register", urdu: "Hazri se tankhwah tak, sab khud hisaab.",
    points: ["PIN attendance kiosk at the counter", "Overtime, advances and deductions worked out for you", "Salary details visible only to the owner"], alt: "DineX payroll run showing each employee's monthly pay" },
];

const MORE = [
  { icon: CloudOff, title: "Works offline", text: "Orders are saved on the device and sync when the internet returns." },
  { icon: Boxes, title: "Recipe-based stock", text: "Stock falls as you sell. Low-stock alerts and purchases." },
  { icon: Wallet, title: "Cash desk", text: "Open and close shifts, count the drawer, track expenses." },
  { icon: Gift, title: "Loyalty points", text: "Reward regular customers. You set the rules." },
  { icon: BarChart3, title: "Clear reports", text: "Sales, best sellers and payment methods, with CSV download." },
  { icon: Package, title: "Many branches", text: "Run every branch from one login." },
  { icon: Receipt, title: "Branded bills", text: "Your logo, account numbers and a QR on every bill." },
  { icon: CalendarClock, title: "Reservations", text: "Time and party-size checks built in." },
  { icon: Smartphone, title: "Any device", text: "Phone, tablet or PC. Installs from the browser." },
];

const FAQ = [
  { q: "Does DineX work without internet?", a: "Yes. The POS opens and takes orders with no internet. Orders wait on the device and are sent safely when the connection is back, even if it drops in the middle of sending." },
  { q: "How does the free trial work?", a: "Sign up, accept the terms and pick a plan. You get 14 days free with everything switched on and no card needed. Before it ends you pay by bank transfer, JazzCash or Easypaisa and the plan continues as soon as the payment is confirmed." },
  { q: "Which printers and devices do I need?", a: "Any 80 mm thermal printer or a normal printer, and any phone, tablet or computer with Chrome. There is nothing to install." },
  { q: "Can I use it for more than one branch?", a: "Yes. Growth includes up to 3 branches and Pro up to 10, each with its own tables, stock and cash desk, all under one login." },
  { q: "Is my restaurant's data private?", a: "Yes. Every restaurant sees only its own data. Salary information is visible only to the owner, and connections are protected with HTTPS." },
  { q: "How do customers get loyalty points?", a: "The cashier types the customer's phone number at the POS. Points are added when the bill is paid, and the customer can get an email with the points earned. You set the rules in Setup." },
];

const money = (v: string) => `PKR ${Number(v).toLocaleString("en-PK")}`;

const Frame = ({ src, w, h, alt, eager = false, className = "" }: { src: string; w: number; h: number; alt: string; eager?: boolean; className?: string }) => (
  <div className={`overflow-hidden rounded-2xl border border-white/10 bg-[#0d1714] shadow-[0_30px_80px_-20px_rgba(0,0,0,.55)] ${className}`}>
    <div className="flex items-center gap-1.5 border-b border-white/10 bg-[#13201c] px-4 py-2.5" aria-hidden>
      <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" /><span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" /><span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
      
    </div>
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src={src} width={w} height={h} alt={alt} loading={eager ? "eager" : "lazy"} className="block h-auto w-full" />
  </div>
);

export default function Home() {
  const software = {
    "@type": "SoftwareApplication", name: SITE_NAME, applicationCategory: "BusinessApplication", operatingSystem: "Web, Android, iOS, Windows, macOS",
    description: SITE_DESCRIPTION, url: abs("/"), image: abs("/opengraph-image"),
    publisher: { "@type": "Organization", name: COMPANY },
    offers: FALLBACK_PLANS.map((p) => ({ "@type": "Offer", name: p.name, price: p.price_monthly, priceCurrency: "PKR", url: abs("/start"), availability: "https://schema.org/InStock" })),
  };
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "Organization", "@id": abs("/#org"), name: COMPANY, url: abs("/"), logo: abs("/icon.png"), ...(CONTACT_EMAIL || CONTACT_PHONE ? { contactPoint: { "@type": "ContactPoint", contactType: "sales", ...(CONTACT_EMAIL ? { email: CONTACT_EMAIL } : {}), ...(CONTACT_PHONE ? { telephone: CONTACT_PHONE } : {}) } } : {}) },
      { "@type": "WebSite", "@id": abs("/#site"), name: SITE_NAME, url: abs("/"), publisher: { "@id": abs("/#org") }, inLanguage: "en" },
      software,
      { "@type": "FAQPage", mainEntity: FAQ.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })) },
    ],
  };
  const btnMain = "inline-flex min-h-[52px] items-center justify-center gap-2 rounded-xl bg-[#f5a623] px-7 text-base font-bold text-[#1a1200] shadow-[0_8px_30px_-8px_rgba(245,166,35,.6)] transition hover:brightness-105";
  const btnGhost = "inline-flex min-h-[52px] items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/5 px-7 text-base font-semibold text-white transition hover:bg-white/10";
  const wa = { href: WHATSAPP_URL, target: "_blank", rel: "noopener noreferrer" } as const;
  return (
    <div className="min-h-screen bg-[#f6f8f7] text-[#0f1f1a]">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <RedirectIfSignedIn />

      {/* ---------- HERO (always dark) ---------- */}
      <div className="relative overflow-hidden bg-[#08130f] text-white">
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(70%_55%_at_50%_-5%,rgba(16,185,129,.35),transparent),radial-gradient(40%_40%_at_90%_30%,rgba(245,166,35,.12),transparent)]" />
        <div aria-hidden className="pointer-events-none absolute inset-0 opacity-[.07] [background-image:linear-gradient(#fff_1px,transparent_1px),linear-gradient(90deg,#fff_1px,transparent_1px)] [background-size:56px_56px] [mask-image:radial-gradient(60%_60%_at_50%_20%,#000,transparent)]" />
        <header className="relative z-10">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-4 sm:px-6">
            <Link href="/" className="flex items-center gap-2.5" aria-label="DineX home"><Logo className="h-9 w-9" /><span className="font-display text-xl font-extrabold tracking-tight">DineX</span></Link>
            <nav aria-label="Main" className="hidden items-center gap-8 text-sm font-semibold text-white/70 md:flex">
              <a href="#features" className="hover:text-white">Features</a><a href="#pricing" className="hover:text-white">Pricing</a><a href="#faq" className="hover:text-white">FAQ</a>
            </nav>
            <div className="flex items-center gap-2">
              <Link href="/login" className="inline-flex min-h-[44px] items-center rounded-xl px-4 text-sm font-semibold text-white/90 hover:bg-white/10">Sign in</Link>
              <Link href="/start" className="inline-flex min-h-[44px] items-center rounded-xl bg-white px-4 text-sm font-bold text-[#08130f] hover:bg-white/90">Free trial</Link>
            </div>
          </div>
        </header>
        <section className="relative z-10 mx-auto max-w-6xl px-4 pb-20 pt-10 text-center sm:px-6 sm:pt-16">
          <p className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3.5 py-1.5 text-xs font-semibold text-emerald-300"><BadgeCheck className="h-3.5 w-3.5" />Made in Pakistan · PKR billing · JazzCash &amp; Easypaisa</p>
          <h1 className="mx-auto mt-6 max-w-4xl font-display text-[2.5rem] font-extrabold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">Restaurant POS software that <span className="bg-gradient-to-r from-emerald-300 to-[#f5a623] bg-clip-text text-transparent">works offline</span></h1>
          <p className="mx-auto mt-5 max-w-2xl text-base text-white/70 sm:text-lg">Billing, kitchen, tables, stock, staff payroll and loyalty in one simple system. Internet chala jaye tab bhi aapka restaurant nahi rukta.</p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/start" className={btnMain}>Start 14-day free trial <ArrowRight className="h-4 w-4" /></Link>
            <a href="#features" className={btnGhost}>See what is inside</a>
          </div>
          <p className="mt-4 text-xs text-white/50">No card needed · Cancel anytime · Setup in minutes</p>
          <div className="relative mx-auto mt-14 max-w-5xl">
            <div aria-hidden className="absolute -inset-x-6 -bottom-10 top-10 -z-0 rounded-[40px] bg-emerald-500/20 blur-3xl" />
            <Frame src="/images/dashboard-screen.jpg" w={1200} h={750} eager alt="DineX dashboard showing today's orders, kitchen status and a setup checklist" className="relative" />
          </div>
        </section>
      </div>

      {/* ---------- NUMBERS ---------- */}
      <section aria-label="Highlights" className="border-b border-[#dfe7e3] bg-white">
        <dl className="mx-auto grid max-w-6xl grid-cols-2 gap-y-6 px-4 py-8 text-center sm:px-6 md:grid-cols-4">
          {[["100%", "Works offline"], ["14 days", "Free trial"], ["2,999", "PKR / month, from"], ["Any device", "Phone, tablet, PC"]].map(([n, l]) => (
            <div key={l}><dt className="sr-only">{l}</dt><dd className="font-display text-3xl font-extrabold text-[#0b6b52]">{n}</dd><dd className="mt-0.5 text-sm text-[#5b6b64]">{l}</dd></div>
          ))}
        </dl>
      </section>

      {/* ---------- FEATURE SHOWCASE ---------- */}
      <section id="features" aria-labelledby="features-h" className="mx-auto max-w-6xl scroll-mt-16 px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-bold uppercase tracking-widest text-[#0b6b52]">Everything included</p>
          <h2 id="features-h" className="mt-2 font-display text-3xl font-extrabold tracking-tight sm:text-5xl">Everything a restaurant needs, in one place</h2>
          <p className="mt-3 text-[#5b6b64]">No extra apps to buy. Every feature is in every plan; you only choose how many branches and staff you need.</p>
        </div>

        <article className="mt-16 grid items-center gap-10 lg:grid-cols-2">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-[#e3f4ee] px-3 py-1 text-xs font-bold text-[#0b6b52]"><Receipt className="h-3.5 w-3.5" />Point of sale</span>
            <h3 className="mt-3 font-display text-2xl font-extrabold tracking-tight sm:text-4xl">Tap picture cards. Bill in seconds.</h3>
            <p className="mt-1 text-sm font-semibold text-[#0b6b52]">Tasveer dabayein, bill tayyar.</p>
            <ul className="mt-5 space-y-3 text-[#33433c]">
              {["Cash, card, JazzCash or Easypaisa, with split bills", "Dine-in, takeaway and delivery in one screen", "Print a bill with your logo, account numbers and QR", "Customer points shown at the counter"].map((t) => <li key={t} className="flex gap-3"><Check className="mt-1 h-4 w-4 shrink-0 text-[#0b6b52]" /><span>{t}</span></li>)}
            </ul>
          </div>
          <Frame src="/images/pos-screen.jpg" w={1200} h={750} alt="DineX point of sale with menu cards, an open order and a customer's loyalty points" />
        </article>

        {SHOWCASE.map((f, i) => (
          <article key={f.tag} className="mt-20 grid items-center gap-10 lg:grid-cols-2">
            <div className={i % 2 === 0 ? "lg:order-2" : ""}>
              <span className="inline-flex items-center gap-2 rounded-full bg-[#e3f4ee] px-3 py-1 text-xs font-bold text-[#0b6b52]">{f.tag}</span>
              <h3 className="mt-3 font-display text-2xl font-extrabold tracking-tight sm:text-4xl">{f.title}</h3>
              <p className="mt-1 text-sm font-semibold text-[#0b6b52]">{f.urdu}</p>
              <ul className="mt-5 space-y-3 text-[#33433c]">{f.points.map((t) => <li key={t} className="flex gap-3"><Check className="mt-1 h-4 w-4 shrink-0 text-[#0b6b52]" /><span>{t}</span></li>)}</ul>
            </div>
            <div className={i % 2 === 0 ? "lg:order-1" : ""}><Frame src={f.img} w={1200} h={f.h} alt={f.alt} /></div>
          </article>
        ))}

        <h3 className="mt-24 text-center font-display text-2xl font-extrabold sm:text-3xl">And much more</h3>
        <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {MORE.map(({ icon: Icon, title, text }) => (
            <li key={title} className="flex gap-4 rounded-2xl border border-[#dfe7e3] bg-white p-5 transition hover:-translate-y-0.5 hover:shadow-lg">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-[#e3f4ee] text-[#0b6b52]"><Icon className="h-5 w-5" /></span>
              <div><h4 className="font-display text-base font-bold">{title}</h4><p className="mt-0.5 text-sm text-[#5b6b64]">{text}</p></div>
            </li>
          ))}
        </ul>
      </section>

      {/* ---------- HOW IT WORKS (dark band) ---------- */}
      <section aria-labelledby="how-h" className="bg-[#08130f] text-white">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <h2 id="how-h" className="text-center font-display text-3xl font-extrabold tracking-tight sm:text-5xl">Start in three steps</h2>
          <ol className="mt-12 grid gap-6 md:grid-cols-3">
            {[["Sign up", "Accept the terms, pick a plan and add your restaurant. Your 14-day trial starts at once."], ["Add your menu", "Dishes with pictures, tables and staff. A checklist on the dashboard guides you."], ["Take your first order", "Open the POS on any device, take an order and print the bill."]].map(([t, d], i) => (
              <li key={t} className="rounded-2xl border border-white/10 bg-white/5 p-6">
                <span className="grid h-10 w-10 place-items-center rounded-full bg-[#f5a623] font-bold text-[#1a1200]">{i + 1}</span>
                <h3 className="mt-4 font-display text-xl font-bold">{t}</h3><p className="mt-1 text-sm text-white/65">{d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ---------- PRICING ---------- */}
      <section id="pricing" aria-labelledby="pricing-h" className="mx-auto max-w-6xl scroll-mt-16 px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-bold uppercase tracking-widest text-[#0b6b52]">Pricing</p>
          <h2 id="pricing-h" className="mt-2 font-display text-3xl font-extrabold tracking-tight sm:text-5xl">Simple monthly pricing</h2>
          <p className="mt-3 text-[#5b6b64]">Every plan starts with 14 free days. Pay by bank transfer, JazzCash or Easypaisa.</p>
        </div>
        <div className="mt-12 grid gap-6 md:grid-cols-3 md:items-stretch">
          {FALLBACK_PLANS.map((p) => {
            const hot = p.code === POPULAR_PLAN;
            return (
              <div key={p.code} className={`relative flex flex-col rounded-3xl p-7 ${hot ? "bg-[#0b2a21] text-white shadow-[0_30px_60px_-20px_rgba(11,107,82,.6)] md:-my-3" : "border border-[#dfe7e3] bg-white"}`}>
                {hot && <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[#f5a623] px-3.5 py-1 text-xs font-extrabold text-[#1a1200]">Most popular</span>}
                <h3 className="font-display text-xl font-extrabold">{p.name}</h3>
                <p className={`text-sm ${hot ? "text-white/65" : "text-[#5b6b64]"}`}>{p.description}</p>
                <p className="mt-6"><span className="font-display text-4xl font-extrabold sm:text-5xl">{money(p.price_monthly)}</span><span className={`text-sm ${hot ? "text-white/60" : "text-[#5b6b64]"}`}> / month</span></p>
                <ul className="mt-6 flex-1 space-y-2.5 text-sm">
                  <li className="flex gap-2"><Check className={`mt-0.5 h-4 w-4 shrink-0 ${hot ? "text-emerald-300" : "text-[#0b6b52]"}`} />{p.max_locations} {p.max_locations === 1 ? "branch" : "branches"} · {p.max_users} staff accounts</li>
                  {p.features.filter((f) => !/branch|staff accounts/i.test(f)).map((f) => <li key={f} className="flex gap-2"><Check className={`mt-0.5 h-4 w-4 shrink-0 ${hot ? "text-emerald-300" : "text-[#0b6b52]"}`} />{f}</li>)}
                </ul>
                <Link href="/start" className={`mt-7 inline-flex min-h-[50px] w-full items-center justify-center rounded-xl text-sm font-bold ${hot ? "bg-[#f5a623] text-[#1a1200] hover:brightness-105" : "border border-[#cfdad5] bg-[#f6f8f7] hover:bg-[#e9efec]"}`}>Start 14-day free trial</Link>
              </div>
            );
          })}
        </div>
        <ul className="mt-10 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-[#5b6b64]">
          <li className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-[#0b6b52]" />Your data stays private</li>
          <li className="flex items-center gap-2"><Banknote className="h-4 w-4 text-[#0b6b52]" />No card for the trial</li>
          <li className="flex items-center gap-2"><ChefHat className="h-4 w-4 text-[#0b6b52]" />Help on WhatsApp</li>
        </ul>
      </section>

      {/* ---------- FAQ ---------- */}
      <section id="faq" aria-labelledby="faq-h" className="mx-auto max-w-3xl scroll-mt-16 px-4 pb-20 sm:px-6">
        <h2 id="faq-h" className="text-center font-display text-3xl font-extrabold tracking-tight sm:text-4xl">Questions restaurants ask</h2>
        <div className="mt-8 space-y-3">
          {FAQ.map((f) => (
            <details key={f.q} className="group rounded-2xl border border-[#dfe7e3] bg-white p-5">
              <summary className="flex min-h-[32px] cursor-pointer list-none items-center justify-between gap-3 font-semibold">{f.q}<span className="text-xl text-[#0b6b52] transition group-open:rotate-45" aria-hidden>+</span></summary>
              <p className="mt-3 text-sm leading-relaxed text-[#5b6b64]">{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* ---------- FINAL CTA ---------- */}
      <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
        <div className="relative overflow-hidden rounded-3xl bg-[#08130f] p-8 text-center text-white sm:p-14">
          <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_80%_at_50%_0%,rgba(16,185,129,.35),transparent)]" />
          <div className="relative">
            <h2 className="font-display text-3xl font-extrabold sm:text-5xl">Try DineX free for 14 days</h2>
            <p className="mx-auto mt-3 max-w-xl text-white/70">Set up your menu in minutes and take your first order today.</p>
            <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link href="/start" className={btnMain}>Start your free trial <ArrowRight className="h-4 w-4" /></Link>
              
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#dfe7e3] bg-white">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-8 text-sm text-[#5b6b64] sm:flex-row sm:px-6">
          <div className="flex items-center gap-2.5"><Logo className="h-8 w-8" /><p>© {new Date().getFullYear()} {COMPANY}. DineX is a product of {COMPANY}.</p></div>
          <nav aria-label="Footer" className="flex flex-wrap items-center justify-center gap-5">
            <Link href="/terms" className="hover:text-[#0f1f1a]">Terms of Use</Link><Link href="/login" className="hover:text-[#0f1f1a]">Sign in</Link>
            <a {...wa} className="hover:text-[#0f1f1a]">WhatsApp</a>
            {CONTACT_PHONE && <a href={`tel:${CONTACT_PHONE.replace(/\s/g, "")}`} className="hover:text-[#0f1f1a]">{CONTACT_PHONE}</a>}
            {CONTACT_EMAIL && <a href={`mailto:${CONTACT_EMAIL}`} className="hover:text-[#0f1f1a]">{CONTACT_EMAIL}</a>}
          </nav>
        </div>
      </footer>
    </div>
  );
}
