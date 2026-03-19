import Link from "next/link";
import styles from "./page.module.css";

export const metadata = {
  title: "RAG Smart QA — Intelligent Document Intelligence",
};

const features = [
  {
    icon: "◈",
    title: "Precise Answers, Always Cited",
    description:
      "Every response links directly to the source document and page. No hallucinations, no guesswork — just verified intelligence grounded in your own content.",
  },
  {
    icon: "⬡",
    title: "Multi-Document Reasoning",
    description:
      "Ask questions that span dozens of documents simultaneously. RAG Smart QA synthesizes information across your entire knowledge base in seconds.",
  },
  {
    icon: "◎",
    title: "Intelligent Summaries",
    description:
      "Get executive-level summaries for any document on demand. Understand the key ideas without reading every line, then drill in where it matters.",
  },
  {
    icon: "⟡",
    title: "Conversation Memory",
    description:
      "Build on previous questions in the same session. Follow-up, refine, and explore — RAG Smart QA remembers context so you don't have to repeat yourself.",
  },
  {
    icon: "◇",
    title: "Any Document Format",
    description:
      "PDFs, Word documents, text files, research papers — upload whatever you have. RAG Smart QA handles parsing, indexing, and retrieval automatically.",
  },
  {
    icon: "⬧",
    title: "Enterprise-Ready Security",
    description:
      "Your documents stay yours. Isolated storage, encrypted at rest, with role-based access control and full audit trails for compliance requirements.",
  },
];

const steps = [
  {
    num: "01",
    title: "Upload your documents",
    description:
      "Drag and drop PDFs, research papers, contracts, or any text-based document. We index everything within seconds.",
  },
  {
    num: "02",
    title: "Ask anything in natural language",
    description:
      "Type your question as if you were asking a colleague. No special syntax required — just plain English.",
  },
  {
    num: "03",
    title: "Get precise, cited answers",
    description:
      "Receive a clear answer with exact citations. Click any citation to jump directly to the relevant passage.",
  },
];

const testimonials = [
  {
    quote:
      "We cut document review time by 70%. What used to take a junior analyst an afternoon now takes five minutes.",
    name: "Sarah Chen",
    role: "Head of Research, Meridian Capital",
    avatar: "SC",
  },
  {
    quote:
      "Finally, an AI tool that cites its sources. Our compliance team actually trusts the outputs now.",
    name: "Marcus Webb",
    role: "VP Legal, Structured Finance Corp",
    avatar: "MW",
  },
  {
    quote:
      "The multi-document reasoning is genuinely impressive. It found a contradiction between two contracts our team had missed for months.",
    name: "Priya Nair",
    role: "Senior Counsel, TechVenture Legal",
    avatar: "PN",
  },
];

