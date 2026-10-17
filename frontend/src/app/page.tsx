import Link from "next/link";

const offerings = [
  {
    phase: "কেনার আগে",
    title: "কাগজ যাচাই",
    copy: "খতিয়ান, দলিল ও নামজারির তথ্য মিলিয়ে দেখুন।",
    href: "/upload",
    mark: "ক",
  },
  {
    phase: "কেনার আগে",
    title: "মালিকানার ইতিহাস",
    copy: "কাগজে থাকা মালিকানা পরিবর্তনের ধারাটি একসঙ্গে দেখুন।",
    href: "/cases",
    mark: "ই",
  },
  {
    phase: "লেনদেনের সময়",
    title: "বায়না escrow",
    copy: "শর্তভিত্তিক অর্থ লেনদেনের জন্য ব্যাংক পার্টনারের ব্যবস্থা।",
    href: "/escrow",
    mark: "ব",
  },
  {
    phase: "কেনার পরে",
    title: "প্রবাসী গার্ডিয়ান",
    copy: "খতিয়ানের নতুন কপি এলে আগের তথ্যের সঙ্গে পরিবর্তন মিলিয়ে দেখুন।",
    href: "/guardian",
    mark: "গ",
  },
];

const steps = [
  ["কাগজ যোগ করুন", "খতিয়ান, দলিল বা নামজারির কপি দিন।"],
  ["তথ্য পড়া হয়", "মুদ্রিত তথ্য আলাদা করে সাজানো হয়।"],
  ["মিল পরীক্ষা হয়", "এক কাগজের তথ্য আরেক কাগজের সঙ্গে মেলানো হয়।"],
  ["করণীয় দেখুন", "কোন তথ্য মিলেছে, কোথায় যাচাই দরকার—তা দেখুন।"],
];

function Arrow() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" fill="none" className="h-4 w-4">
      <path d="M3.5 10h12m-5-5 5 5-5 5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LandSketch() {
  return (
    <svg aria-hidden="true" viewBox="0 0 220 178" fill="none" className="absolute -right-3 -top-4 w-44 opacity-20 sm:w-52">
      <path d="M18 24 111 8l86 24-9 121-91 15-84-29 5-115Z" stroke="currentColor" />
      <path d="m26 52 83-14 78 21M16 80l92-15 82 19M15 110l89-14 88 18M17 139l86-14 85 15M56 17l-8 139M95 11l-5 140M137 14l-4 140M172 24l-3 135" stroke="currentColor" strokeDasharray="3 5" />
      <path d="m68 69 45-8 35 12-3 36-43 8-37-12 3-36Z" stroke="currentColor" strokeWidth="2" />
      <circle cx="111" cy="91" r="3" fill="currentColor" />
    </svg>
  );
}

