# End-to-end checks (Playwright)
Run against a QA backend (`:8000`) and a production web build (`npx next start -p 3101`, built with
`NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`). Install once: `npm i -g playwright && npx playwright install chromium`.

Order matters because later steps reuse the restaurant created earlier:
* `reset.sh` then `step1.js` (signup flow) → `step2.js`, `step5.js`, `step9.js` (each needs a fresh `reset.sh` + `step1.js`)
* `reset.sh` + `seed2.js` → `step4.js`, `step6.js`, `step7.js`, `step8.js`
* `step10.js` (SEO: robots, sitemap, JSON-LD, noindex, OG image, redirect) needs `seed_demo` data (`karachigrill`)
* `resp_public.js` checks the public pages at 8 screen sizes for sideways scrolling

`reset.sh` and `seed*.js` live next to the scripts in the QA scratch folder; copy them from `qa_e2e/` if present.