export default function HomePage() {
  return (
    <div className={styles.page}>
      {/* ── HERO ── */}
      <section className={styles.hero}>
        <div className={styles.heroBg} aria-hidden="true">
          <div className={styles.heroGlow1} />
          <div className={styles.heroGlow2} />
          <div className={styles.heroGrid} />
        </div>

        <div className="container">
          <div className={styles.heroBadge}>
            <span className="badge badge-accent">
              <span>✦</span> Now in public beta
            </span>
          </div>

          <h1 className={`display-2xl ${styles.heroTitle}`}>
            Your documents,<br />
            <span className="text-gradient">finally answering</span><br />
            your questions.
          </h1>

          <p className={`body-lg ${styles.heroSub}`}>
            Upload any document. Ask anything. Get precise answers with exact
            citations — powered by retrieval-augmented generation that never
            makes things up.
          </p>

          <div className={styles.heroCta}>
            <Link href="/signin" className="btn btn-primary btn-lg">
              Start for free
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </Link>
            <Link href="/#how-it-works" className="btn btn-secondary btn-lg">
              See how it works
            </Link>
          </div>

          <p className={styles.heroNote}>
            No credit card required · 5 documents free · Upgrade anytime
          </p>
        </div>

        {/* Product preview */}
        <div className={`container ${styles.previewWrap}`}>
          <div className={styles.previewWindow}>
            <div className={styles.previewBar}>
              <div className={styles.previewDots}>
                <span /><span /><span />
              </div>
              <span className={styles.previewUrl}>app.ragsmartqa.com/chat</span>
            </div>
            <div className={styles.previewContent}>
              <div className={styles.previewSidebar}>
                <div className={styles.previewSidebarItem + " " + styles.active}>
                  Q4 Earnings Report.pdf
                </div>
                <div className={styles.previewSidebarItem}>Market Analysis 2024.pdf</div>
                <div className={styles.previewSidebarItem}>Legal Contract v3.pdf</div>
                <div className={styles.previewSidebarItem}>Technical Spec.pdf</div>
              </div>
              <div className={styles.previewMain}>
                <div className={styles.previewQuestion}>
                  What was the year-over-year revenue growth and what factors drove it?
                </div>
                <div className={styles.previewAnswer}>
                  <p>Revenue grew <strong>34.2% year-over-year</strong> to $847M, primarily driven by three factors:</p>
                  <ol>
                    <li>Enterprise segment expansion (+52% YoY) led by key wins in financial services</li>
                    <li>International market entry in APAC contributing $94M in new ARR</li>
                    <li>Improved net revenue retention of 118%, up from 109% prior year</li>
                  </ol>
                </div>
                <div className={styles.previewCitations}>
                  <span className={styles.citLabel}>Citations</span>
                  <span className={styles.cit}>Q4 Report · p.4</span>
                  <span className={styles.cit}>Q4 Report · p.11</span>
                  <span className={styles.cit}>Q4 Report · p.18</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── LOGOS ── */}
      <section className={styles.logos}>
        <div className="container">
          <p className={styles.logosLabel}>Trusted by teams at</p>
          <div className={styles.logosRow}>
            {["Meridian Capital", "TechVenture", "LexGroup", "Structured Finance", "Arboreal Labs", "Proxima Research"].map((name) => (
              <span key={name} className={styles.logoItem}>{name}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className={styles.features} id="features">
        <div className="container">
          <div className={styles.sectionHeader}>
            <span className="caption" style={{ color: "var(--accent-primary)" }}>Capabilities</span>
            <h2 className={`display-lg ${styles.sectionTitle}`}>
              Built for the way<br />professionals actually work
            </h2>
            <p className={`body-lg ${styles.sectionSub}`}>
              Every feature is designed around the reality of document-heavy workflows — where speed, accuracy, and trust aren't optional.
            </p>
          </div>

          <div className={styles.featuresGrid}>
            {features.map((f) => (
              <div key={f.title} className={`card card-hover ${styles.featureCard}`}>
                <div className={styles.featureIcon}>{f.icon}</div>
                <h3 className="heading-md">{f.title}</h3>
                <p className={`body-sm ${styles.featureDesc}`}>{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className={styles.howItWorks} id="how-it-works">
        <div className={styles.howBg} aria-hidden="true" />
        <div className="container">
          <div className={styles.sectionHeader}>
            <span className="caption" style={{ color: "var(--accent-primary)" }}>Process</span>
            <h2 className={`display-lg ${styles.sectionTitle}`}>Three steps to clarity</h2>
            <p className={`body-lg ${styles.sectionSub}`}>
              From upload to insight in under a minute. No training required, no complex setup.
            </p>
          </div>

          <div className={styles.stepsGrid}>
            {steps.map((step, i) => (
              <div key={step.num} className={styles.step}>
                <div className={styles.stepNum}>{step.num}</div>
                {i < steps.length - 1 && <div className={styles.stepConnector} aria-hidden="true" />}
                <h3 className="heading-lg">{step.title}</h3>
                <p className={`body-md ${styles.stepDesc}`}>{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TESTIMONIALS ── */}
      <section className={styles.testimonials} id="testimonials">
        <div className="container">
          <div className={styles.sectionHeader}>
            <span className="caption" style={{ color: "var(--accent-primary)" }}>Social proof</span>
            <h2 className={`display-lg ${styles.sectionTitle}`}>What teams are saying</h2>
          </div>

          <div className={styles.testimonialsGrid}>
            {testimonials.map((t) => (
              <div key={t.name} className={`card ${styles.testimonialCard}`}>
                <div className={styles.stars}>★★★★★</div>
                <blockquote className={styles.quote}>&ldquo;{t.quote}&rdquo;</blockquote>
                <div className={styles.testimonialAuthor}>
                  <div className={styles.avatar}>{t.avatar}</div>
                  <div>
                    <div className={styles.authorName}>{t.name}</div>
                    <div className={styles.authorRole}>{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PRICING ── */}
      <section className={styles.pricing} id="pricing">
        <div className="container">
          <div className={styles.sectionHeader}>
            <span className="caption" style={{ color: "var(--accent-primary)" }}>Pricing</span>
            <h2 className={`display-lg ${styles.sectionTitle}`}>Simple, honest pricing</h2>
            <p className={`body-lg ${styles.sectionSub}`}>Start free. Scale when you need to. No hidden fees.</p>
          </div>

          <div className={styles.pricingGrid}>
            <div className={`card ${styles.pricingCard}`}>
              <div className={styles.planName}>Starter</div>
              <div className={styles.planPrice}><span>$0</span>/mo</div>
              <p className={styles.planDesc}>For individuals and small projects.</p>
              <ul className={styles.planFeatures}>
                <li>5 documents</li>
                <li>50 queries/month</li>
                <li>Summaries included</li>
                <li>Email support</li>
              </ul>
              <Link href="/signin" className="btn btn-secondary" style={{width:'100%',marginTop:'auto'}}>Get started free</Link>
            </div>

            <div className={`card ${styles.pricingCard} ${styles.featured}`}>
              <div className={styles.featuredBadge}>Most popular</div>
              <div className={styles.planName}>Professional</div>
              <div className={styles.planPrice}><span>$49</span>/mo</div>
              <p className={styles.planDesc}>For teams that run on documents.</p>
              <ul className={styles.planFeatures}>
                <li>Unlimited documents</li>
                <li>1,000 queries/month</li>
                <li>Priority indexing</li>
                <li>Citation export</li>
                <li>Priority support</li>
              </ul>
              <Link href="/signin" className="btn btn-primary" style={{width:'100%',marginTop:'auto'}}>Start free trial</Link>
            </div>

            <div className={`card ${styles.pricingCard}`}>
              <div className={styles.planName}>Enterprise</div>
              <div className={styles.planPrice}><span>Custom</span></div>
              <p className={styles.planDesc}>For organizations with compliance requirements.</p>
              <ul className={styles.planFeatures}>
                <li>Unlimited everything</li>
                <li>SSO & SCIM</li>
                <li>Audit logs</li>
                <li>Custom data retention</li>
                <li>Dedicated support</li>
              </ul>
              <Link href="/contact" className="btn btn-secondary" style={{width:'100%',marginTop:'auto'}}>Talk to sales</Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className={styles.cta}>
        <div className={styles.ctaBg} aria-hidden="true" />
        <div className="container">
          <div className={styles.ctaBox}>
            <h2 className={`display-lg ${styles.ctaTitle}`}>
              Ready to stop<br />searching, and start knowing?
            </h2>
            <p className={`body-lg ${styles.ctaSub}`}>
              Join thousands of analysts, lawyers, and researchers who've replaced document dread with document confidence.
            </p>
            <div className={styles.ctaActions}>
              <Link href="/signin" className="btn btn-primary btn-lg">
                Get started free
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
              </Link>
              <p className={styles.ctaNote}>No credit card · 5 documents free</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