export default function HomePage() {
  return (
    <div className="space-y-16 pb-10 pt-3 sm:space-y-20 sm:pt-8">
      <section className="relative isolate overflow-hidden rounded-2xl bg-[#12342A] px-5 py-9 text-white sm:px-10 sm:py-12 lg:px-14 lg:py-16">
        <div className="absolute inset-y-0 right-0 -z-10 hidden w-[48%] bg-[#1B4638] lg:block" />
        <LandSketch />
        <div className="grid items-center gap-10 lg:grid-cols-[1fr_0.82fr] lg:gap-14">
          <div className="max-w-2xl">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/20 px-3 py-1.5 text-xs font-medium text-[#CBE6D8]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#7FD1B3]" />
              জমির কাগজ, এক জায়গায় যাচাই
            </p>
            <h1 className="max-w-xl text-3xl font-normal leading-[1.35] tracking-tight sm:text-4xl lg:text-[3.35rem]">
              বায়না দেওয়ার আগে,
              <br className="hidden sm:block" /> কাগজে কী মেলে জেনে নিন
            </h1>
            <p className="mt-5 max-w-lg text-sm leading-7 text-white/75 sm:text-base">
              খতিয়ান, দলিল আর নামজারির তথ্য পাশাপাশি মিলিয়ে দেখুন। অমিল ও পরের করণীয় স্পষ্টভাবে পান।
            </p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <Link href="/upload" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-[#7FD1B3] px-5 font-semibold text-[#12342A] transition-colors hover:bg-[#A1E1C8] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">
                কাগজ যাচাই শুরু করুন <Arrow />
              </Link>
              <Link href="/cases" className="inline-flex min-h-12 items-center justify-center rounded-lg border border-white/30 px-5 font-medium text-white transition-colors hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">
                নমুনা রিপোর্ট দেখুন
              </Link>
            </div>
            <p className="mt-5 text-xs leading-6 text-white/60">এটি কাগজের তথ্যের প্রাথমিক মিল পরীক্ষা; আইনি মতামত নয়।</p>
          </div>

          <article aria-label="নমুনা যাচাই ফলাফল" className="relative rounded-xl border border-white/15 bg-[#F8FAF8] p-4 text-[#16201B] shadow-2xl shadow-black/10 sm:p-5">
            <div className="flex items-start justify-between gap-3 border-b border-[#D9DFDA] pb-4">
              <div>
                <p className="text-xs font-semibold text-[#56635C]">নমুনা যাচাই ফলাফল</p>
                <h2 className="mt-1 text-lg font-semibold">দলিল ও খতিয়ানের মিল</h2>
              </div>
              <span className="shrink-0 rounded-full bg-[#F9E3E1] px-3 py-1.5 text-xs font-semibold text-[#A3221B]">বড় অমিল</span>
            </div>
            <div className="space-y-3 py-4">
              <div className="flex items-start gap-3 rounded-lg bg-[#FBEDEB] p-3">
                <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#B3261E] text-sm font-bold text-white">!</span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold">বিক্রির পরিমাণ অংশের বেশি</p>
                  <p className="mt-1 text-xs leading-5 text-[#56635C]">দলিলে ১৮ শতাংশ · কাগজে বিক্রেতার অংশ ৪.৭৯৫ শতাংশ</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <span className="rounded bg-white px-2 py-1 text-[11px] text-[#56635C]">দলিল · তফসিল</span>
                    <span className="rounded bg-white px-2 py-1 text-[11px] text-[#56635C]">খতিয়ান · মালিকের অংশ</span>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg border border-[#D9DFDA] p-3">
                  <p className="text-[11px] text-[#56635C]">হস্তান্তর</p>
                  <p className="mt-1 text-lg font-semibold tabular-nums">১৮.০০ <span className="text-sm font-medium">শতাংশ</span></p>
                </div>
                <div className="rounded-lg border border-[#D9DFDA] p-3">
                  <p className="text-[11px] text-[#56635C]">উপলব্ধ অংশ</p>
                  <p className="mt-1 text-lg font-semibold tabular-nums">৪.৭৯৫ <span className="text-sm font-medium">শতাংশ</span></p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 border-t border-[#D9DFDA] pt-3 text-xs leading-5 text-[#56635C]">
              <span aria-hidden="true" className="text-[#7A4B00]">?</span>
              <span>পরবর্তী পদক্ষেপ: বাকি অংশের কাগজ বা সম্মতি যাচাই করুন।</span>
            </div>
          </article>
        </div>
      </section>

      <section aria-labelledby="services-title" className="space-y-6">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold text-accent">একটি কাজের ধারায়</p>
          <h2 id="services-title" className="mt-2 text-2xl font-normal text-ink sm:text-3xl">কেনা থেকে মালিকানা নজরদারি</h2>
          <p className="mt-3 text-sm leading-7 text-muted">কাগজ যাচাই, লেনদেনের সহায়তা আর কেনার পরের নজরদারি—প্রয়োজন অনুযায়ী ব্যবহার করুন।</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {offerings.map((item) => (
            <Link key={item.title} href={item.href} className="group rounded-xl border border-line bg-surface p-5 transition-colors hover:border-accent/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              <div className="flex items-center justify-between gap-3">
                <span className="rounded-full bg-accent-soft px-2.5 py-1 text-xs font-semibold text-accent">{item.phase}</span>
                <span aria-hidden="true" className="font-heading text-2xl text-accent/70">{item.mark}</span>
              </div>
              <h3 className="mt-5 text-lg font-semibold text-ink group-hover:text-accent">{item.title}</h3>
              <p className="mt-2 min-h-14 text-sm leading-6 text-muted">{item.copy}</p>
              <span className="mt-4 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-accent">বিস্তারিত <Arrow /></span>
            </Link>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-line bg-surface p-5 sm:p-8">
        <div className="grid gap-8 lg:grid-cols-[0.72fr_1fr] lg:gap-12">
          <div>
            <p className="text-sm font-semibold text-accent">যাচাইয়ের ধাপ</p>
            <h2 className="mt-2 text-2xl font-normal text-ink sm:text-3xl">কাগজ থেকে করণীয়</h2>
            <p className="mt-3 text-sm leading-7 text-muted">প্রতিটি ফলাফলে কোন কাগজ থেকে তথ্য এসেছে তা দেখুন।</p>
          </div>
          <ol className="grid gap-3 sm:grid-cols-2">
            {steps.map(([title, copy], index) => (
              <li key={title} className="flex gap-3 rounded-lg bg-bg p-4">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-surface font-mono text-xs text-accent">০{index + 1}</span>
                <div>
                  <h3 className="font-semibold text-ink">{title}</h3>
                  <p className="mt-1 text-sm leading-6 text-muted">{copy}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="flex flex-col gap-5 rounded-2xl bg-[#E1EEE8] p-5 sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div className="max-w-2xl">
          <h2 className="text-xl font-normal text-[#12342A] sm:text-2xl">কাগজের মিল মানেই সব যাচাই শেষ নয়</h2>
          <p className="mt-2 text-sm leading-7 text-[#3E5A4D]">মামলা, দখল বা কাগজে না থাকা বন্ধকের তথ্য এই মিল পরীক্ষায় ধরা নাও পড়তে পারে। প্রয়োজন হলে সংশ্লিষ্ট পেশাজীবীর পরামর্শ নিন।</p>
        </div>
        <Link href="/upload" className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-lg bg-accent px-5 font-semibold text-white hover:bg-[#185541] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">যাচাই শুরু করুন <Arrow /></Link>
      </section>

    </div>
  );
}
